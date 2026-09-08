"""MVP-VOICE-01 — explicit tts status when speak requested/not requested."""

from fastapi.testclient import TestClient
from backend.main import app
from backend.providers.memory import LocalMemoryProvider

client = TestClient(app)


def test_mvp_voice_tts_status(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMORY_DB_PATH", str(tmp_path / "v.sqlite3"))
    from backend.config import get_settings
    import backend.main as main_mod

    get_settings.cache_clear()
    main_mod._memory = LocalMemoryProvider(tmp_path / "v.sqlite3")
    res = client.post("/api/directive", json={"text": "Slept 8 hours, feeling ready.", "speak": False})
    assert res.status_code == 200
    tts = res.json()["tts"]
    assert tts is not None
    assert "ok" in tts and "detail" in tts
