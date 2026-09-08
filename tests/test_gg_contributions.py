"""GG-CONTRIB-01 / GG-SUGGEST-01 — journal contribution engine + HITL."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.goals import (
    ContributionEffect,
    GoalGraphStore,
    GraphGoalCreate,
    SuggestionDecision,
    analyze_journal_entry,
    persist_analysis_as_pending,
)
from backend.main import app


client = TestClient(app)

BEEF_RICE_RUN = "Ate beef and rice, run was good, averaged 10:30 for 3 miles."


def _seed_goals(store: GoalGraphStore) -> dict[str, str]:
    conditioning = store.create_goal(
        GraphGoalCreate(
            title="Improve running conditioning",
            description="Build endurance and track pace",
            metric="running_pace",
        )
    )
    nutrition = store.create_goal(
        GraphGoalCreate(
            title="Improve nutrition consistency",
            metric="diet",
        )
    )
    recovery = store.create_goal(
        GraphGoalCreate(
            title="Improve recovery",
            description="Sleep and HRV focused recovery",
            metric="recovery",
        )
    )
    body = store.create_goal(
        GraphGoalCreate(
            title="Reduce body fat",
            metric="body_composition",
        )
    )
    return {
        "conditioning": conditioning.id,
        "nutrition": nutrition.id,
        "recovery": recovery.id,
        "body": body.id,
    }


def test_beef_rice_run_contributions(tmp_path: Path):
    store = GoalGraphStore(tmp_path / "c1.sqlite3")
    ids = _seed_goals(store)
    analysis = analyze_journal_entry(
        BEEF_RICE_RUN, store=store, journal_ref="entry-1", memory_hits=[]
    )
    by_goal = {c.goal_id: c for c in analysis.contributions}

    assert by_goal[ids["conditioning"]].effect == ContributionEffect.POSITIVE
    assert any("pace" in e.lower() for e in by_goal[ids["conditioning"]].evidence)

    assert by_goal[ids["nutrition"]].effect == ContributionEffect.PARTIAL
    assert any("beef" in e.lower() or "rice" in e.lower() for e in by_goal[ids["nutrition"]].evidence)

    assert by_goal[ids["recovery"]].effect == ContributionEffect.INSUFFICIENT_EVIDENCE
    assert by_goal[ids["body"]].effect == ContributionEffect.INSUFFICIENT_EVIDENCE

    titles = {t.title for t in analysis.task_suggestions}
    assert "Review weekly running pace" in titles
    assert analysis.to_dict()["applied"] is False
    assert analysis.to_dict()["human_in_the_loop"] is True


def test_persist_pending_then_approve_creates_task(tmp_path: Path):
    store = GoalGraphStore(tmp_path / "c2.sqlite3")
    ids = _seed_goals(store)
    analysis = analyze_journal_entry(BEEF_RICE_RUN, store=store, journal_ref="entry-2")
    persisted = persist_analysis_as_pending(analysis, store=store)
    assert persisted["persisted"]["contribution_ids"]
    assert persisted["persisted"]["suggestion_ids"]

    # No tasks until approval
    assert store.list_tasks(goal_id=ids["conditioning"]) == []

    pending = store.list_suggestions(pending_only=True)
    assert pending
    pace_sug = next(s for s in pending if "pace" in s.title.lower())
    store.decide_suggestion(pace_sug.id, SuggestionDecision.APPROVED)
    tasks = store.list_tasks(goal_id=ids["conditioning"])
    assert any("pace" in t.title.lower() for t in tasks)

    # Reject path does not create
    remaining = [s for s in store.list_suggestions(pending_only=True) if "protein" in s.title.lower()]
    if remaining:
        store.decide_suggestion(remaining[0].id, SuggestionDecision.REJECTED)
        assert not any(
            "protein" in t.title.lower() for t in store.list_tasks(goal_id=ids["nutrition"])
        )


def test_no_goals_returns_note(tmp_path: Path):
    store = GoalGraphStore(tmp_path / "c3.sqlite3")
    analysis = analyze_journal_entry(BEEF_RICE_RUN, store=store, journal_ref="e")
    assert analysis.contributions == []
    assert any("No active goals" in n for n in analysis.notes)


def test_api_analyze_and_decide(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from backend.config import get_settings
    import backend.main as main_mod

    get_settings.cache_clear()
    main_mod._goal_graph = GoalGraphStore(tmp_path / "api_c.sqlite3")
    _seed_goals(main_mod._goal_graph)

    res = client.post(
        "/api/goal-graph/analyze",
        json={"text": BEEF_RICE_RUN, "persist": True},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["goal_contributions"]
    assert body["human_in_the_loop"] is True
    effects = {c["goal"]: c["effect"] for c in body["goal_contributions"]}
    assert any(v == "positive" for v in effects.values())
    assert any(v == "partial" for v in effects.values())
    assert any(v == "insufficient_evidence" for v in effects.values())

    sug = client.get("/api/goal-graph/suggestions?pending_only=true")
    assert sug.status_code == 200
    suggestions = sug.json()["suggestions"]
    assert suggestions
    sid = suggestions[0]["id"]
    decided = client.post(
        f"/api/goal-graph/suggestions/{sid}/decide",
        json={"decision": "approved"},
    )
    assert decided.status_code == 200
    assert decided.json()["decision"] in {"approved", "edited"}

    contribs = client.get("/api/goal-graph/contributions?pending_only=true")
    assert contribs.status_code == 200
    if contribs.json()["contributions"]:
        cid = contribs.json()["contributions"][0]["id"]
        cdec = client.post(
            f"/api/goal-graph/contributions/{cid}/decide",
            json={"decision": "approved"},
        )
        assert cdec.status_code == 200
