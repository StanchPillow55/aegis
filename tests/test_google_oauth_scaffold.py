"""Scaffolding up to secrets — Google Calendar + Health OAuth (no fake auth)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.connectors import google_oauth, token_store
from backend.main import app
from backend.sync import SourceId, SourceRegistry

client = TestClient(app)


def test_google_status_needs_credentials_without_secrets(monkeypatch, tmp_path):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("AEGIS_GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("AEGIS_GOOGLE_CLIENT_SECRET", raising=False)
    from backend.config import get_settings

    get_settings.cache_clear()

    for path in ("/api/google/calendar/status", "/api/google/health/status"):
        res = client.get(path)
        assert res.status_code == 200
        body = res.json()
        assert body["authenticated"] is False
        assert body["integration_state"] == "needs_credentials"
        assert body["live_oauth"] is False
        assert body["auth_url"] is None

    pull = client.post("/api/google/health/pull")
    assert pull.status_code == 200
    assert pull.json()["mode"] == "needs_credentials"
    assert pull.json()["fallback"] == "use_takeout_zip"

    events = client.get("/api/google/calendar/events")
    assert events.status_code == 200
    assert events.json()["mode"] == "needs_token"
    assert events.json()["events"] == []


def test_google_auth_url_when_credentials_present(monkeypatch, tmp_path):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")
    from backend.config import get_settings

    get_settings.cache_clear()

    cal = client.get("/api/google/calendar/auth")
    assert cal.status_code == 200
    body = cal.json()
    assert body["integration_state"] == "configured"
    assert body["authenticated"] is False
    assert body["live_oauth"] is True
    assert "accounts.google.com" in (body.get("auth_url") or "")
    assert "calendar.readonly" in (body.get("auth_url") or "")

    health = client.get("/api/google/health/auth")
    assert health.status_code == 200
    h = health.json()
    assert h["integration_state"] == "configured"
    assert "fitness.activity.read" in (h.get("auth_url") or "")
    assert h["primary_metric_path"] is True


def test_token_store_roundtrip_and_no_fake_connected(monkeypatch, tmp_path):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("AEGIS_TOKEN_KEY", "unit-test-token-key-for-fernet-seed")
    from backend.config import get_settings

    get_settings.cache_clear()

    stored = token_store.store_token(
        google_oauth.SOURCE_CALENDAR,
        "access-xyz",
        "refresh-xyz",
        3600,
        scopes=google_oauth.CALENDAR_SCOPES,
    )
    assert stored.get("stored") is True, stored
    tok = token_store.get_token(google_oauth.SOURCE_CALENDAR)
    assert tok is not None
    assert tok["access_token"] == "access-xyz"
    assert tok["expired"] is False

    st = google_oauth.status(google_oauth.SOURCE_CALENDAR)
    # Still needs GOOGLE_CLIENT_* for live_oauth path labeling when checking auth_url
    # Without client id, status is needs_credentials even with orphan token
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")
    st = google_oauth.status(google_oauth.SOURCE_CALENDAR)
    assert st["authenticated"] is True
    assert st["integration_state"] == "connected"

    google_oauth.revoke(google_oauth.SOURCE_CALENDAR)
    assert token_store.get_token(google_oauth.SOURCE_CALENDAR) is None


def test_google_health_source_registered(tmp_path):
    reg = SourceRegistry(tmp_path / "sync.sqlite3")
    ids = {s.source_id.value for s in reg.list_sources()}
    assert "google_health" in ids
    assert SourceId.GOOGLE_HEALTH.value == "google_health"


def test_frontend_exposes_google_scaffold_controls():
    html = client.get("/").text
    assert 'id="google-calendar-auth-btn"' in html
    assert 'id="google-health-auth-btn"' in html
    assert "/api/google/calendar/" in client.get("/static/app.js").text
    assert "CLIENT_SECRET" not in client.get("/static/app.js").text


def test_exchange_without_credentials_fails_closed(monkeypatch, tmp_path):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
    from backend.config import get_settings

    get_settings.cache_clear()
    res = client.get("/api/google/calendar/callback", params={"code": "fake"})
    assert res.status_code == 400
