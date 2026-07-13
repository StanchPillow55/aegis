"""SC-ANTH-01 — Claude intake extractor tests.

Two layers:

1. `test_extract_binds_tool_output` — deterministic, no network. A fake
   Anthropic client returns a canned `record_intake` tool call; we assert
   `extract()` binds it into a valid `IntakeResult` with populated fields.
   This always runs and pins the tool-output -> typed-model wiring.

2. `test_live_extraction_on_demo_log` — the real SC-ANTH-01 acceptance check:
   Claude parses the demo transcript into valid typed JSON. Skipped unless
   `ANTHROPIC_API_KEY` is set, so `pytest -q` stays green offline while still
   providing real evidence when a key is present.
"""

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.intake.extractor import extract
from backend.intake.schema import IntakeResult

DEMO_LOG = (Path(__file__).parent / "fixtures" / "demo_log.txt").read_text().strip()


class _FakeMessages:
    def __init__(self, tool_input: dict):
        self._tool_input = tool_input

    def create(self, **kwargs):
        # Mirror the SDK: response.content is a list of typed blocks.
        block = SimpleNamespace(
            type="tool_use", name="record_intake", input=self._tool_input
        )
        return SimpleNamespace(content=[block], stop_reason="tool_use")


class _FakeClient:
    def __init__(self, tool_input: dict):
        self.messages = _FakeMessages(tool_input)


def test_extract_binds_tool_output():
    canned = {
        "soreness": [{"body_part": "forearms", "severity": 4}],
        "sleep": {"quality": "poor"},
        "meals": [{"description": "chicken and rice", "protein_g": 40}],
        "todays_wod": {"movements": ["cleans", "pull-ups", "biking"]},
        "subjective_readiness": "low",
    }
    result = extract(DEMO_LOG, client=_FakeClient(canned), model="test-model")

    assert isinstance(result, IntakeResult)
    assert result.todays_wod.movements == ["cleans", "pull-ups", "biking"]
    assert result.soreness and result.soreness[0].body_part == "forearms"
    assert 1 <= result.soreness[0].severity <= 5
    assert result.sleep.quality == "poor"
    assert result.meals and "chicken" in result.meals[0].description.lower()
    assert result.subjective_readiness == "low"


def test_extract_raises_without_tool_call():
    """If Claude returns no tool call, extract() fails loudly rather than guessing."""

    class _NoToolClient:
        messages = SimpleNamespace(
            create=lambda **kw: SimpleNamespace(
                content=[SimpleNamespace(type="text", text="...")],
                stop_reason="end_turn",
            )
        )

    with pytest.raises(ValueError):
        extract(DEMO_LOG, client=_NoToolClient(), model="test-model")


@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set; skipping live Claude extraction.",
)
def test_live_extraction_on_demo_log():
    import anthropic

    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
    result = extract(DEMO_LOG, client=anthropic.Anthropic(), model=model)

    assert isinstance(result, IntakeResult)
    # WOD movements — the three named movements should be captured.
    movements = " ".join(m.lower() for m in result.todays_wod.movements)
    assert "clean" in movements
    assert "pull" in movements
    assert "bik" in movements or "bike" in movements
    # Recovery / nutrition / readiness all populated.
    assert any("forearm" in s.body_part.lower() for s in result.soreness)
    assert all(1 <= s.severity <= 5 for s in result.soreness)
    assert result.sleep.quality.strip() != ""
    assert any("chicken" in m.description.lower() for m in result.meals)
    assert result.subjective_readiness.strip() != ""
