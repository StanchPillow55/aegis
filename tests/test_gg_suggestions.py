"""GG-SUGGEST-01 — HITL approve / edit / reject / defer; no silent mutations."""

from __future__ import annotations

from pathlib import Path

from backend.goals import (
    GoalGraphStore,
    GraphGoalCreate,
    SuggestionCreate,
    SuggestionDecision,
    SuggestionKind,
    analyze_journal_entry,
    persist_analysis_as_pending,
)


BEEF_RICE_RUN = "Ate beef and rice, run was good, averaged 10:30 for 3 miles."


def _seed_conditioning(store: GoalGraphStore) -> str:
    return store.create_goal(
        GraphGoalCreate(
            title="Improve running conditioning",
            description="Build endurance and track pace",
            metric="running_pace",
        )
    ).id


def test_reject_and_defer_do_not_create_tasks(tmp_path: Path):
    store = GoalGraphStore(tmp_path / "s1.sqlite3")
    goal_id = _seed_conditioning(store)
    analysis = analyze_journal_entry(BEEF_RICE_RUN, store=store, journal_ref="e1")
    persist_analysis_as_pending(analysis, store=store)
    pending = store.list_suggestions(pending_only=True)
    assert pending
    first, *rest = pending
    store.decide_suggestion(first.id, SuggestionDecision.REJECTED)
    assert store.list_tasks(goal_id=goal_id) == []
    if rest:
        store.decide_suggestion(rest[0].id, SuggestionDecision.DEFERRED)
        assert store.list_tasks(goal_id=goal_id) == []
        assert store.list_suggestions(pending_only=True) == []


def test_edit_then_approve_uses_edited_payload(tmp_path: Path):
    store = GoalGraphStore(tmp_path / "s2.sqlite3")
    goal_id = _seed_conditioning(store)
    sug = store.propose_suggestion(
        SuggestionCreate(
            kind=SuggestionKind.CREATE_TASK,
            title="Review weekly running pace",
            reason="from journal",
            evidence=["pace"],
            assumptions=["draft"],
            confidence="medium",
            affected_goal_id=goal_id,
            payload={"title": "Review weekly running pace", "description": "old"},
        )
    )
    decided = store.decide_suggestion(
        sug.id,
        SuggestionDecision.APPROVED,
        edited_payload={
            "title": "Log Sunday long run",
            "description": "user-edited title",
        },
    )
    assert decided.decision == SuggestionDecision.EDITED
    tasks = store.list_tasks(goal_id=goal_id)
    assert len(tasks) == 1
    assert tasks[0].title == "Log Sunday long run"
    assert tasks[0].user_approved is True


def test_audit_preserves_suggestion_revision(tmp_path: Path):
    store = GoalGraphStore(tmp_path / "s3.sqlite3")
    goal_id = _seed_conditioning(store)
    sug = store.propose_suggestion(
        SuggestionCreate(
            kind=SuggestionKind.CREATE_TASK,
            title="Review weekly protein average",
            reason="meal",
            evidence=["beef"],
            affected_goal_id=goal_id,
            payload={"title": "Review weekly protein average"},
        )
    )
    store.decide_suggestion(sug.id, SuggestionDecision.REJECTED)
    audit = store.audit_history(limit=50)
    actions = {a.action for a in audit if a.entity_id == sug.id}
    assert "proposed" in actions
    assert "decision:rejected" in actions
    # Rejected → still no tasks
    assert store.list_tasks(goal_id=goal_id) == []
