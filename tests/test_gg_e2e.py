"""GG-E2E-01 — fixture path for Goal Graph completion bar (§12).

journal → evidence → contribution → suggestion → edit/approve →
dashboard/history → screen-aware chat
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.goals import GoalGraphStore, GraphGoalCreate
from backend.main import app


client = TestClient(app)

BEEF_RICE_RUN = "Ate beef and rice, run was good, averaged 10:30 for 3 miles."


def test_goal_graph_fixture_e2e_path(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from backend.config import get_settings
    import backend.main as main_mod
    from backend.chat import ChatService, ChatStore
    from backend.goals.tools import GoalGraphTools
    from backend.providers.memory import LocalMemoryProvider
    from backend.tools import HealthQueryTools

    get_settings.cache_clear()
    graph = GoalGraphStore(tmp_path / "e2e.sqlite3")
    memory = LocalMemoryProvider(db_path=tmp_path / "mem.sqlite3")
    chat_store = ChatStore(tmp_path / "chat.sqlite3")
    tools = HealthQueryTools(memory=memory, chat_store=chat_store)
    main_mod._goal_graph = graph
    main_mod._memory = memory
    main_mod._chat_store = chat_store
    main_mod._tools = tools
    main_mod._chat = ChatService(tools=tools, store=chat_store)
    main_mod._graph_tools = GoalGraphTools(
        graph=graph, memory=memory, chat_store=chat_store
    )

    # 1) Create goal from conversation (API stand-in for NL create)
    vision = client.post(
        "/api/goal-graph/goals",
        json={"title": "Functional longevity", "goal_type": "outcome"},
    )
    assert vision.status_code == 200
    conditioning = client.post(
        "/api/goal-graph/goals",
        json={
            "title": "Improve running conditioning",
            "metric": "running_pace",
            "parent_goal_id": vision.json()["id"],
            "description": "Track pace and endurance",
        },
    )
    assert conditioning.status_code == 200
    nutrition = client.post(
        "/api/goal-graph/goals",
        json={"title": "Nutrition consistency", "metric": "diet"},
    )
    assert nutrition.json()["metric"] == "diet"
    cond_id = conditioning.json()["id"]

    # 2–5) Submit journal → contributions + task suggestions (pending)
    directive = client.post("/api/directive", json={"text": BEEF_RICE_RUN, "speak": False})
    assert directive.status_code == 200
    dbody = directive.json()
    assert dbody["directive"]
    assert dbody.get("goal_analysis")
    ga = dbody["goal_analysis"]
    assert ga["human_in_the_loop"] is True
    assert ga["applied"] is False
    assert ga["goal_contributions"]
    assert ga["persisted"]["suggestion_ids"]

    # 3) Prior evidence retrievable via memory/search tool
    journal = client.post(
        "/api/goal-graph/tools/search_journal",
        json={"query": "beef rice run"},
    )
    assert journal.status_code == 200
    assert journal.json()["mode"] == "read"

    # Contributions pending for review
    contribs = client.get("/api/goal-graph/contributions?pending_only=true")
    assert contribs.status_code == 200
    assert contribs.json()["contributions"]

    # 6) Edit + approve a pace suggestion
    pending = client.get("/api/goal-graph/suggestions?pending_only=true")
    suggestions = pending.json()["suggestions"]
    assert suggestions
    pace = next(s for s in suggestions if "pace" in s["title"].lower())
    decided = client.post(
        f"/api/goal-graph/suggestions/{pace['id']}/decide",
        json={
            "decision": "approved",
            "edited_payload": {
                "title": "Log Sunday long run",
                "description": "Approved from journal E2E path",
            },
        },
    )
    assert decided.status_code == 200
    assert decided.json()["decision"] in {"approved", "edited"}

    # 7) Dashboard / goal history updated — task exists; snapshot shows tree
    tasks = client.get(f"/api/goal-graph/tasks?goal_id={cond_id}")
    assert tasks.status_code == 200
    assert any(t["title"] == "Log Sunday long run" for t in tasks.json()["tasks"])

    snap = client.get("/api/goal-graph")
    assert snap.status_code == 200
    assert snap.json()["goal_tree"]
    assert any(
        a["action"].startswith("decision:")
        for a in snap.json().get("audit") or []
    )

    # Progress dashboard for related metric still works
    prog = client.get("/api/progress/steps?horizon=week")
    assert prog.status_code == 200
    assert "chart" in prog.json()

    # 8) Screen-aware chat about updated dashboard
    chat = client.post(
        "/api/chat",
        json={
            "message": "What am I looking at on my goals dashboard?",
            "screen_context": {
                "panel": "goals",
                "route": "/#goals",
                "selected_goal_id": cond_id,
                "selected_chart_metric": "steps",
                "date_range": {"horizon": "week"},
                "pins": [{"id": "goals", "label": "Goals & tasks"}],
            },
        },
    )
    assert chat.status_code == 200
    reply = chat.json()["reply"].lower()
    assert "looking at" in reply or "goals" in reply or "context" in reply

    # History searchable after the turn
    search = client.get("/api/chat/search?q=goals")
    assert search.status_code == 200
    assert search.json()["count"] >= 1
