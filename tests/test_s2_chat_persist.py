"""S2 / PHC-CHAT-02 — SQLite chat persist + searchable history."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.chat import ChatService, ChatStore, ChatTurnRequest
from backend.main import app
from backend.tools import HealthQueryTools


client = TestClient(app)


def test_chat_store_persists_across_instances(tmp_path: Path):
    db = tmp_path / "chat.sqlite3"
    store = ChatStore(db)
    svc = ChatService(tools=HealthQueryTools(), store=store)
    res = svc.turn(ChatTurnRequest(message="What is my sleep status?"))
    sid = res.session_id
    assert sid
    assert len(store.history(session_id=sid)) == 2

    # New service instance, same DB — history survives
    store2 = ChatStore(db)
    svc2 = ChatService(tools=HealthQueryTools(), store=store2)
    hist = svc2.history(session_id=sid)
    assert len(hist) == 2
    assert hist[0].role == "user"
    assert "sleep" in hist[0].content.lower()
    sessions = svc2.list_sessions()
    assert any(s["session_id"] == sid for s in sessions)


def test_chat_search_finds_message(tmp_path: Path):
    db = tmp_path / "chat2.sqlite3"
    store = ChatStore(db)
    sid = store.ensure_session()
    store.append_message(
        session_id=sid, role="user", content="Ate beef and rice after my tempo run"
    )
    store.append_message(
        session_id=sid, role="assistant", content="Noted nutrition and conditioning."
    )
    hits = store.search("beef")
    assert hits
    assert any("beef" in h["content"].lower() for h in hits)
    assert store.search("zzzz-no-hit") == []


def test_api_chat_persist_and_search(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from backend.config import get_settings
    import backend.main as main_mod

    get_settings.cache_clear()
    store = ChatStore(tmp_path / "api_chat.sqlite3")
    tools = HealthQueryTools(chat_store=store)
    main_mod._chat_store = store
    main_mod._tools = tools
    main_mod._chat = ChatService(tools=tools, store=store)

    res = client.post("/api/chat", json={"message": "Tell me about my goals and sync"})
    assert res.status_code == 200
    sid = res.json()["session_id"]

    hist = client.get(f"/api/chat/history?session_id={sid}")
    assert hist.status_code == 200
    assert hist.json()["count"] >= 2

    sessions = client.get("/api/chat/sessions")
    assert sessions.status_code == 200
    assert any(s["session_id"] == sid for s in sessions.json()["sessions"])

    search = client.get("/api/chat/search?q=goals")
    assert search.status_code == 200
    assert search.json()["source"] == "chat_store"
    assert search.json()["count"] >= 1

    # Tool search uses chat store
    out = tools.search_conversations("goals")
    assert out["source"] == "chat_store"
    assert out["limitation"] is None


def test_ui_has_chat_search():
    html = client.get("/").text
    assert 'id="chat-search-form"' in html
    assert 'id="chat-search-q"' in html
    js = client.get("/static/app.js").text
    assert "aegis_chat_session_id" in js
    assert "/api/chat/search" in js
    assert "restoreChatSession" in js
