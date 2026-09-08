"""FITINDEX screenshot OCR via local Ollama llava (optional).

Creates a review draft — never auto-saves without confirm.
"""

from __future__ import annotations

import base64
import json
import re
from typing import Any
from urllib import error, request

from backend.chat import vision_status
from backend.config import get_settings
from backend.health.store import FitindexManualIn, FitindexReview, HealthMetricsStore

_VISION_PROMPT = """Look at this FITINDEX app screenshot and extract body composition metrics.
Return ONLY valid JSON:
{"weight_kg": number_or_null, "body_fat_pct": number_or_null, "day": "YYYY-MM-DD_or_null", "notes": "ocr"}
If weight is in pounds, convert to kg (divide by 2.2046). Use null when unknown.
"""


def _lbs_to_kg(lbs: float) -> float:
    return round(lbs / 2.2046, 2)


def propose_from_image(image_bytes: bytes, store: HealthMetricsStore | None = None) -> dict[str, Any]:
    """OCR screenshot → FITINDEX review draft, or honest disabled status."""
    store = store or HealthMetricsStore()
    status = vision_status()
    if not status.get("available"):
        return {
            "ok": False,
            "draft": None,
            "vision": status,
            "detail": status.get("detail") or "Vision OCR disabled — install Ollama llava or use CSV/manual.",
        }

    settings = get_settings()
    model = (status.get("models") or ["llava"])[0]
    b64 = base64.b64encode(image_bytes).decode("ascii")
    payload = {
        "model": model,
        "prompt": _VISION_PROMPT,
        "images": [b64],
        "stream": False,
        "format": "json",
    }
    req = request.Request(
        f"{settings.ollama_base_url.rstrip('/')}/api/generate",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=max(30.0, settings.ollama_timeout_s)) as resp:
            raw = json.loads(resp.read().decode())
        text = raw.get("response") or "{}"
        parsed = json.loads(text) if isinstance(text, str) else text
    except (error.URLError, error.HTTPError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "draft": None,
            "vision": status,
            "detail": f"llava OCR failed: {type(exc).__name__}: {exc}",
        }

    weight = parsed.get("weight_kg")
    # Accept weight_lb mistaken field
    if weight is None and parsed.get("weight") is not None:
        w = float(parsed["weight"])
        weight = _lbs_to_kg(w) if w > 140 else w  # heuristic: large numbers likely lbs
    body = FitindexManualIn(
        weight_kg=float(weight) if weight is not None else None,
        body_fat_pct=float(parsed["body_fat_pct"]) if parsed.get("body_fat_pct") is not None else None,
        day=parsed.get("day"),
        notes="fitindex_ocr_llava",
        confirmed=False,
    )
    if body.weight_kg is None and body.body_fat_pct is None:
        return {
            "ok": False,
            "draft": None,
            "vision": status,
            "raw": parsed,
            "detail": "OCR returned no usable metrics — try CSV or manual entry.",
        }
    draft: FitindexReview = store.fitindex_propose(body)
    return {
        "ok": True,
        "draft": draft.model_dump(),
        "vision": status,
        "detail": "Review and confirm draft before save.",
    }


def propose_from_text_heuristic(text: str, store: HealthMetricsStore | None = None) -> FitindexReview:
    """Offline fallback: regex extract weight/body fat from free text into a draft."""
    store = store or HealthMetricsStore()
    lower = text.lower()
    weight_kg = None
    body_fat = None
    m = re.search(r"(\d+(?:\.\d+)?)\s*kg", lower)
    if m:
        weight_kg = float(m.group(1))
    else:
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:lb|lbs|pounds)", lower)
        if m:
            weight_kg = _lbs_to_kg(float(m.group(1)))
    m = re.search(r"(\d+(?:\.\d+)?)\s*%?\s*(?:body\s*fat|bf)", lower)
    if m:
        body_fat = float(m.group(1))
    body = FitindexManualIn(
        weight_kg=weight_kg,
        body_fat_pct=body_fat,
        notes="fitindex_text_heuristic",
        confirmed=False,
    )
    return store.fitindex_propose(body)
