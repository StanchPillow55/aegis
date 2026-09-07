import sys
from unittest.mock import MagicMock


import pytest
from fastapi.testclient import TestClient
from src.backend.main import app
from src.backend.safety.guardrails import apply_guardrails
from src.backend.importers.google_calendar import derive_signals

client = TestClient(app)

from unittest.mock import patch
from src.backend.models.intake import IntakeResult, Sleep

@patch("src.backend.api.intake.extract_with_ollama")
def test_preservation_intake(mock_extract):
    """Observe: POST /api/intake with valid payload on unfixed code (non-buggy path) returns 200 with scoring data"""
    mock_extract.return_value = IntakeResult(sleep=Sleep(quality="good"))
    payload = {
        "text": "I woke up at 6am feeling great. I did a 30 minute run."
    }
    response = client.post("/api/intake", data=payload, headers={"X-User-ID": "test_user"})
    assert response.status_code == 200
    data = response.json()
    assert "scores" in data

def test_preservation_trends():
    """Observe: GET /api/trends with valid date range returns score time-series rows"""
    response = client.get("/api/trends/scores?start=2024-01-01&end=2024-01-07", headers={"X-User-ID": "test_user"})
    assert response.status_code == 200
    assert "scores" in response.json()

def test_preservation_guardrails():
    """Observe: apply_guardrails returns the original string unchanged for neutral LLM responses"""
    input_text = "Your readiness looks good."
    assert apply_guardrails(input_text) == input_text
    
    neutral_text = "I have noted your activities for the day."
    assert apply_guardrails(neutral_text) == neutral_text

def test_preservation_calendar_signals():
    """Observe: derive_signals([event]) with an early-morning event returns early_morning: True signal"""
    from src.backend.importers.google_calendar import parse_events
    event = {
        "start": {"dateTime": "2024-01-01T05:00:00Z"},
        "end": {"dateTime": "2024-01-01T06:00:00Z"},
        "summary": "Morning workout"
    }
    signals = parse_events([event])[0].derived_signals
    assert signals.get("early_morning") is True
