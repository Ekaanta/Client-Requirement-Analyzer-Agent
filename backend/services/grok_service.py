import json
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from backend.core.config import get_settings
from backend.core.exceptions import GrokError
from backend.core.logging import get_logger
from backend.models.schemas import AnalysisReport, Issue, Severity

logger = get_logger(__name__)
settings = get_settings()

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """You are an expert UI/UX Requirement Validation Analyst and QA Engineer.
Compare software requirements against a Figma design summary and identify ALL mismatches.
Respond ONLY with a single valid JSON object and nothing else.
JSON schema:
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

ANALYSIS_PROMPT = """Analyze requirements vs Figma design and find ALL mismatches.

=== SOFTWARE REQUIREMENTS ===
{requirements}

=== FIGMA DESIGN SUMMARY ===
File: {file_name}
Screens: {screens}
Components: {components}
Text styles: {text_styles}
Colors: {colors}
Total nodes: {total_nodes}

Return ONLY the JSON object."""


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def analyze_with_grok(
    requirements: str,
    design_summary: dict,
    screen_images: dict | None = None,
) -> AnalysisReport:
    if not settings.grok_api_key:
        raise GrokError("GROK_API_KEY is not configured.")

    prompt = ANALYSIS_PROMPT.format(
        requirements=requirements,
        file_name=design_summary.get("file_name", "Unknown"),
        screens=", ".join(design_summary.get("screens", [])) or "None",
        components=", ".join(design_summary.get("components", [])) or "None",
        text_styles=", ".join(design_summary.get("text_styles", [])) or "None",
        colors=", ".join(design_summary.get("colors", [])) or "None",
        total_nodes=design_summary.get("total_nodes", 0),
    )

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 4096,
    }

    headers = {
        "Authorization": f"Bearer {settings.grok_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(GROQ_API_URL, json=payload, headers=headers)

    logger.info("groq_response", status=resp.status_code, body=resp.text[:300])

    if resp.status_code == 401:
        raise GrokError("Groq API key invalid.")
    if resp.status_code == 429:
        raise GrokError("Groq rate limit exceeded.")
    if resp.status_code != 200:
        raise GrokError(f"Groq API error: {resp.status_code}", detail=resp.text[:300])

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