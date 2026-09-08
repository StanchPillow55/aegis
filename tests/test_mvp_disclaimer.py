"""MVP-DISCLAIMER-01: safety disclaimer in API + HTML."""

from fastapi.testclient import TestClient

from backend.health.schema import SAFETY_DISCLAIMER
from backend.main import app


client = TestClient(app)


def test_directive_includes_disclaimer(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMORY_DB_PATH", str(tmp_path / "d.sqlite3"))
    from backend.config import get_settings
    import backend.main as main_mod
    from backend.providers.memory import LocalMemoryProvider

    get_settings.cache_clear()
    main_mod._memory = LocalMemoryProvider(tmp_path / "d.sqlite3")

    res = client.post(
        "/api/directive",
        json={"text": "Slept 8 hours well, feeling ready, chicken for lunch.", "speak": False},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["disclaimer"]
    assert "does not diagnose" in data["disclaimer"].lower()
    assert data["disclaimer"] == SAFETY_DISCLAIMER
    assert data["tts"] is not None
    assert data["tts"]["ok"] is False
    assert "today" in data["evidence"]
    assert "history" in data["evidence"]
    assert "conflicts" in data["evidence"]
    assert data["extractor"] in {"heuristic", "ollama"}


def test_frontend_contains_disclaimer_hook():
    res = client.get("/")
    assert res.status_code == 200
    html = res.text
    assert "disclaimer-text" in html
    assert "Today" in html
    assert "History" in html
    assert "Conflicts" in html
