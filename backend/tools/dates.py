"""Optional natural-language date parsing for tool ranges."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any


def parse_date_range(text: str, *, today: date | None = None) -> dict[str, Any]:
    """Parse simple NL date phrases. Uses dateparser if installed, else heuristics.

    Returns {ok, start, end, method, limitation?}.
    """
    today = today or date.today()
    raw = (text or "").strip().lower()
    if not raw:
        return {"ok": False, "limitation": "Empty date text"}

    # Try optional dateparser
    try:
        import dateparser  # type: ignore

        settings = {"PREFER_DATES_FROM": "past", "RETURN_AS_TIMEZONE_AWARE": False}
        # range patterns
        if " to " in raw or " through " in raw or "–" in raw or "—" in raw:
            sep = " to " if " to " in raw else (" through " if " through " in raw else None)
            if sep:
                left, right = raw.split(sep, 1)
            else:
                left, right = raw.replace("—", "–").split("–", 1)
            d1 = dateparser.parse(left.strip(), settings=settings)
            d2 = dateparser.parse(right.strip(), settings=settings)
            if d1 and d2:
                return {
                    "ok": True,
                    "start": d1.date().isoformat(),
                    "end": d2.date().isoformat(),
                    "method": "dateparser",
                }
        dt = dateparser.parse(raw, settings=settings)
        if dt:
            d = dt.date()
            return {
                "ok": True,
                "start": d.isoformat(),
                "end": d.isoformat(),
                "method": "dateparser",
            }
    except ImportError:
        pass

    # Heuristics (no extra dependency)
    if raw in {"today"}:
        return {"ok": True, "start": today.isoformat(), "end": today.isoformat(), "method": "heuristic"}
    if raw in {"yesterday"}:
        d = today - timedelta(days=1)
        return {"ok": True, "start": d.isoformat(), "end": d.isoformat(), "method": "heuristic"}
    if "last 7" in raw or "past week" in raw or "last week" in raw:
        start = today - timedelta(days=6)
        return {
            "ok": True,
            "start": start.isoformat(),
            "end": today.isoformat(),
            "method": "heuristic",
        }
    if "last 30" in raw or "past month" in raw or "last month" in raw:
        start = today - timedelta(days=29)
        return {
            "ok": True,
            "start": start.isoformat(),
            "end": today.isoformat(),
            "method": "heuristic",
        }
    # ISO date
    try:
        d = datetime.strptime(raw[:10], "%Y-%m-%d").date()
        return {"ok": True, "start": d.isoformat(), "end": d.isoformat(), "method": "iso"}
    except ValueError:
        pass

    return {
        "ok": False,
        "limitation": "Could not parse date; install dateparser for richer NL, or use YYYY-MM-DD / today / last 7 days.",
        "method": "none",
    }
