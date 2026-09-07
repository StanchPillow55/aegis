"""PHC-FALLBACK-01 — local usable when external sync fails."""

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app
from backend.providers.memory import LocalMemoryProvider
from backend.sync import SourceId, SourceRegistry


client = TestClient(app)


def test_local_fallback_when_externals_fail(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("MEMORY_DB_PATH", str(tmp_path / "mem.sqlite3"))
    from backend.config import get_settings
    import backend.main as main_mod

    get_settings.cache_clear()
    main_mod._sync = SourceRegistry(tmp_path / "fb_sync.sqlite3")
    main_mod._memory = LocalMemoryProvider(tmp_path / "mem.sqlite3")

    main_mod._sync.set_enabled(SourceId.FITBIT, True)
    main_mod._sync.set_enabled(SourceId.CALENDAR, True)
    main_mod._sync.set_enabled(SourceId.WEATHER, True)
    for sid in ("fitbit", "calendar", "weather"):
        res = client.post("/api/sync", json={"source_id": sid})
        assert res.status_code == 200
        assert res.json()["results"][0]["success"] is False

    # Fixture + manual directive still work
    assert client.post("/api/sync", json={"source_id": "fixture"}).json()["results"][0]["success"]
    directive = client.post(
        "/api/directive",
        json={"text": "Slept 8 hours, feeling ready, eggs and rice, squats today.", "speak": False},
    )
    assert directive.status_code == 200
    assert directive.json()["directive"]
    assert client.get("/health").json()["status"] == "ok"
