"""PHC-CHAT / CONTEXT / VISION — grounded chat + honest vision status."""

from fastapi.testclient import TestClient

from backend.chat import vision_status
from backend.main import app
from backend.tools import HealthQueryTools
from backend.tools.dates import parse_date_range

client = TestClient(app)


def test_phc_chat_search_proxy():
    tools = HealthQueryTools()
    out = tools.search_conversations("sleep")
    assert "hits" in out
    assert "limitation" in out


def test_phc_chat_api_grounded():
    res = client.post(
        "/api/chat",
        json={
            "message": "What is my steps and sync status?",
            "screen_context": {"panel": "overview"},
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["reply"]
    assert data["disclaimer"]
    assert "tool_results" in data
    assert any(t["tool"] == "source_freshness" for t in data["tool_results"])


def test_phc_chat_history():
    client.post("/api/chat", json={"message": "hello goals"})
    hist = client.get("/api/chat/history")
    assert hist.status_code == 200
    assert hist.json()["count"] >= 1


def test_phc_aicontext_placeholder():
    # Screen context provider feeds chat; geo/environment remain context APIs
    assert client.get("/api/environment").json()["ok"] is True
    ctx = client.get("/api/context/screen")
    assert ctx.status_code == 200
    assert "panel" in ctx.json() or "sources" in ctx.json()


def test_phc_vision_optional_status():
    status = vision_status()
    assert status["available"] in (True, False)
    assert status["mode"] in {"ollama_llava", "disabled"}
    api = client.get("/api/vision/status")
    assert api.status_code == 200
    assert "available" in api.json()


def test_date_parse_heuristic():
    out = parse_date_range("last 7 days")
    assert out["ok"] is True
    assert out["start"] <= out["end"]
