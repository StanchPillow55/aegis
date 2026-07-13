import logging
from typing import Optional

from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeout

from backend.config import get_settings
from backend.intake.schema import WOD
from backend.obs.tracing import capture_exception_with_context, traced_span, traced_span_context

logger = logging.getLogger(__name__)


def _extract_wod_from_page(page: Page) -> WOD:
    try:
        with traced_span_context("browserbase.parse_content"):
            page.wait_for_load_state("networkidle", timeout=10000)
            
            content = page.content().lower()
            
            movements = []
            movement_keywords = [
                "clean", "snatch", "squat", "deadlift", "press", "jerk",
                "pull-up", "pullup", "push-up", "pushup", "row", "run",
                "bike", "burpee", "lunge", "thruster", "box jump"
            ]
            
            for keyword in movement_keywords:
                if keyword in content:
                    movements.append(keyword.replace("-", " "))
            
            movements = list(dict.fromkeys(movements))
            
            raw_text = page.inner_text("body")
            raw_lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
            raw_text = " ".join(raw_lines[:20])
            
            if not movements:
                logger.warning("No movements detected in page content")
                return WOD(movements=[], raw="")
            
            return WOD(movements=movements, raw=raw_text[:500])
    
    except Exception as e:
        logger.error(f"Error extracting WOD from page: {e}")
        capture_exception_with_context(e, function="_extract_wod_from_page")
        return WOD(movements=[], raw="")


@traced_span("browserbase.import_wod", operation="fetch")
def import_wod(url: str) -> WOD:
    settings = get_settings()
    
    try:
        with sync_playwright() as p:
            with traced_span_context("browserbase.connect"):
                browser = p.chromium.connect_over_cdp(
                    f"wss://connect.browserbase.com?apiKey={settings.browserbase_api_key}"
                )
            
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.new_page()
            
            try:
                with traced_span_context("browserbase.navigate", url=url):
                    page.goto(url, timeout=30000, wait_until="domcontentloaded")
                wod = _extract_wod_from_page(page)
                
                logger.info(f"Imported WOD from {url}: {len(wod.movements)} movements")
                return wod
            
            finally:
                page.close()
                browser.close()
    
    except Exception as e:
        logger.error(f"Failed to import WOD from {url}: {e}")
        capture_exception_with_context(e, function="import_wod", url=url)
        return WOD(movements=[], raw="")
