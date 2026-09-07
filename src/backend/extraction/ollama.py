"""Ollama-based extraction using Llama 3.2 with structured JSON output."""

import json
from typing import Optional

import httpx

from src.backend.config import get_settings
from src.backend.models.intake import IntakeResult

_SYSTEM_PROMPT = """You are the intake parser for a voice-first training copilot. The user speaks a short daily update covering sleep, soreness, nutrition, hydration, and workout details.

Extract ONLY what is stated or clearly implied. Do not invent details.

Return a JSON object matching this exact structure:
{
  "soreness": [{"body_part": "string", "severity": 1-5, "notes": "optional"}],
  "sleep": {"quality": "string", "hours": number_or_null, "notes": "optional"},
  "meals": [{"description": "string", "protein_g": number_or_null, "calories": number_or_null, "timing": "optional"}],
  "hydration": {"water_oz": number_or_null, "alcohol_drinks": number_or_null, "notes": "optional"},
  "todays_wod": {"workout_type": "amrap|for_time|emom|strength|chipper|interval|other", "movements": ["list"], "prescribed_weight": "optional", "time_cap": number_or_null, "rounds": number_or_null, "raw": "optional"},
  "performance": {"total_time_seconds": number_or_null, "total_rounds": number_or_null, "total_reps": number_or_null, "rx": bool_or_null, "scaled_notes": "optional", "hr_avg": number_or_null, "hr_max": number_or_null, "rpe": 1-10_or_null, "splits": [], "rep_breakdown": "optional", "feel": "optional", "notes": "optional"},
  "subjective_readiness": "low|moderate|high",
  "notes": "optional"
}

Rules:
- severity is 1 (barely sore) to 5 (severe)
- For subjective_readiness, infer from overall tone if not stated explicitly
- Convert time formats: "8:42" = 522 seconds
- Omit fields that weren't mentioned (use null)
- Return ONLY valid JSON, no markdown fences or explanation
"""


async def extract_with_ollama(
    text: str,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> IntakeResult:
    """Extract structured intake from free text using Ollama."""
    settings = get_settings()
    url = base_url or settings.ollama_base_url
    mdl = model or settings.ollama_model

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{url}/api/generate",
            json={
                "model": mdl,
                "prompt": text,
                "system": _SYSTEM_PROMPT,
                "stream": False,
                "format": "json",
            },
        )
        response.raise_for_status()
        result = response.json()

    raw_text = result.get("response", "")
    parsed = json.loads(raw_text)
    parsed = _repair_parsed(parsed)

    # Try strict validation first, fall back to lenient parsing
    try:
        return IntakeResult.model_validate(parsed)
    except Exception:
        # Strip fields that fail validation and try again
        return _lenient_validate(parsed)


def _repair_parsed(data: dict) -> dict:
    """Fill in missing required fields so Pydantic doesn't reject partial LLM output."""
    # Valid workout_type enum values
    _VALID_WORKOUT_TYPES = {"amrap", "for_time", "emom", "strength", "chipper", "interval", "other"}

    # sleep.quality is required — infer from hours or default
    if "sleep" in data and isinstance(data["sleep"], dict):
        if "quality" not in data["sleep"] or data["sleep"]["quality"] is None:
            hours = data["sleep"].get("hours")
            if hours is not None:
                if hours >= 7:
                    data["sleep"]["quality"] = "good"
                elif hours >= 5:
                    data["sleep"]["quality"] = "fair"
                else:
                    data["sleep"]["quality"] = "poor"
            else:
                data["sleep"]["quality"] = "not reported"
    elif "sleep" not in data or data["sleep"] is None:
        data["sleep"] = {"quality": "not reported"}

    # soreness entries need body_part and severity
    if "soreness" in data and isinstance(data["soreness"], list):
        # Filter out nulls/strings/invalid entries
        data["soreness"] = [item for item in data["soreness"] if isinstance(item, dict)]
        for item in data["soreness"]:
            if "body_part" not in item:
                item["body_part"] = "unspecified"
            if "severity" not in item:
                item["severity"] = 2

    # meals need description
    if "meals" in data and isinstance(data["meals"], list):
        data["meals"] = [item for item in data["meals"] if isinstance(item, dict)]
        for item in data["meals"]:
            if "description" not in item:
                item["description"] = "unspecified meal"

    # todays_wod.workout_type must be a valid enum value
    if "todays_wod" in data and isinstance(data["todays_wod"], dict):
        wt = data["todays_wod"].get("workout_type")
        if wt is not None and str(wt).lower() not in _VALID_WORKOUT_TYPES:
            data["todays_wod"]["workout_type"] = "other"

    # Clean up null string values the LLM sometimes returns as literal "null"
    _clean_null_strings(data)

    return data


