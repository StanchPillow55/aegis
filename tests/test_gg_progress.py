"""GG-PROGRESS-01 — horizons, bands, explain, create-task-from-chart (GL4)."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from backend.goals import GoalGraphStore, GraphGoalCreate, GraphTaskCreate, TaskType
from backend.goals.progress import (
    build_progress_view,
    explain_progress,
    propose_task_from_chart,
)
from backend.health.schema import DataQuality, DataSource, Provenance
from backend.health.store import HealthMetricsStore
from backend.main import app


client = TestClient(app)


def _seed_metric(store: HealthMetricsStore, metric: str = "sleep_hours") -> None:
    now = time.time()
    for i, val in enumerate([6.0, 6.5, 7.0, 7.2, 6.8]):
        observed = now - (4 - i) * 86400
        store.upsert_point(
            metric=metric,
            value=val,
            unit="hours" if "sleep" in metric else "count",
            observed_at=observed,
            provenance=Provenance(
                source=DataSource.MANUAL_TEXT,
                quality=DataQuality.MEDIUM,
                recorded_at=now,
                observed_at=observed,
            ),
        )


def test_progress_horizons_and_bands(tmp_path: Path):
    metrics = HealthMetricsStore(tmp_path / "m.sqlite3")
    _seed_metric(metrics)
    graph = GoalGraphStore(tmp_path / "g.sqlite3")
    goal = graph.create_goal(
        GraphGoalCreate(
            title="Sleep consistency",
            metric="sleep_hours",
            target=7.5,
        )
    )
    graph.create_task(
        GraphTaskCreate(
            title="Milestone: 7h streak",
            goal_id=goal.id,
            task_type=TaskType.MILESTONE,
        )
    )
    view = build_progress_view(
        "sleep_hours",
        horizon="week",
        metrics=metrics,
        graph=graph,
    )
    assert view["horizon"] == "week"
    assert view["chart"]["series"][0]["points"]
    assert any(b["target"] == 7.5 for b in view["goal_bands"])
    assert any("7h" in m["title"] for m in view["milestones"])
    assert "missing" in view
    assert view["language"]["observation"]


def test_explain_and_create_task_hitl(tmp_path: Path):
    metrics = HealthMetricsStore(tmp_path / "m2.sqlite3")
    _seed_metric(metrics)
    graph = GoalGraphStore(tmp_path / "g2.sqlite3")
    graph.create_goal(
        GraphGoalCreate(title="Sleep consistency", metric="sleep_hours", target=7.5)
    )
    view = build_progress_view("sleep_hours", horizon="month", metrics=metrics, graph=graph)
    explained = explain_progress(view)
    assert "Observed" in explained["explanation"] or "Insufficient" in explained["explanation"]
    assert explained["kind"] == "derived_interpretation_over_observations"
    assert explained["evidence"]["point_count"] >= 1

    proposed = propose_task_from_chart(
        graph=graph, metric="sleep_hours", horizon="month"
    )
    assert proposed["applied"] is False
    assert proposed["human_in_the_loop"] is True
    assert proposed["suggestion"]["decision"] == "pending"
    assert graph.list_tasks() == []  # no silent create


def test_api_progress_explain_and_task(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from backend.config import get_settings
    import backend.main as main_mod

    get_settings.cache_clear()
    metrics = HealthMetricsStore(tmp_path / "api_m.sqlite3")
    _seed_metric(metrics, "steps")
    graph = GoalGraphStore(tmp_path / "api_g.sqlite3")
    graph.create_goal(GraphGoalCreate(title="Move more", metric="steps", target=8000))
    main_mod._metrics = metrics
    main_mod._goal_graph = graph

    prog = client.get("/api/progress/steps?horizon=week")
    assert prog.status_code == 200
    body = prog.json()
    assert body["horizon"] == "week"
    assert "goal_bands" in body

    expl = client.post("/api/progress/steps/explain?horizon=week")
    assert expl.status_code == 200
    assert expl.json()["explanation"]

    task = client.post(
        "/api/progress/steps/create-task",
        json={"horizon": "week"},
    )
    assert task.status_code == 200
    assert task.json()["applied"] is False
    pending = client.get("/api/goal-graph/suggestions?pending_only=true")
    assert pending.json()["suggestions"]


def test_progress_ui_markup():
    html = client.get("/").text
    assert 'data-horizon="today"' in html
    assert 'data-horizon="week"' in html
    assert 'data-horizon="month"' in html
    assert 'id="chart-explain-btn"' in html
    assert 'id="chart-task-btn"' in html
    js = client.get("/static/app.js").text
    assert "/api/progress/" in js
    assert "chartHorizon" in js
    assert "create-task" in js
