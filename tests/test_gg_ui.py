"""GG-UI-01 — Goal tree, task views, editor, suggestion review (GL3)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.goals import (
    GoalGraphStore,
    GraphGoalCreate,
    GraphTaskCreate,
    SuggestionCreate,
    SuggestionDecision,
    SuggestionKind,
    TaskStatus,
)
from backend.main import app


client = TestClient(app)


def test_goals_ui_markup_and_handlers():
    html = client.get("/").text
    assert 'id="goals"' in html
    assert 'id="goal-tree"' in html
    assert 'id="goal-editor"' in html
    assert 'id="task-list"' in html
    assert 'data-view="inbox"' in html
    assert 'data-view="today"' in html
    assert 'data-view="upcoming"' in html
    assert 'data-view="completed"' in html
    assert 'id="suggestion-panel"' in html
    assert 'id="suggestion-list"' in html

    js = client.get("/static/app.js").text
    assert "refreshGoalsUi" in js
    assert "refreshSuggestions" in js
    assert "sug-decide" in js
    assert 'data-decision="approved"' in js
    assert 'data-decision="rejected"' in js
    assert 'data-decision="deferred"' in js
    assert 'data-decision="edited"' in js
    assert "/api/goal-graph/suggestions/" in js
    assert "edited_payload" in js

    css = client.get("/static/styles.css").text
    assert ".goal-tree" in css
    assert ".suggestion-panel" in css
    assert ".task-views" in css


def test_task_views_and_editor_api(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from backend.config import get_settings
    import backend.main as main_mod

    get_settings.cache_clear()
    store = GoalGraphStore(tmp_path / "ui.sqlite3")
    main_mod._goal_graph = store

    parent = store.create_goal(GraphGoalCreate(title="Longevity base"))
    child = store.create_goal(
        GraphGoalCreate(
            title="Running conditioning",
            parent_goal_id=parent.id,
            metric="running_pace",
        )
    )
    store.create_task(
        GraphTaskCreate(title="Inbox item", goal_id=child.id, status=TaskStatus.INBOX)
    )
    store.create_task(
        GraphTaskCreate(
            title="Planned run",
            goal_id=child.id,
            status=TaskStatus.PLANNED,
            due_date="2099-01-01",
        )
    )
    store.create_task(
        GraphTaskCreate(
            title="Due today work",
            goal_id=child.id,
            status=TaskStatus.PLANNED,
            due_date="2020-01-01",
        )
    )
    done = store.create_task(
        GraphTaskCreate(title="Done thing", goal_id=child.id, status=TaskStatus.COMPLETED)
    )

    snap = client.get("/api/goal-graph")
    assert snap.status_code == 200
    tree = snap.json()["goal_tree"]
    assert tree[0]["goal"]["id"] == parent.id
    assert tree[0]["children"][0]["goal"]["id"] == child.id

    inbox = client.get("/api/goal-graph/tasks?view=inbox")
    assert inbox.status_code == 200
    assert any(t["title"] == "Inbox item" for t in inbox.json()["tasks"])

    today = client.get("/api/goal-graph/tasks?view=today")
    assert any(t["title"] == "Due today work" for t in today.json()["tasks"])

    upcoming = client.get("/api/goal-graph/tasks?view=upcoming")
    assert any(t["title"] == "Planned run" for t in upcoming.json()["tasks"])

    completed = client.get("/api/goal-graph/tasks?view=completed")
    assert any(t["id"] == done.id for t in completed.json()["tasks"])

    patched = client.patch(
        f"/api/goal-graph/goals/{child.id}",
        json={"description": "Pace + endurance", "success_criteria": "3 runs/week"},
    )
    assert patched.status_code == 200
    assert patched.json()["description"] == "Pace + endurance"

    created = client.post(
        "/api/goal-graph/tasks",
        json={"title": "UI-added task", "goal_id": child.id, "status": "inbox"},
    )
    assert created.status_code == 200


def test_suggestion_review_hitl_via_api(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from backend.config import get_settings
    import backend.main as main_mod

    get_settings.cache_clear()
    store = GoalGraphStore(tmp_path / "ui2.sqlite3")
    main_mod._goal_graph = store
    goal = store.create_goal(GraphGoalCreate(title="Nutrition"))
    sug = store.propose_suggestion(
        SuggestionCreate(
            kind=SuggestionKind.CREATE_TASK,
            title="Review weekly protein average",
            reason="meal logged",
            evidence=["beef", "rice"],
            assumptions=["draft"],
            confidence="medium",
            affected_goal_id=goal.id,
            payload={"title": "Review weekly protein average"},
        )
    )
    pending = client.get("/api/goal-graph/suggestions?pending_only=true")
    assert pending.status_code == 200
    assert any(s["id"] == sug.id for s in pending.json()["suggestions"])

    # Reject does not create tasks
    other = store.propose_suggestion(
        SuggestionCreate(
            kind=SuggestionKind.CREATE_TASK,
            title="Skip me",
            reason="x",
            affected_goal_id=goal.id,
            payload={"title": "Skip me"},
        )
    )
    rej = client.post(
        f"/api/goal-graph/suggestions/{other.id}/decide",
        json={"decision": "rejected"},
    )
    assert rej.status_code == 200
    assert store.list_tasks(goal_id=goal.id) == []

    approved = client.post(
        f"/api/goal-graph/suggestions/{sug.id}/decide",
        json={
            "decision": "approved",
            "edited_payload": {"title": "Log protein tonight", "description": "edited"},
        },
    )
    assert approved.status_code == 200
    assert approved.json()["decision"] == SuggestionDecision.EDITED.value
    tasks = store.list_tasks(goal_id=goal.id)
    assert any(t.title == "Log protein tonight" for t in tasks)
