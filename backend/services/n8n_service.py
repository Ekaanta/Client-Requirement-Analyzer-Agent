from backend.core.config import get_settings
from backend.core.logging import get_logger
from backend.models.schemas import AnalysisReport
from backend.services import grok_service

logger = get_logger(__name__)
settings = get_settings()

MOCK_DESIGN_SUMMARY = {
    "file_name": "GOGO Delivery App",
    "screens": ["Login", "Dashboard", "Order List", "Order Details", "Rider Management", "Map View", "Settings"],
    "components": ["Button", "Input Field", "Navbar", "Card", "Modal", "Dropdown", "Table", "Search Bar"],
    "text_styles": ["Inter/14px", "Inter/16px", "Inter/24px"],
    "colors": ["#ffffff", "#000000", "#FF5733", "#3498DB"],
    "total_nodes": 450,
}


async def trigger_n8n_workflow(requirements: str, figma_url: str) -> AnalysisReport:
    logger.info("using_mock_figma_data")
    return await grok_service.analyze_with_grok(requirements, MOCK_DESIGN_SUMMARY)


async def check_n8n_health() -> bool:
    return False