"""GG-SCHEMA-01 — Goal Graph hierarchy, suggestions, audit (GL0)."""

from __future__ import annotations

from pathlib import Path

from backend.goals import (
    ContributionEffect,
    GoalGraphStore,
    GoalOrigin,
    GoalType,
    GraphGoalCreate,
    GraphTaskCreate,
    SuggestionCreate,
    SuggestionDecision,
    SuggestionKind,
    TaskStatus,
)


def test_goal_tree_and_tasks(tmp_path: Path):
    store = GoalGraphStore(tmp_path / "gg.sqlite3")
    assert store.schema_version() == 1

    vision = store.create_goal(
        GraphGoalCreate(
            title="Maintain functional longevity",
            goal_type=GoalType.OUTCOME,
            origin=GoalOrigin.MANUAL,
            original_wording="I want to feel healthier long-term",
        )
    )
    child = store.create_goal(
        GraphGoalCreate(
            title="Improve running conditioning",
            parent_goal_id=vision.id,
            goal_type=GoalType.OUTCOME,
            metric="running_pace",
            direction=None,
        )
    )
    task = store.create_task(
        GraphTaskCreate(
            title="Record one run per week",
            goal_id=child.id,
            status=TaskStatus.PLANNED,
        )
    )
    store.add_evidence_link(
        kind="journal",
        ref="log-abc",
        goal_id=child.id,
        snippet="averaged 10:30 for 3 miles",
    )

    tree = store.goal_tree()
    assert len(tree) == 1
    assert tree[0]["goal"]["id"] == vision.id
    assert tree[0]["children"][0]["goal"]["id"] == child.id
    assert any(t.id == task.id for t in store.list_tasks(goal_id=child.id))
    assert vision.original_wording.startswith("I want to feel")


def test_contribution_and_suggestion_require_decision(tmp_path: Path):
    store = GoalGraphStore(tmp_path / "gg2.sqlite3")
    goal = store.create_goal(GraphGoalCreate(title="Improve running conditioning"))
    contrib = store.record_contribution(
        journal_ref="entry-1",
        goal_id=goal.id,
        effect=ContributionEffect.POSITIVE,
        evidence=["3-mile run", "Average pace 10:30"],
        assumptions=["User self-report is accurate"],
        confidence="high",
        proposed_update="Add run to conditioning history",
    )
    assert contrib.user_decision == SuggestionDecision.PENDING

    decided = store.decide_contribution(contrib.id, SuggestionDecision.APPROVED)
    assert decided.user_decision == SuggestionDecision.APPROVED
    assert decided.decided_at is not None

    sug = store.propose_suggestion(
        SuggestionCreate(
            kind=SuggestionKind.CREATE_TASK,
            title="Review weekly running pace",
            reason="A new run was recorded",
            evidence=["journal entry-1"],
            affected_goal_id=goal.id,
            payload={"title": "Review weekly running pace"},
        )
    )
    assert sug.decision == SuggestionDecision.PENDING
    assert len(store.list_tasks(goal_id=goal.id)) == 0  # no silent create

    approved = store.decide_suggestion(sug.id, SuggestionDecision.APPROVED)
    assert approved.decision == SuggestionDecision.APPROVED
    tasks = store.list_tasks(goal_id=goal.id)
    assert any(t.title == "Review weekly running pace" for t in tasks)

    audit = store.audit_history(limit=20)
    actions = {a.action for a in audit}
    assert "created" in actions or any(a.action.startswith("decision:") for a in audit)
    assert any(a.entity_type == "suggestion" for a in audit)


def test_reject_suggestion_does_not_create_task(tmp_path: Path):
    store = GoalGraphStore(tmp_path / "gg3.sqlite3")
    goal = store.create_goal(GraphGoalCreate(title="Nutrition consistency"))
    sug = store.propose_suggestion(
        SuggestionCreate(
            kind=SuggestionKind.CREATE_TASK,
            title="Log meals for 7 days",
            reason="Beef and rice logged",
            affected_goal_id=goal.id,
            payload={"title": "Log meals for 7 days"},
        )
    )
    store.decide_suggestion(sug.id, SuggestionDecision.REJECTED)
    assert store.list_tasks(goal_id=goal.id) == []


def test_snapshot_includes_tree(tmp_path: Path):
    store = GoalGraphStore(tmp_path / "gg4.sqlite3")
    store.create_goal(GraphGoalCreate(title="Root"))
    snap = store.snapshot()
    assert snap["schema_version"] == 1
    assert snap["goals"]
    assert "goal_tree" in snap
