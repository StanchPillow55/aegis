"""Remaining unblocked polish: dual safety modes, geo consent, PWA shell, S8 browser."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_dual_safety_output_modes():
    d = client.post(
        "/api/directive",
        json={"text": "Slept 7 hours, ready for training.", "speak": False},
    )
    assert d.status_code == 200
    assert d.json()["output_mode"] == "training_planning"
    assert "training planning" in d.json()["output_mode_label"].lower()

    c = client.post("/api/chat", json={"message": "What is my sync status?"})
    assert c.status_code == 200
    assert c.json()["output_mode"] == "health_analysis"
    assert "health analysis" in c.json()["output_mode_label"].lower()

    html = client.get("/").text
    assert 'id="directive-mode"' in html
    js = client.get("/static/app.js").text
    assert "output_mode_label" in js
    assert "output-mode-tag" in js


def test_geo_consent_opt_in_and_revoke(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from backend.config import get_settings
    import backend.main as main_mod
    from backend.geo import GeoConsentStore

    get_settings.cache_clear()
    main_mod._geo_consent = GeoConsentStore(tmp_path / "geo.json")

    st = client.get("/api/geo/status")
    assert st.status_code == 200
    assert st.json()["enabled"] is False
    assert st.json()["default"] == "off"
    assert st.json()["cloud_llm"] is False
    assert st.json()["coords_stored"] is False

    on = client.put("/api/geo/consent", json={"enabled": True})
    assert on.status_code == 200
    assert on.json()["enabled"] is True
    # Preference file must not contain lat/lon keys
    raw = (tmp_path / "geo.json").read_text()
    assert "lat" not in raw.lower()
    assert "lon" not in raw.lower()

    off = client.put("/api/geo/consent", json={"enabled": False})
    assert off.json()["enabled"] is False

    html = client.get("/").text
    assert 'id="geo-consent-toggle"' in html
    assert 'id="geo-revoke-btn"' in html


def test_pwa_service_worker_and_icon():
    man = client.get("/manifest.webmanifest")
    assert man.status_code == 200
    assert "icons" in man.json()
    assert man.json()["icons"][0]["src"].endswith("icon.svg")
    sw = client.get("/sw.js")
    assert sw.status_code == 200
    assert "aegis-shell" in sw.text
    assert "/api/" in sw.text  # network-only API note
    icon = client.get("/static/icons/icon.svg")
    assert icon.status_code == 200
    html = client.get("/").text
    assert "serviceWorker" in html


@pytest.mark.skipif(
    os.environ.get("AEGIS_PLAYWRIGHT") != "1",
    reason="Set AEGIS_PLAYWRIGHT=1 after `pip install playwright && playwright install chromium`",
)
def test_s8_playwright_goal_graph_smoke():
    """Optional browser smoke for Goal Graph path (S8)."""
    playwright = pytest.importorskip("playwright.sync_api")
    from playwright.sync_api import sync_playwright

    # Use TestClient ASGI via uvicorn in-thread is heavy; hit live if available,
    # else skip. Prefer in-process via base_url from env.
    base = os.environ.get("AEGIS_BASE_URL", "http://127.0.0.1:8000")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(base + "/", wait_until="networkidle")
        page.click('a[href="#goals"]')
        page.wait_for_selector("#goals")
        assert page.locator("#goal-tree").count() == 1
        assert page.locator("#suggestion-panel").count() == 1
        page.fill("#goal-new-title", "Playwright conditioning")
        page.fill("#goal-new-metric", "running_pace")
        page.click("#goal-create-form button[type=submit]")
        page.wait_for_timeout(500)
        page.click('a[href="#composer"]')
        page.fill("#compose-text", "Ate beef and rice, run was good, averaged 10:30 for 3 miles.")
        page.click("#directive-btn")
        page.wait_for_selector("#result:not([hidden])", timeout=15000)
        assert "training planning" in page.locator("#directive-mode").inner_text().lower()
        page.click('a[href="#goals"]')
        page.click("#suggestion-refresh-btn")
        page.wait_for_timeout(400)
        browser.close()
