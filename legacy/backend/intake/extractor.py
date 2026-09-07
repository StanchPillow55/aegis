"""Claude intake extractor (SC-ANTH-01).

`extract(transcript)` turns a spoken daily update into a validated
`IntakeResult` using Claude tool-use: Claude is given a single forced tool whose
input schema IS the `IntakeResult` JSON Schema, so the model returns structured,
typed arguments rather than free-form prose we'd have to parse.

Design notes:
- `model` comes from config (`Settings.anthropic_model`). Extraction runs at
  `temperature=0` for determinism, which requires a sampling-capable model
  (Sonnet/Haiku tier) — `claude-opus-4-8`/4.7/`claude-fable-5` reject
  `temperature` with a 400.
- `max_tokens` is deliberately modest to respect the $30 Claude budget; the
  tool arguments for one update are small.
- `client`/`model` are injectable so the extraction logic can be unit-tested
  without a network call or a fully-populated `.env`.
"""

from __future__ import annotations

from typing import Any

import anthropic

from backend.config import get_settings
from backend.intake.schema import IntakeResult

# Modest cap: one update's structured args are small; keep token spend low.
_MAX_TOKENS = 1024

_TOOL_NAME = "record_intake"

_SYSTEM = (
    "You are the intake parser for a voice-first training copilot. The user "
    "speaks a short daily update covering how they feel, how they slept, what "
    "they've eaten, and today's workout. Extract ONLY what is stated or clearly "
    "implied — do not invent details. Call the `record_intake` tool exactly "
    "once with the structured result. Field rules: each soreness `severity` is "
    "an integer 1 (barely sore) to 5 (severe); `protein_g` is grams of protein "
    "as an integer, or omit it if not stated or estimable; set the WOD `raw` "
    "field to the verbatim workout text when present. For `subjective_readiness`, "
    "infer a short label ('low' / 'moderate' / 'high') from the overall tone "
    "(poor sleep and soreness imply lower readiness)."
)


def _tool_definition() -> dict[str, Any]:
    """Build the forced tool whose input schema is the IntakeResult schema."""
    return {
        "name": _TOOL_NAME,
        "description": (
            "Record the structured daily training/recovery/nutrition intake "
            "parsed from the athlete's spoken update."
        ),
        "input_schema": IntakeResult.model_json_schema(),
    }


def extract(
    transcript: str,
    *,
    client: anthropic.Anthropic | None = None,
    model: str | None = None,
) -> IntakeResult:
    """Parse a spoken daily update into a validated `IntakeResult`.

    Args:
        transcript: The athlete's spoken (or fallback typed) daily update.
        client: Optional Anthropic client (injected for tests / custom auth).
        model: Optional model id override (defaults to `Settings.anthropic_model`).

    Returns:
        A validated `IntakeResult`.

    Raises:
        ValueError: if Claude returned no `record_intake` tool call.
        pydantic.ValidationError: if the tool arguments don't match the schema.
    """
    settings = None
    if model is None:
        settings = get_settings()
        model = settings.anthropic_model
    if client is None:
        settings = settings or get_settings()
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    response = client.messages.create(
        model=model,
        max_tokens=_MAX_TOKENS,
        temperature=0,
        system=_SYSTEM,
        tools=[_tool_definition()],
        tool_choice={"type": "tool", "name": _TOOL_NAME},
        messages=[{"role": "user", "content": transcript}],
    )

    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == _TOOL_NAME:
            return IntakeResult.model_validate(block.input)

    raise ValueError(
        f"Claude returned no '{_TOOL_NAME}' tool call (stop_reason="
        f"{getattr(response, 'stop_reason', None)!r})."
    )
