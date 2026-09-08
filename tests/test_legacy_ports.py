"""Legacy residual ports — guardrails, Fitbit honesty, patterns, OCR status."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from backend.connectors.calendar_signals import derive_calendar_signals, summarize_calendar_signals
from backend.connectors.fitbit_oauth import status as fitbit_status
from backend.connectors.takeout import ingest_takeout_bytes
from backend.health.store import HealthMetricsStore
from backend.intake.schema import Hydration, IntakeResult, Meal, Performance
from backend.main import app
from backend.patterns.correlations import correlate_metrics
from backend.safety.guardrails import apply_guardrails
from backend.scorers.canonical import score_canonical
from backend.scorers.hydration import score_hydration
from backend.scorers.performance import score_performance

client = TestClient(app)


def test_guardrails_rewrite_prescriptive():
    out = apply_guardrails("You should rest today. Heart rate is fine.")
    assert "you should" not in out.lower()
    assert "may be worth considering" in out.lower()


def test_guardrails_keeps_goal_metric_sentence():
    out = apply_guardrails("You should raise steps today.", active_goal_metrics=["steps"])
    assert "you should" in out.lower()


def test_fitbit_status_needs_credentials(monkeypatch):
    monkeypatch.delenv("FITBIT_CLIENT_ID", raising=False)
    monkeypatch.delenv("FITBIT_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("AEGIS_FITBIT_CLIENT_ID", raising=False)
    monkeypatch.delenv("AEGIS_FITBIT_CLIENT_SECRET", raising=False)
    # Clear any cached env by calling module functions after env clear
    st = fitbit_status()
    assert st["authenticated"] is False
    assert st["integration_state"] == "needs_credentials"
    assert st["live_oauth"] is False
    res = client.get("/api/fitbit/status")
    assert res.status_code == 200
    assert res.json()["authenticated"] is False


def test_calendar_signal_derivation():
    events = [
        {
            "name": "Early flight",
            "start": "2026-09-07T04:30:00+00:00",
            "end": "2026-09-07T05:00:00+00:00",
            "location": "Home",
        },
        {
            "name": "Late call",
            "start": "2026-09-07T23:30:00+00:00",
            "end": "2026-09-07T23:45:00+00:00",
        },
    ]
    out = summarize_calendar_signals(events)
    assert out["early_events"] >= 1
    assert out["late_events"] >= 1
    annotated = derive_calendar_signals(events)
    assert annotated[0]["derived_signals"].get("early_morning") is True


def test_takeout_json_datapoints(tmp_path: Path):
    buf = io.BytesIO()
    payload = {
        "Data Points": [
            {
                "startTimeNanos": str(int(1_725_700_000_000_000_000)),
                "fitValue": [{"value": {"fpVal": 8500}}],
            }
        ]
    }
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("Takeout/Fit/step_count.json", json.dumps(payload))
    store = HealthMetricsStore(tmp_path / "t.sqlite3")
    result = ingest_takeout_bytes(store, buf.getvalue())
    assert result["written"] >= 1
    assert "steps" in result["metrics"]
    assert store.latest("steps").value == 8500


def test_hydration_performance_factors():
    intake = IntakeResult.model_validate(
        {
            "soreness": [],
            "sleep": {"quality": "good", "hours": 8},
            "meals": [Meal(description="chicken", protein_g=40)],
            "todays_wod": {"movements": ["squats"], "raw": "squats"},
            "subjective_readiness": "high",
            "hydration": Hydration(water_oz=80, alcohol_drinks=0),
            "performance": Performance(rpe=7, rx=True, feel="strong"),
        }
    )
    assert score_hydration(intake)["score"] >= 90
    assert score_performance(intake)["score"] is not None
    scores = score_canonical(intake)
    assert "factors" in scores
    assert scores["factors"]["hydration"]["score"] is not None


def test_patterns_api_and_correlate(tmp_path: Path, monkeypatch):
    # Use default store via API after ingesting fixture
    client.post("/api/ingest/fixture")
    res = client.get("/api/patterns/trend/steps")
    assert res.status_code == 200
    assert "direction" in res.json()
    res2 = client.get("/api/patterns/correlate", params={"metric_a": "steps", "metric_b": "calories"})
    assert res2.status_code == 200
    body = res2.json()
    assert body["metric_a"] == "steps"
    # pearson may be None with sparse overlap — still structured
    assert "n" in body


def test_fitindex_ocr_disabled_without_llava():
    # Tiny fake png bytes — OCR should fail soft without llava
    res = client.post(
        "/api/fitindex/ocr",
        files={"file": ("shot.png", b"\x89PNG\r\n\x1a\nnot-an-image", "image/png")},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is False
    assert data["draft"] is None


def test_rich_context_and_chat_session():
    ctx = client.get("/api/context/screen").json()
    assert "vitals_24h" in ctx
    assert "text" in ctx
    r1 = client.post("/api/chat", json={"message": "any calendar travel today?"})
    assert r1.status_code == 200
    sid = r1.json()["session_id"]
    r2 = client.post("/api/chat", json={"message": "and goals?", "session_id": sid})
    assert r2.json()["session_id"] == sid
    sessions = client.get("/api/chat/sessions").json()
    assert sessions["sessions"]
