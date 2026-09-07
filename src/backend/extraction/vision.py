"""Vision extraction: screenshot/image -> WOD structure using Ollama multimodal."""

import base64
import json
from pathlib import Path
from typing import Optional

import httpx

from src.backend.config import get_settings
from src.backend.models.intake import WOD

_VISION_PROMPT = """Look at this CrossFit workout screenshot and extract the workout details.

Return JSON:
{
  "workout_type": "amrap|for_time|emom|strength|chipper|interval|other",
  "movements": ["movement1", "movement2"],
  "prescribed_weight": "e.g. 135/95 or null",
  "time_cap": minutes_or_null,
  "rounds": number_or_null,
  "raw": "the full workout text as shown"
}

Return ONLY valid JSON."""


async def extract_wod_from_image(
    image_bytes: bytes,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> WOD:
    """Extract WOD from a screenshot using Ollama vision model."""
    settings = get_settings()
    url = base_url or settings.ollama_base_url
    mdl = model or settings.ollama_vision_model

    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{url}/api/generate",
            json={
                "model": mdl,
                "prompt": _VISION_PROMPT,
                "images": [b64_image],
                "stream": False,
                "format": "json",
            },
        )
        response.raise_for_status()
        result = response.json()

    raw_text = result.get("response", "")
    parsed = json.loads(raw_text)
    return WOD.model_validate(parsed)

async def describe_image_with_ollama(
    image_bytes: bytes,
    prompt: str = "Describe this image in detail.",
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> str:
    """Get a text description of an image using Ollama vision model."""
    settings = get_settings()
    url = base_url or settings.ollama_base_url
    mdl = model or settings.ollama_vision_model

    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{url}/api/generate",
            json={
                "model": mdl,
                "prompt": prompt,
                "images": [b64_image],
                "stream": False,
            },
        )
        response.raise_for_status()
        result = response.json()

    return result.get("response", "")
