"""GG-SIGNAL-01 — pluggable signals; dynamic selection; overall optional."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.goals import GoalGraphStore, GoalType, GraphGoalCreate, GraphGoalStatus
from backend.intake.schema import IntakeResult, Meal, Sleep, WOD
from backend.main import app
from backend.scorers.canonical import score_canonical
from backend.signals import SignalRegistry, build_context, select_signals, signals_payload
from backend.signals.providers import default_providers


client = TestClient(app)


def _intake(*, meals: list[str] | None = None) -> IntakeResult:
    return IntakeResult(
        sleep=Sleep(quality="ok", hours=7.0),
        soreness=[],
        meals=[Meal(description=m) for m in (meals or ["eggs"])],
        subjective_readiness="moderate",
        todays_wod=WOD(movements=[], raw=None),
    )


def test_providers_wrap_canonical_scorers():
    intake = _intake()
    canon = score_canonical(intake)
    reg = SignalRegistry(default_providers())
    ctx = build_context(intake, view="directive")
    for sid in ("front_rack", "sleep", "diet", "workout_preparation", "overall"):
        result = reg.get(sid).compute(ctx)
        assert result.score == canon[sid]["score"]


def test_no_goals_selects_core_plus_overall():
    intake = _intake()
    ctx = build_context(intake, view="directive")
    selected = select_signals(ctx)
    ids = [s.id for s in selected]
    assert ids[:4] == ["front_rack", "sleep", "diet", "workout_preparation"]
    assert "overall" in ids


def test_running_goal_selects_pace_and_diet_signals(tmp_path: Path):
    store = GoalGraphStore(tmp_path / "sig.sqlite3")
    store.create_goal(
        GraphGoalCreate(
            title="Improve running conditioning",
            description="Track pace over time",
            goal_type=GoalType.OUTCOME,
            metric="running_pace",
        )
    )
    store.create_goal(
        GraphGoalCreate(
            title="Improve nutrition consistency",
            metric="diet",
        )
    )
    text = "Ate beef and rice, run was good, averaged 10:30 for 3 miles."
    intake = _intake(meals=["beef", "rice"])
    ctx = build_context(intake, goal_store=store, recent_text=text, view="dashboard")
    assert any(g.status == GraphGoalStatus.IN_PROGRESS for g in ctx.active_goals)
    selected = select_signals(ctx)
    ids = {s.id for s in selected}
    assert "running_pace" in ids
    assert "diet" in ids
    assert "overall" not in ids
    pace = next(s for s in selected if s.id == "running_pace")
    assert pace.available is False


def test_signals_payload_includes_compat_scores():
    intake = _intake()
    payload = signals_payload(build_context(intake))
    assert "compat_scores" in payload
    assert "front_rack" in payload["compat_scores"]
    assert payload["selected"]


def test_api_signals_and_directive_include_signals(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from backend.config import get_settings
    import backend.main as main_mod

    get_settings.cache_clear()
    main_mod._goal_graph = GoalGraphStore(tmp_path / "api_gg.sqlite3")
    main_mod._goal_graph.create_goal(
        GraphGoalCreate(title="Running goal", metric="running_pace")
    )

    res = client.get("/api/signals", params={"text": "ran 3 miles at 10:30"})
    assert res.status_code == 200
    body = res.json()
    assert "selected" in body
    assert "compat_scores" in body

    d = client.post(
        "/api/directive",
        json={"text": "Ate beef and rice, run was good, averaged 10:30 for 3 miles."},
    )
    assert d.status_code == 200
    payload = d.json()
    assert "front_rack" in payload["scores"]
    assert payload.get("signals") and payload["signals"]["selected"]
    selected_ids = [s["id"] for s in payload["signals"]["selected"]]
    assert "running_pace" in selected_ids or "diet" in selected_ids
