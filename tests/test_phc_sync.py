"""PHC-SYNC-01 / PHC-STALE-01 / PHC-FALLBACK-01 — source registry tests."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app
from backend.sync import STALE_AFTER_SECONDS, SourceId, SourceRegistry, SyncConfig
from backend.sync.fixtures import load_fixture_bundle


client = TestClient(app)


def test_fixture_bundle_loads():
    bundle = load_fixture_bundle()
    assert bundle["record_count"] >= 1
    assert "resting_hr" in bundle["metrics"]


def test_registry_fixture_sync_and_history(tmp_path: Path):
    reg = SourceRegistry(tmp_path / "sync.sqlite3")
    assert any(s.source_id == SourceId.FIXTURE for s in reg.list_sources())

    result = reg.sync_one(SourceId.FIXTURE)
    assert result.success is True
    assert result.record_count >= 1
    status = reg._load(SourceId.FIXTURE.value)
    assert status.last_success_at is not None
    assert status.last_attempt_at is not None
    assert status.last_error is None
    assert status.stale is False
    hist = reg.history(source_id=SourceId.FIXTURE, limit=5)
    assert hist and hist[0].success is True


def test_disabled_source_skips_unless_forced(tmp_path: Path):
    reg = SourceRegistry(tmp_path / "sync2.sqlite3")
    reg.set_enabled(SourceId.FIXTURE, False)
    skipped = reg.sync_one(SourceId.FIXTURE)
    assert skipped.success is False
    assert skipped.error and skipped.error.code == "disabled"

    forced = reg.sync_one(SourceId.FIXTURE, force=True)
    assert forced.success is True


def test_external_unconfigured_fails_soft(tmp_path: Path):
    reg = SourceRegistry(tmp_path / "sync3.sqlite3")
    reg.set_enabled(SourceId.FITBIT, True)
    result = reg.sync_one(SourceId.FITBIT)
    assert result.success is False
    assert result.error and result.error.code == "not_configured"
    # App registry still lists other sources — local path intact
    assert any(s.source_id == SourceId.MANUAL for s in reg.list_sources())


def test_staleness_after_24h(tmp_path: Path):
    reg = SourceRegistry(tmp_path / "sync4.sqlite3")
    reg.sync_one(SourceId.FIXTURE)
    status = reg._load(SourceId.FIXTURE.value)
    status.last_success_at = time.time() - (STALE_AFTER_SECONDS + 10)
    reg._save(status)
    stale = reg.stale_sources()
    assert any(s.source_id == SourceId.FIXTURE for s in stale)


def test_sync_config_roundtrip(tmp_path: Path):
    reg = SourceRegistry(tmp_path / "sync5.sqlite3")
    cfg = SyncConfig(background_enabled=True, interval_seconds=1800, sources={"fixture": True})
    saved = reg.set_config(cfg)
    assert saved.background_enabled is True
    assert reg.get_config().interval_seconds == 1800


def test_api_sources_and_sync(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from backend.config import get_settings
    import backend.main as main_mod

    get_settings.cache_clear()
    main_mod._sync = SourceRegistry(tmp_path / "api_sync.sqlite3")

    listed = client.get("/api/sources")
    assert listed.status_code == 200
    payload = listed.json()
    assert "sources" in payload
    assert "config" in payload

    synced = client.post("/api/sync", json={"source_id": "fixture"})
    assert synced.status_code == 200
    body = synced.json()
    assert body["results"][0]["success"] is True

    hist = client.get("/api/sync/history?source_id=fixture")
    assert hist.status_code == 200
    assert hist.json()["history"]

    # Fitbit enabled but unconfigured — soft fail, app still healthy
    client.post("/api/sources/fitbit/enable", json={"enabled": True})
    soft = client.post("/api/sync", json={"source_id": "fitbit"})
    assert soft.status_code == 200
    assert soft.json()["results"][0]["success"] is False
    assert client.get("/health").json()["status"] == "ok"
