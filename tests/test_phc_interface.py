from fastapi.testclient import TestClient
from backend.main import app

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
    assert res.json()["ok"] is True


def test_phc_pwa():
    res = client.get("/manifest.webmanifest")
    assert res.status_code == 200
    assert "aegis" in res.text
    html = client.get("/").text
    assert "manifest.webmanifest" in html


def test_phc_tailscale_security():
    from pathlib import Path
    doc = (Path(__file__).resolve().parents[1] / "docs" / "TAILSCALE.md").read_text()
    assert "localhost only" in doc.lower() or "localhost" in doc.lower()
    assert "Funnel" in doc
    assert "SQLite" in doc
