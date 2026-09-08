from fastapi.testclient import TestClient
from backend.main import app
from backend.environment.open_meteo import fetch_environment

client = TestClient(app)


def test_phc_geolocation_privacy():
    res = client.get("/api/geo/status")
    assert res.status_code == 200
    data = res.json()
    assert data["enabled"] is False
    assert data["cloud_llm"] is False


def test_phc_environment():
    res = client.get("/api/environment")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["mode"] in {"live", "offline", "disabled"}
    assert "weather" in data
    assert "aqi" in data
    # Must not claim live when using fixture
    if data["mode"] == "offline":
        assert data.get("source") == "fixture"
        assert "fixture" in (data.get("detail") or "").lower() or "offline" in (
            data.get("detail") or ""
        ).lower()


def test_phc_environment_force_offline():
    data = fetch_environment(force_offline=True)
    assert data["mode"] == "offline"
    assert data["source"] == "fixture"
    assert data["ok"] is True


def test_phc_connector_honesty():
    res = client.get("/api/sources")
    assert res.status_code == 200
    sources = res.json()["sources"]
    by_id = {s["source_id"]: s for s in sources}
    assert by_id["fitbit"]["live_oauth"] is False
    assert by_id["fitbit"]["integration_state"] in {
        "needs_credentials",
        "configured",
    }
    assert by_id["calendar"]["live_oauth"] is False


def test_phc_pwa():
    res = client.get("/manifest.webmanifest")
    assert res.status_code == 200
    assert "aegis" in res.text
    html = client.get("/").text
    assert "manifest.webmanifest" in html
    assert 'id="sync-panel"' in html or "Sync status" in html


def test_unified_composer_not_floating_dock():
    """Journal + ask share one expanding composer; no bottom-right chat dock."""
    html = client.get("/").text
    assert 'id="compose-form"' in html
    assert 'id="compose-text"' in html
    assert 'id="ask-btn"' in html
    assert 'id="directive-btn"' in html
    assert 'id="pin-mode-btn"' in html
    assert 'id="thread"' in html
    assert "chat-dock" not in html
    assert 'id="chat-input"' not in html
    # Attachable page regions for click-to-pin context
    assert 'data-pin-id="sync"' in html
    assert 'data-pin-id="overview"' in html
    js = client.get("/static/app.js").text
    assert "autosizeComposer" in js
    assert "pinnedContexts" in js
    assert "pin-picking" in js


def test_phc_tailscale_security():
    from pathlib import Path

    doc = (Path(__file__).resolve().parents[1] / "docs" / "TAILSCALE.md").read_text()
    assert "localhost only" in doc.lower() or "localhost" in doc.lower()
    assert "Funnel" in doc
    assert "SQLite" in doc
