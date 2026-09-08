"""GG-CONTEXT-01 — typed screen context + read vs mutate-preview tools (GL5)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.context.screen import ScreenContext, parse_screen_context
from backend.goals import GoalGraphStore, GraphGoalCreate
from backend.goals.tools import MUTATE_PREVIEW_TOOLS, READ_TOOLS, GoalGraphTools
from backend.main import app


client = TestClient(app)


def test_screen_context_rejects_html():
    with pytest.raises((ValidationError, ValueError)):
        parse_screen_context({"panel": "overview", "html": "<b>x</b>"})
    with pytest.raises((ValidationError, ValueError)):
        parse_screen_context({"script": "alert(1)"})
    ctx = parse_screen_context(
        {
            "panel": "<b>goals</b>",
            "pins": [{"id": "chart", "label": "<em>Chart</em>", "snippet": "ok"}],
            "selected_goal_id": "abc",
            "date_range": {"horizon": "week"},
        }
    )
    assert "<" not in ctx.panel
    assert ctx.panel == "goals"
    assert "<" not in ctx.pins[0].label
    assert ctx.selected_goal_id == "abc"


def test_read_vs_mutate_tool_sets(tmp_path: Path):
    graph = GoalGraphStore(tmp_path / "t.sqlite3")
    tools = GoalGraphTools(graph=graph)
    listed = tools.list_tools()
    assert set(listed["read"]) == READ_TOOLS
    assert set(listed["mutate_preview"]) == MUTATE_PREVIEW_TOOLS
    assert tools.classify("list_goal_tree") == "read"
    assert tools.classify("propose_create_task") == "mutate_preview"

    goal = graph.create_goal(GraphGoalCreate(title="Sleep", metric="sleep_hours"))
    preview = tools.dispatch(
        "propose_create_task", title="Log bedtime", goal_id=goal.id
    )
    assert preview["mode"] == "mutate_preview"
    assert preview["applied"] is False
    assert graph.list_tasks(goal_id=goal.id) == []

    # confirm without user_confirmed does not apply
    sid = preview["suggestion"]["id"]
    blocked = tools.dispatch(
        "confirm_suggestion", suggestion_id=sid, decision="approved", user_confirmed=False
    )
    assert blocked["applied"] is False
    assert graph.list_tasks(goal_id=goal.id) == []

    applied = tools.dispatch(
        "confirm_suggestion", suggestion_id=sid, decision="approved", user_confirmed=True
    )
    assert applied["applied"] is True
    assert graph.list_tasks(goal_id=goal.id)


def test_api_context_and_tools(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from backend.config import get_settings
    import backend.main as main_mod
    from backend.goals.tools import GoalGraphTools

    get_settings.cache_clear()
    graph = GoalGraphStore(tmp_path / "api.sqlite3")
    goal = graph.create_goal(GraphGoalCreate(title="Run", metric="running_pace"))
    main_mod._goal_graph = graph
    main_mod._graph_tools = GoalGraphTools(graph=graph)

    ctx = client.get(
        f"/api/context/screen?panel=goals&goal_id={goal.id}&chart_metric=steps&horizon=week"
    )
    assert ctx.status_code == 200
    body = ctx.json()
    assert "typed" in body
    assert body["typed"]["selected_goal_id"] == goal.id
    assert body["typed"]["selected_chart_metric"] == "steps"
    assert "html" not in body["typed"]
    assert "typed_summary" in body

    tools = client.get("/api/goal-graph/tools")
    assert tools.status_code == 200
    assert "list_goal_tree" in tools.json()["read"]
    assert "propose_create_task" in tools.json()["mutate_preview"]

    tree = client.post("/api/goal-graph/tools/list_goal_tree", json={})
    assert tree.status_code == 200
    assert tree.json()["mode"] == "read"

    mut = client.post(
        "/api/goal-graph/tools/propose_create_task",
        json={"title": "Easy run", "goal_id": goal.id},
    )
    assert mut.status_code == 200
    assert mut.json()["applied"] is False

    chat = client.post(
        "/api/chat",
        json={
            "message": "What am I looking at?",
            "screen_context": {
                "panel": "goals",
                "route": "/#goals",
                "selected_goal_id": goal.id,
                "pins": [{"id": "goals", "label": "Goals"}],
            },
        },
    )
    assert chat.status_code == 200
    assert "looking at" in chat.json()["reply"].lower()


def test_frontend_builds_typed_context():
    js = client.get("/static/app.js").text
    assert "selected_goal_id" in js
    assert "selected_chart_metric" in js
    assert "date_range" in js
    assert "delete screen.html" in js
