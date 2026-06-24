from fastapi import APIRouter, HTTPException, status
from backend.models.schemas import AnalyzeRequest, AnalyzeResponse, HealthResponse
from backend.services import n8n_service
from backend.core.exceptions import AppBaseException
from backend.core.logging import get_logger
from backend.core.config import get_settings

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse, status_code=status.HTTP_200_OK)
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    Main endpoint: receive requirements + figma_url,
    trigger n8n workflow, return structured report.
    """
    logger.info(
        "analyze_request",
        figma_url=request.figma_url,
        req_length=len(request.requirements),
    )
    try:
        report = await n8n_service.trigger_n8n_workflow(
            requirements=request.requirements,
            figma_url=request.figma_url,
        )
        logger.info("analyze_success", score=report.overall_score, issues=report.total_issues)
        return AnalyzeResponse(success=True, report=report)

    except AppBaseException as e:
        logger.error("analyze_app_error", error=e.message, detail=e.detail)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{e.message}: {e.detail or ''}",
        )
    except Exception as e:
        logger.exception("analyze_unexpected_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again.",
        )


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    n8n_ok = await n8n_service.check_n8n_health()
    return HealthResponse(
        status="ok",
        version="1.0.0",
        n8n_reachable=n8n_ok,
    )
