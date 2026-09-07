"""Tests for alerts, goals, canonical scores, WOD, tools, charts."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.alerts import AlertEngine
from backend.charts import build_metric_trend, validate_chart_spec
from backend.goals import GoalCreate, GoalStore
from backend.health.schema import DataQuality, DataSource, Provenance
from backend.health.store import HealthMetricsStore
from backend.intake.schema import IntakeResult
from backend.main import app
from backend.reasoner.wod import negotiate_wod
from backend.scorers.canonical import score_canonical
from backend.tools import HealthQueryTools


client = TestClient(app)


def _intake(**kw) -> IntakeResult:
    data = {
        "soreness": [{"body_part": "shoulders", "severity": 4}],
        "sleep": {"quality": "poor", "hours": 5.0},
        "meals": [{"description": "toast"}],
        "todays_wod": {"movements": ["cleans", "pull-ups"], "raw": "cleans"},
        "subjective_readiness": "low",
    }
    data.update(kw)
    return IntakeResult.model_validate(data)


def test_canonical_scores_present():
    scores = score_canonical(_intake())
    for key in ("front_rack", "sleep", "diet", "workout_preparation", "overall"):
        assert key in scores
        assert 0 <= scores[key]["score"] <= 100
    assert "transitional" in scores


def test_wod_negotiation_substitutes_front_rack():
    decision = negotiate_wod(_intake())
    assert decision["status"] in {"substituted", "deferred", "scaled"}
    assert decision["reasons"]


def test_directive_api_canonical(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMORY_DB_PATH", str(tmp_path / "m.sqlite3"))
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from backend.config import get_settings
    import backend.main as main_mod
    from backend.providers.memory import LocalMemoryProvider

    get_settings.cache_clear()
    main_mod._memory = LocalMemoryProvider(tmp_path / "m.sqlite3")
    res = client.post(
        "/api/directive",
        json={
            "text": "Slept 5 hours poorly, shoulders sore 4/5, cleans and pull-ups, feeling low.",
            "speak": False,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "front_rack" in data["scores"]
    assert "workout_preparation" in data["scores"]
    assert "overall" in data["scores"]
    assert data["wod_decision"]["status"]
    assert "does not diagnose" in data["disclaimer"].lower()


def test_alerts_defaults_and_dedup(tmp_path):
    store = HealthMetricsStore(tmp_path / "h.sqlite3")
    prov = Provenance(
        source=DataSource.FIXTURE,
        recorded_at=1,
        observed_at=1,
        quality=DataQuality.MEDIUM,
        extractor="t",
    )
    # baseline points then spike
    for i, v in enumerate([60, 61, 59, 60]):
        store.upsert_point(metric="heart_rate", value=v, observed_at=float(i), provenance=prov, day=f"2026-09-0{i+1}")
    store.upsert_point(metric="heart_rate", value=210, observed_at=10.0, provenance=prov, day="2026-09-07")
    engine = AlertEngine(tmp_path / "a.sqlite3", metrics=store)
    fired = engine.evaluate()
    assert any(a.rule_id == "heart_rate_high" for a in fired)
    again = engine.evaluate()
    assert again == []  # duplicate suppressed


def test_goals_confirm_flow(tmp_path):
    store = HealthMetricsStore(tmp_path / "hg.sqlite3")
    prov = Provenance(
        source=DataSource.MANUAL_TEXT,
        recorded_at=1,
        observed_at=1,
        quality=DataQuality.HIGH,
        extractor="manual",
    )
    store.upsert_point(metric="body_fat_pct", value=17.0, provenance=prov, day="2026-09-07")
    goals = GoalStore(tmp_path / "g.sqlite3", metrics=store)
    g = goals.create(GoalCreate(metric="body_fat_pct", target=18.0, direction="lte"))
    ev = goals.evaluate(g.goal_id)
    assert ev["possible_completion"] is True
    done = goals.confirm_complete(g.goal_id)
    assert done.status.value == "completed"
    assert done.history


def test_tools_and_charts(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from backend.config import get_settings

    get_settings.cache_clear()
    store = HealthMetricsStore()
    store.ingest_fixture()
    tools = HealthQueryTools(metrics=store)
    assert "resting_hr" in tools.list_metrics()["metrics"]
    latest = tools.latest("resting_hr")
    assert latest["source"]
    series = tools.series("resting_hr")
    assert series["points"]
    chart = build_metric_trend("resting_hr", metrics=store)
    assert chart.type in {"metric_trend", "sleep_trend", "body_comp_trend", "activity_load"}
    try:
        validate_chart_spec({"type": "metric_trend", "title": "x", "html": "<script>"})
        assert False
    except Exception:
        pass
