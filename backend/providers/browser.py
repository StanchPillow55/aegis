import logging
from typing import Optional

from playwright.sync_api import sync_playwright, Page

from backend.intake.schema import WOD

logger = logging.getLogger(__name__)


def _extract_wod_from_page(page: Page) -> WOD:
    try:
        page.wait_for_load_state("networkidle", timeout=10000)

        content = page.content().lower()

        movements = []
        movement_keywords = [
            "clean",
            "snatch",
            "squat",
            "deadlift",
            "press",
            "jerk",
            "pull-up",
            "pullup",
            "push-up",
            "pushup",
            "row",
            "run",
            "bike",
            "burpee",
            "lunge",
            "thruster",
            "box jump",
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
        return WOD(movements=[], raw="")


def import_wod(url: str) -> WOD:
    """Import a WOD from a URL using local Playwright."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            try:
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                wod = _extract_wod_from_page(page)

                logger.info(f"Imported WOD from {url}: {len(wod.movements)} movements")
                return wod
            finally:
                page.close()
                browser.close()

    except Exception as e:
        logger.error(f"Failed to import WOD from {url}: {e}")
        return WOD(movements=[], raw="")
