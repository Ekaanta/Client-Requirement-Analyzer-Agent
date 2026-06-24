from pydantic import BaseModel, HttpUrl, field_validator
from typing import Literal
from enum import Enum


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AnalyzeRequest(BaseModel):
    requirements: str
    figma_url: str

    @field_validator("requirements")
    @classmethod
    def requirements_not_empty(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 20:
            raise ValueError("Requirements must be at least 20 characters.")
        return v

    @field_validator("figma_url")
    @classmethod
    def figma_url_valid(cls, v: str) -> str:
        v = v.strip()
        if "figma.com" not in v:
            raise ValueError("URL must be a valid Figma link (figma.com).")
        return v


class Issue(BaseModel):
    id: str
    category: str
    severity: Severity
    title: str
    description: str
    location: str | None = None
    recommendation: str


class AnalysisReport(BaseModel):
    overall_score: int          # 0-100
    requirement_coverage: float # 0.0-100.0
    total_issues: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    issues: list[Issue]
    ai_summary: str
    figma_file_name: str | None = None
    screens_found: list[str] = []
    components_found: list[str] = []


class AnalyzeResponse(BaseModel):
    success: bool
    report: AnalysisReport | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    n8n_reachable: bool
