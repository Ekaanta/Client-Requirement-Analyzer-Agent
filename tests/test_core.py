import pytest
from backend.models.schemas import AnalyzeRequest, Issue, Severity
from backend.services.figma_service import extract_design_summary, parse_figma_url
from backend.services.grok_service import _build_report
from backend.core.exceptions import FigmaError


# ── Model validation ─────────────────────────────────────────────────────────

def test_analyze_request_valid():
    r = AnalyzeRequest(
        requirements="User can log in with email and password. Dashboard shows recent orders.",
        figma_url="https://www.figma.com/file/ABC123/My-App",
    )
    assert r.requirements.startswith("User")
    assert "figma.com" in r.figma_url


def test_analyze_request_short_requirements():
    with pytest.raises(Exception):
        AnalyzeRequest(requirements="too short", figma_url="https://figma.com/file/X/Y")


def test_analyze_request_invalid_url():
    with pytest.raises(Exception):
        AnalyzeRequest(
            requirements="User can log in with email and password. Dashboard shows recent orders.",
            figma_url="https://example.com/design",
        )


# ── Figma URL parser ──────────────────────────────────────────────────────────

def test_parse_figma_url_design():
    key, node = parse_figma_url("https://www.figma.com/design/XYZ789abc/My-App?node-id=1-2")
    assert key == "XYZ789abc"
    assert node == "1:2"


def test_parse_figma_url_file():
    key, node = parse_figma_url("https://www.figma.com/file/ABC123/My-App")
    assert key == "ABC123"
    assert node is None


def test_parse_figma_url_invalid():
    with pytest.raises(FigmaError):
        parse_figma_url("https://example.com/notfigma")


# ── Design summary extractor ──────────────────────────────────────────────────

MOCK_FIGMA_DATA = {
    "name": "Test App",
    "document": {
        "type": "DOCUMENT",
        "name": "Document",
        "children": [
            {
                "type": "FRAME",
                "name": "Login Screen",
                "fills": [{"type": "SOLID", "color": {"r": 1, "g": 1, "b": 1}}],
                "children": [
                    {
                        "type": "COMPONENT",
                        "name": "Login Button",
                        "fills": [{"type": "SOLID", "color": {"r": 0.4, "g": 0.2, "b": 0.8}}],
                        "children": [],
                    },
                    {
                        "type": "TEXT",
                        "name": "Email Label",
                        "style": {"fontFamily": "Inter", "fontSize": 14},
                        "fills": [],
                        "children": [],
                    },
                ],
            }
        ],
    },
}


def test_extract_design_summary():
    summary = extract_design_summary(MOCK_FIGMA_DATA)
    assert summary["file_name"] == "Test App"
    assert "Login Screen" in summary["screens"]
    assert any("Inter" in s for s in summary["text_styles"])
    assert len(summary["colors"]) > 0


# ── Report builder ───────────────────────────────────────────────────────────

def test_build_report_counts():
    parsed = {
        "overall_score": 72,
        "requirement_coverage": 65.5,
        "ai_summary": "Several critical issues found.",
        "issues": [
            {"category": "Missing Screen", "severity": "critical", "title": "No dashboard", "description": "...", "recommendation": "Add it"},
            {"category": "Missing Button", "severity": "high", "title": "No logout btn", "description": "...", "recommendation": "Add it"},
            {"category": "Typography", "severity": "medium", "title": "Font mismatch", "description": "...", "recommendation": "Fix it"},
            {"category": "Color", "severity": "low", "title": "Minor color diff", "description": "...", "recommendation": "Fix it"},
        ],
    }
    design_summary = {"file_name": "App", "screens": ["Login"], "components": ["Button"]}
    report = _build_report(parsed, design_summary)

    assert report.overall_score == 72
    assert report.requirement_coverage == 65.5
    assert report.total_issues == 4
    assert report.critical_count == 1
    assert report.high_count == 1
    assert report.medium_count == 1
    assert report.low_count == 1
    assert report.issues[0].severity == Severity.CRITICAL
    assert report.issues[0].id == "issue-001"


def test_build_report_score_clamping():
    parsed = {"overall_score": 999, "requirement_coverage": -5, "ai_summary": "x", "issues": []}
    report = _build_report(parsed, {"file_name": "x", "screens": [], "components": []})
    assert report.overall_score == 100
    assert report.requirement_coverage == 0.0
