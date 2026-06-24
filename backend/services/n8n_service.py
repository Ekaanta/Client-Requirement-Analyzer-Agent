from backend.core.config import get_settings
from backend.core.logging import get_logger
from backend.models.schemas import AnalysisReport
from backend.services import grok_service

logger = get_logger(__name__)
settings = get_settings()

MOCK_DESIGN_SUMMARY = {
    "file_name": "GOGO Delivery App",
    "screens": [
        "Login", "Register", "Dashboard", "Order List", "Order Details",
        "Rider Management", "Map View", "Settings", "Profile", "Support"
    ],
    "components": [
        "Primary Button", "Input Field", "Navbar", "Card", "Modal",
        "Dropdown", "Table", "Search Bar", "Status Badge", "Avatar"
    ],
    "text_styles": ["Inter/12px", "Inter/14px", "Inter/16px", "Inter/24px"],
    "colors": ["#ffffff", "#000000", "#FF5733", "#3498DB", "#2ECC71"],
    "total_nodes": 850,
}


async def trigger_n8n_workflow(requirements: str, figma_url: str) -> AnalysisReport:
    logger.info("using_mock_figma_data")
    return await grok_service.analyze_with_grok(requirements, MOCK_DESIGN_SUMMARY, None)


async def check_n8n_health() -> bool:
    return False