def _clean_null_strings(obj):
    """Recursively replace string 'null' with actual None."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if value == "null" or value == "None":
                obj[key] = None
            elif isinstance(value, (dict, list)):
                _clean_null_strings(value)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            if item == "null" or item == "None":
                obj[i] = None
            elif isinstance(item, (dict, list)):
                _clean_null_strings(item)


def _lenient_validate(data: dict) -> IntakeResult:
    """Progressively strip problematic fields until validation passes.
    
    Local LLMs frequently return creative interpretations of the schema
    (strings where ints are expected, invented enum values, etc.). Rather
    than failing, we strip the offending nested objects and keep what works.
    """
    from pydantic import ValidationError
    from src.backend.models.intake import IntakeResult, Sleep

    # Fields to try removing on failure (least important first)
    optional_keys = ["performance", "todays_wod", "hydration", "notes", "subjective_readiness"]

    # First, try to coerce common type issues
    _coerce_types(data)

    # Try validation after coercion
    try:
        return IntakeResult.model_validate(data)
    except ValidationError:
        pass

    # Progressively strip optional fields that might be malformed
    for key in optional_keys:
        if key in data:
            backup = data.pop(key)
            try:
                return IntakeResult.model_validate(data)
            except ValidationError:
                data[key] = backup  # Put it back, try removing the next one

    meals_data = data.get("meals", [])
    if not isinstance(meals_data, list):
        meals_data = []
        
    soreness_data = data.get("soreness", [])
    if not isinstance(soreness_data, list):
        soreness_data = []

    # Nuclear option: keep only sleep + soreness + meals (the core data)
    minimal = {
        "sleep": data.get("sleep", {"quality": "not reported"}),
        "soreness": soreness_data,
        "meals": meals_data,
        "notes": f"Partial extraction — some fields had invalid format",
    }
    minimal = _repair_parsed(minimal)
    return IntakeResult.model_validate(minimal)


def _coerce_types(data: dict) -> None:
    """Attempt to coerce common type mismatches from LLM output."""
    # performance fields that should be int/float
    if "performance" in data and isinstance(data["performance"], dict):
        perf = data["performance"]
        _try_int(perf, "total_time_seconds", allow_float=True)
        _try_int(perf, "total_rounds")
        _try_int(perf, "total_reps")
        _try_int(perf, "hr_avg")
        _try_int(perf, "hr_max")
        _try_int(perf, "rpe")

    # sleep.hours should be float
    if "sleep" in data and isinstance(data["sleep"], dict):
        _try_int(data["sleep"], "hours", allow_float=True)

    # soreness severity should be int
    if "soreness" in data and isinstance(data["soreness"], list):
        for item in data["soreness"]:
            if isinstance(item, dict):
                _try_int(item, "severity")

    # hydration
    if "hydration" in data and isinstance(data["hydration"], dict):
        _try_int(data["hydration"], "water_oz", allow_float=True)
        _try_int(data["hydration"], "alcohol_drinks")


def _try_int(d: dict, key: str, allow_float: bool = False) -> None:
    """Try to convert a value to int (or float). On failure, set to None."""
    if key not in d or d[key] is None:
        return
    val = d[key]
    if isinstance(val, (int, float)):
        return  # already correct
    if isinstance(val, str):
        # Try to extract a number from strings like "8:42" or "315 reps"
        import re
        # Handle time format "M:SS" -> seconds
        time_match = re.match(r"^(\d+):(\d{2})$", val.strip())
        if time_match and key in ("total_time_seconds",):
            d[key] = int(time_match.group(1)) * 60 + int(time_match.group(2))
            return
        # Try extracting first number
        num_match = re.search(r"[\d.]+", val)
        if num_match:
            try:
                if allow_float:
                    d[key] = float(num_match.group())
                else:
                    d[key] = int(float(num_match.group()))
                return
            except (ValueError, OverflowError):
                pass
    # Can't parse — set to None
    d[key] = None
