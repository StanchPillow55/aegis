import logging
from backend.providers.browser import import_wod
from backend.providers.tracing import traced_span

logger = logging.getLogger(__name__)

@traced_span("wod_importer.fetch")
def fetch_wod(url: str):
    """Fetch WOD from url using local playwright."""
    logger.info(f"Fetching WOD from {url}")
    return import_wod(url)
