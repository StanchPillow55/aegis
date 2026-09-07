"""Claude Haiku extraction fallback (optional cloud path)."""

from typing import Any, Optional

import anthropic

from src.backend.config import get_settings
from src.backend.models.intake import IntakeResult

_SYSTEM = (
    "You are the intake parser for a voice-first training copilot. The user "
    "speaks a short daily update covering sleep, soreness, nutrition, hydration, "
    "and workout performance. Extract ONLY what is stated or clearly implied. "
    "Call the record_intake tool exactly once."
)

_TOOL_NAME = "record_intake"


def _tool_definition() -> dict[str, Any]:
    return {
        "name": _TOOL_NAME,
        "description": "Record structured daily training/recovery/nutrition intake.",
        "input_schema": IntakeResult.model_json_schema(),
    }


async def extract_with_claude(
    text: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> IntakeResult:
    """Extract structured intake using Claude tool-use."""
    settings = get_settings()
    key = api_key or settings.anthropic_api_key
    if not key:
        raise ValueError("ANTHROPIC_API_KEY not configured")

    mdl = model or settings.anthropic_model
    client = anthropic.Anthropic(api_key=key)

    response = client.messages.create(
        model=mdl,
        max_tokens=1024,
        temperature=0,
        system=_SYSTEM,
        tools=[_tool_definition()],
        tool_choice={"type": "tool", "name": _TOOL_NAME},
        messages=[{"role": "user", "content": text}],
    )

    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == _TOOL_NAME:
            return IntakeResult.model_validate(block.input)

    raise ValueError("Claude returned no tool call")
