import json
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from backend.core.config import get_settings
from backend.core.exceptions import GrokError
from backend.core.logging import get_logger
from backend.models.schemas import AnalysisReport, Issue, Severity

logger = get_logger(__name__)
settings = get_settings()

GROK_API_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT = """You are an expert UI/UX Requirement Validation Analyst and QA Engineer.
You will be given software requirements AND actual Figma screen images.

Perform TRUE VISUAL analysis:
- Look at the actual UI in the images
- Check if required screens, components, buttons, forms exist VISUALLY
- Check layout, spacing, alignment, colors, typography VISUALLY
- Do NOT flag things as missing if they exist visually in the screenshots
- Only report REAL mismatches between requirements and what you actually SEE

You MUST respond with a single valid JSON object and nothing else:
{
  "overall_score": <int 0-100>,
  "requirement_coverage": <float 0-100>,
  "ai_summary": "<string>",
  "issues": [
    {
      "category": "<Requirement Coverage|Missing Screen|Missing Component|Missing Button|Missing Form|Missing Input|Missing Navigation|Missing Validation|Missing State|Typography|Color|Spacing|Responsive|Accessibility|UI Consistency|UX Problem|Business Logic|Design Quality>",
      "severity": "<critical|high|medium|low>",
      "title": "<string>",
      "description": "<string>",
      "location": "<screen name or null>",
      "recommendation": "<string>"
    }
  ]
}"""


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def analyze_with_grok(
    requirements: str,
    design_summary: dict,
    screen_images: dict[str, str] | None = None,
) -> AnalysisReport:
    if not settings.grok_api_key:
        raise GrokError("GROK_API_KEY is not configured.")

    # Build message content
    content = []

    # Add text prompt
    text_prompt = f"""Analyze these software requirements against the Figma design.

=== SOFTWARE REQUIREMENTS ===
{requirements}

=== FIGMA DESIGN INFO ===
File: {design_summary.get('file_name', 'Unknown')}
Screens: {', '.join(design_summary.get('screens', [])) or 'None'}
Components: {', '.join(design_summary.get('components', [])) or 'None'}

"""
    if screen_images:
        text_prompt += f"I am providing {len(screen_images)} actual Figma screen screenshots below. Analyze them VISUALLY.\n"
        text_prompt += "Return ONLY the JSON object."
    else:
        text_prompt += "No screenshots available. Analyze based on design summary only.\nReturn ONLY the JSON object."

    content.append({"type": "text", "text": text_prompt})

    # Add screen images if available
    if screen_images:
        for node_id, b64_image in screen_images.items():
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{b64_image}"
                }
            })

    payload = {
        "model": settings.grok_model,
        "max_tokens": 4096,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
    }

    headers = {
        "Authorization": f"Bearer {settings.grok_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8501",
        "X-Title": "AI Requirement Validator",
    }

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(GROK_API_URL, json=payload, headers=headers)

    logger.info("openrouter_response", status=resp.status_code, body=resp.text[:300])

    if resp.status_code == 401:
        raise GrokError("API key invalid.")
    if resp.status_code == 402:
        raise GrokError("No credits.")
    if resp.status_code == 429:
        raise GrokError("Rate limit exceeded.")
    if resp.status_code != 200:
        raise GrokError(f"API error: {resp.status_code}", detail=resp.text[:300])

    data = resp.json()
    raw_content = data["choices"][0]["message"]["content"].strip()

    if raw_content.startswith("```"):
        raw_content = raw_content.split("```")[1]
        if raw_content.startswith("json"):
            raw_content = raw_content[4:]
    raw_content = raw_content.strip()

    try:
        parsed = json.loads(raw_content)
    except json.JSONDecodeError as e:
        logger.error("json_parse_error", raw=raw_content[:300], error=str(e))
        raise GrokError("Invalid JSON response.", detail=str(e))

    return _build_report(parsed, design_summary)


def _build_report(parsed: dict, design_summary: dict) -> AnalysisReport:
    issues: list[Issue] = []
    for i, raw_issue in enumerate(parsed.get("issues", [])):
        try:
            severity = Severity(raw_issue.get("severity", "medium").lower())
        except ValueError:
            severity = Severity.MEDIUM

        issues.append(Issue(
            id=f"issue-{i+1:03d}",
            category=raw_issue.get("category", "General"),
            severity=severity,
            title=raw_issue.get("title", "Unnamed issue"),
            description=raw_issue.get("description", ""),
            location=raw_issue.get("location"),
            recommendation=raw_issue.get("recommendation", ""),
        ))

    severity_counts = {s: 0 for s in Severity}
    for issue in issues:
        severity_counts[issue.severity] += 1

    return AnalysisReport(
        overall_score=max(0, min(100, int(parsed.get("overall_score", 50)))),
        requirement_coverage=max(0.0, min(100.0, float(parsed.get("requirement_coverage", 50.0)))),
        total_issues=len(issues),
        critical_count=severity_counts[Severity.CRITICAL],
        high_count=severity_counts[Severity.HIGH],
        medium_count=severity_counts[Severity.MEDIUM],
        low_count=severity_counts[Severity.LOW],
        issues=issues,
        ai_summary=parsed.get("ai_summary", "Analysis complete."),
        figma_file_name=design_summary.get("file_name"),
        screens_found=design_summary.get("screens", []),
        components_found=design_summary.get("components", []),
    )