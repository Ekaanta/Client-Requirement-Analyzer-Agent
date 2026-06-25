from backend.core.config import get_settings
from backend.core.logging import get_logger
from backend.models.schemas import AnalysisReport
from backend.services import grok_service
from backend.services.figma_service import (
    parse_figma_url,
    fetch_figma_file,
    extract_design_summary,
    export_figma_screens,
    extract_node_ids,
)

logger = get_logger(__name__)
settings = get_settings()


async def trigger_n8n_workflow(requirements: str, figma_url: str) -> AnalysisReport:
    logger.info("direct_analysis_start")

    # Fetch Figma file
    file_key, _ = parse_figma_url(figma_url)
    figma_data = await fetch_figma_file(file_key)
    design_summary = extract_design_summary(figma_data)

    # Export screen images for visual analysis
    screen_images = None
    try:
        node_ids = extract_node_ids(figma_data)
        if node_ids:
            logger.info("exporting_figma_screens", count=len(node_ids))
            screen_images = await export_figma_screens(file_key, node_ids)
            logger.info("screens_exported", count=len(screen_images))
    except Exception as e:
        logger.warning("screen_export_failed", error=str(e))
        # Continue without images

    return await grok_service.analyze_with_grok(requirements, design_summary, screen_images)


async def check_n8n_health() -> bool:
    return False
