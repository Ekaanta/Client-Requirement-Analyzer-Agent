import re
import time
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_not_exception_type
from backend.core.config import get_settings
from backend.core.exceptions import FigmaError
from backend.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

FIGMA_API_BASE = "https://api.figma.com/v1"

_cache: dict = {}
_cache_ttl = 600  # 10 minutes


def parse_figma_url(url: str) -> tuple[str, str | None]:
    pattern = r"figma\.com/(?:file|design)/([a-zA-Z0-9]+)"
    match = re.search(pattern, url)
    if not match:
        raise FigmaError("Could not parse Figma file key from URL.", detail=url)
    file_key = match.group(1)
    node_match = re.search(r"node-id=([^&]+)", url)
    node_id = node_match.group(1).replace("-", ":") if node_match else None
    return file_key, node_id


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=5, max=30),
    retry=retry_if_not_exception_type(FigmaError),
)
async def fetch_figma_file(file_key: str) -> dict:
    # Cache check — avoid repeated API calls
    cached = _cache.get(file_key)
    if cached and time.time() - cached["ts"] < _cache_ttl:
        logger.info("figma_cache_hit", file_key=file_key)
        return cached["data"]

    if not settings.figma_access_token:
        raise FigmaError("FIGMA_ACCESS_TOKEN is not configured.")

    headers = {"X-Figma-Token": settings.figma_access_token}
    url = f"{FIGMA_API_BASE}/files/{file_key}?depth=3"

    async with httpx.AsyncClient(timeout=settings.figma_timeout_seconds) as client:
        resp = await client.get(url, headers=headers)

    if resp.status_code == 429:
        raise FigmaError("Figma rate limit exceeded. Please wait a few minutes and try again.")
    if resp.status_code == 403:
        raise FigmaError("Figma access denied. Check your token or file permissions.")
    if resp.status_code == 404:
        raise FigmaError("Figma file not found. Verify the URL.")
    if resp.status_code != 200:
        raise FigmaError(f"Figma API error: {resp.status_code}", detail=resp.text[:300])

    data = resp.json()
    _cache[file_key] = {"data": data, "ts": time.time()}
    logger.info("figma_fetch_success", file_key=file_key, name=data.get("name"))
    return data


def extract_design_summary(figma_data: dict) -> dict:
    document = figma_data.get("document", {})
    file_name = figma_data.get("name", "Unknown")

    screens: list[str] = []
    components: list[str] = []
    text_styles: list[str] = []
    colors: list[str] = []

    def traverse(node: dict, depth: int = 0) -> None:
        node_type = node.get("type", "")
        node_name = node.get("name", "")

        if node_type in ("FRAME", "COMPONENT", "INSTANCE") and depth <= 3:
            if depth <= 1:
                screens.append(node_name)
            else:
                components.append(node_name)

        if node_type == "TEXT":
            style = node.get("style", {})
            font = style.get("fontFamily", "")
            size = style.get("fontSize", "")
            if font and f"{font}/{size}" not in text_styles:
                text_styles.append(f"{font}/{size}px")

        for fill in node.get("fills", []):
            if fill.get("type") == "SOLID":
                c = fill.get("color", {})
                r = int(c.get("r", 0) * 255)
                g = int(c.get("g", 0) * 255)
                b = int(c.get("b", 0) * 255)
                hex_color = f"#{r:02x}{g:02x}{b:02x}"
                if hex_color not in colors:
                    colors.append(hex_color)

        for child in node.get("children", []):
            traverse(child, depth + 1)

    traverse(document)

    return {
        "file_name": file_name,
        "screens": list(dict.fromkeys(screens))[:30],
        "components": list(dict.fromkeys(components))[:60],
        "text_styles": list(dict.fromkeys(text_styles))[:20],
        "colors": list(dict.fromkeys(colors))[:30],
        "total_nodes": _count_nodes(document),
    }


def _count_nodes(node: dict) -> int:
    count = 1
    for child in node.get("children", []):
        count += _count_nodes(child)
    return count

async def export_figma_screens(file_key: str, node_ids: list[str]) -> dict[str, str]:
    """Export Figma screens as images and return base64 encoded."""
    import base64

    if not settings.figma_access_token:
        raise FigmaError("FIGMA_ACCESS_TOKEN is not configured.")

    headers = {"X-Figma-Token": settings.figma_access_token}
    ids = ",".join(node_ids[:5])  # Max 5 screens to avoid rate limit
    url = f"{FIGMA_API_BASE}/images/{file_key}?ids={ids}&format=png&scale=1"

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(url, headers=headers)

    if resp.status_code != 200:
        raise FigmaError(f"Figma image export failed: {resp.status_code}")

    image_urls = resp.json().get("images", {})

    # Download each image and convert to base64
    images_b64: dict[str, str] = {}
    async with httpx.AsyncClient(timeout=60) as client:
        for node_id, img_url in image_urls.items():
            if img_url:
                img_resp = await client.get(img_url)
                if img_resp.status_code == 200:
                    b64 = base64.b64encode(img_resp.content).decode("utf-8")
                    images_b64[node_id] = b64

    return images_b64


def extract_node_ids(figma_data: dict) -> list[str]:
    """Extract top-level frame node IDs (screens)."""
    node_ids = []
    document = figma_data.get("document", {})

    def traverse(node: dict, depth: int = 0) -> None:
        if node.get("type") == "FRAME" and depth <= 1:
            node_id = node.get("id", "")
            if node_id:
                node_ids.append(node_id)
        for child in node.get("children", []):
            traverse(child, depth + 1)

    traverse(document)
    return node_ids[:5]  # First 5 screens only