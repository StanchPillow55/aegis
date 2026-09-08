"""Ingestion + Fitbit/Calendar fixture + FITINDEX review tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.connectors import FITBIT_REQUIRED_METRICS, expand_fitbit_fixture_metrics
from backend.health.store import FitindexManualIn, HealthMetricsStore
from backend.main import app
from backend.sync import SourceId, SourceRegistry
from backend.sync.fixtures import load_fixture_bundle


client = TestClient(app)


def test_manual_and_fixture_ingest(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from backend.config import get_settings
    import backend.main as main_mod

    get_settings.cache_clear()
    store = HealthMetricsStore()  # uses DATA_DIR
    main_mod._metrics = store
    main_mod._sync = SourceRegistry(tmp_path / "sync.sqlite3")

    ingested = store.ingest_fixture()
    assert ingested["written"] >= 1
    assert "resting_hr" in store.list_metrics()
    latest = store.latest("resting_hr")
    assert latest is not None
    assert latest.provenance.source.value == "fixture"

    manual = client.post(
        "/api/metrics/manual",
        json={"metric": "resting_hr", "value": 55, "day": "2026-09-07", "notes": "spot check"},
    )
    assert manual.status_code == 200
    assert manual.json()["provenance"]["source"] == "manual_text"

    series = client.get("/api/metrics/resting_hr/series")
    assert series.status_code == 200
    assert len(series.json()["points"]) >= 1


def test_fitbit_fixture_covers_required_metrics(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from backend.config import get_settings
    import backend.main as main_mod

    get_settings.cache_clear()
    main_mod._metrics = HealthMetricsStore()
    main_mod._sync = SourceRegistry(tmp_path / "s.sqlite3")
    main_mod._sync.set_enabled(SourceId.FITBIT, True)

    expanded = expand_fitbit_fixture_metrics(load_fixture_bundle())
    for m in FITBIT_REQUIRED_METRICS:
        assert m in expanded

    res = client.post("/api/sync", json={"source_id": "fitbit", "force": True})
    assert res.status_code == 200
    assert res.json()["results"][0]["success"] is True
    metrics = set(main_mod._metrics.list_metrics())
    for m in FITBIT_REQUIRED_METRICS:
        assert m in metrics


def test_calendar_fixture_readonly(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from backend.config import get_settings
    import backend.main as main_mod

    get_settings.cache_clear()
    main_mod._metrics = HealthMetricsStore()
    main_mod._sync = SourceRegistry(tmp_path / "s2.sqlite3")
    main_mod._sync.set_enabled(SourceId.CALENDAR, True)
    res = client.post("/api/sync", json={"source_id": "calendar", "force": True})
    assert res.json()["results"][0]["success"] is True
    status = main_mod._sync._load("calendar")
    assert status.coverage.get("write_access") is False
    assert set(status.coverage.get("fields") or []) >= {
        "name",
        "location",
        "description",
        "start",
        "end",
    }


def test_fitindex_requires_confirm(tmp_path):
    store = HealthMetricsStore(tmp_path / "fi.sqlite3")
    draft = store.fitindex_propose(
        FitindexManualIn(weight_kg=82.0, body_fat_pct=18.5, day="2026-09-07")
    )
    try:
        store.fitindex_confirm(draft.draft_id, FitindexManualIn(confirmed=False))
        assert False, "expected ValueError"
    except ValueError:
        pass
    saved = store.fitindex_confirm(
        draft.draft_id,
        FitindexManualIn(weight_kg=81.8, body_fat_pct=18.4, day="2026-09-07", confirmed=True),
    )
    assert "weight_kg" in saved["written"]
    assert store.latest("weight_kg").value == 81.8


def test_fitindex_csv_api(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from backend.config import get_settings
    import backend.main as main_mod

    get_settings.cache_clear()
    main_mod._metrics = HealthMetricsStore()
    csv_text = "weight_kg,body_fat_pct,day\n80.5,17.9,2026-09-07\n"
    draft = client.post("/api/fitindex/csv", json={"csv": csv_text})
    assert draft.status_code == 200
    draft_id = draft.json()["draft_id"]
    confirm = client.post(
        f"/api/fitindex/confirm/{draft_id}",
        json={"confirmed": True, "weight_kg": 80.5, "body_fat_pct": 17.9, "day": "2026-09-07"},
    )
    assert confirm.status_code == 200
    assert main_mod._metrics.latest("body_fat_pct").value == 17.9
