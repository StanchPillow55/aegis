from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["mode"] == "open-source-foundation"
    assert "voice" in payload
    assert "schema_version" in payload


def test_frontend_index() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert b"aegis" in response.content


def test_directive_roundtrip(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MEMORY_DB_PATH", str(tmp_path / "t.sqlite3"))
    from backend.config import get_settings
    import backend.main as main_mod
    from backend.providers.memory import LocalMemoryProvider

    get_settings.cache_clear()
    main_mod._memory = LocalMemoryProvider(tmp_path / "t.sqlite3")

    response = client.post(
        "/api/directive",
        json={
            "text": "Slept 7 hours well, shoulders sore 2/5, yogurt, press day, feeling ready.",
            "speak": False,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["directive"]
    assert data["log_id"]
    assert data["disclaimer"]
    assert "front_rack" in data["scores"]
    assert "overall" in data["scores"]
    assert data["wod_decision"]["status"]
    assert data["evidence"]["today"]["authoritative"] is True
    assert isinstance(data["evidence"]["history"], list)
    assert data["extractor"] in {"heuristic", "ollama"}
