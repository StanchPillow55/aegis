"""GG-SAFETY-01 — observation vs interpretation; insufficient evidence; no-goals path."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.goals import GoalGraphStore, GraphGoalCreate, analyze_journal_entry
from backend.goals.progress import build_progress_view, explain_progress
from backend.health.schema import DataQuality, DataSource, Provenance, SAFETY_DISCLAIMER
from backend.health.store import HealthMetricsStore
from backend.main import app


client = TestClient(app)


def test_explain_distinguishes_observation_vs_interpretation(tmp_path: Path):
    metrics = HealthMetricsStore(tmp_path / "s.sqlite3")
    now = __import__("time").time()
    for i, val in enumerate([6.0, 7.0]):
        observed = now - (1 - i) * 86400
        metrics.upsert_point(
            metric="sleep_hours",
            value=val,
            observed_at=observed,
            provenance=Provenance(
                source=DataSource.MANUAL_TEXT,
                quality=DataQuality.MEDIUM,
                recorded_at=now,
                observed_at=observed,
            ),
        )
    view = build_progress_view("sleep_hours", horizon="week", metrics=metrics)
    explained = explain_progress(view)
    text = explained["explanation"].lower()
    assert "observed" in text
    assert "interpretation" in text or "derived" in text
    assert "not medical advice" in text
    assert explained["kind"] == "derived_interpretation_over_observations"

    empty = build_progress_view("hrv", horizon="week", metrics=metrics)
    insuff = explain_progress(empty)
    assert "insufficient" in insuff["explanation"].lower()


def test_journal_insufficient_evidence_explicit(tmp_path: Path):
    store = GoalGraphStore(tmp_path / "g.sqlite3")
    store.create_goal(
        GraphGoalCreate(title="Improve recovery", metric="recovery", description="HRV rest")
    )
    store.create_goal(
        GraphGoalCreate(title="Reduce body fat", metric="body_composition")
    )
    analysis = analyze_journal_entry(
        "Ate beef and rice, run was good, averaged 10:30 for 3 miles.",
        store=store,
        journal_ref="j1",
    )
    effects = {c.goal_title: c.effect.value for c in analysis.contributions}
    assert any(v == "insufficient_evidence" for v in effects.values())
    d = analysis.to_dict()
    assert d["applied"] is False
    assert d["human_in_the_loop"] is True


def test_directive_works_with_no_goals(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from backend.config import get_settings
    import backend.main as main_mod

    get_settings.cache_clear()
    main_mod._goal_graph = GoalGraphStore(tmp_path / "empty.sqlite3")

    res = client.post(
        "/api/directive",
        json={"text": "Slept 7 hours, feeling ready for a light session.", "speak": False},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["directive"]
    assert SAFETY_DISCLAIMER.split(".")[0] in body["disclaimer"] or "non-medical" in body[
        "disclaimer"
    ].lower()
    # Analysis may be empty/notes-only but must not crash or claim applied mutations
    ga = body.get("goal_analysis")
    if ga:
        assert ga.get("applied") is False
        assert ga.get("human_in_the_loop") is True
