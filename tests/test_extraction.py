import pytest
from backend.providers.llm import extract_intake, _deterministic_extractor
from backend.intake.schema import IntakeResult


def test_deterministic_extractor():
    text = "I slept pretty good, about 8 hours. My lower back is a little sore. I ate chicken and rice. I did some pull-ups."
    result = _deterministic_extractor(text)

    assert isinstance(result, IntakeResult)
    assert result.sleep.quality == "good"
    assert result.sleep.hours == 8.0
    assert len(result.soreness) == 1
    assert result.soreness[0].body_part == "lower back"
    assert len(result.meals) == 1
    assert result.meals[0].description == "chicken and rice"
    assert "pull-ups" in result.todays_wod.movements


def test_extract_intake_fallback(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "mock")
    text = "I slept pretty good, about 8 hours. My lower back is a little sore."
    result = extract_intake(text)

    assert isinstance(result, IntakeResult)
    assert result.sleep.quality == "good"
