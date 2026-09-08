"""S9 — computed signals (PDF gaps) + sync label honesty + backup."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from backend.backup import build_backup_zip, restore_backup_zip
from backend.health.store import HealthMetricsStore
from backend.intake.schema import IntakeResult, Meal, Sleep, WOD
from backend.main import app
from backend.signals.computed import score_recovery, score_running_pace
from backend.sync import SourceRegistry

client = TestClient(app)


def test_sync_labels_match_connector_policy(tmp_path):
    reg = SourceRegistry(tmp_path / "sync.sqlite3")
    statuses = {s.source_id.value: s for s in reg.list_sources()}
    assert "primary" in statuses["takeout"].label.lower()
    assert "legacy" in statuses["fitbit"].label.lower() or "not primary" in statuses["fitbit"].label.lower()
    assert "fallback" not in statuses["takeout"].label.lower()
    assert statuses["fitindex"].coverage.get("scale_oauth") is False

    # Existing DB gets label refresh
    stale = statuses["takeout"]
    stale.label = "Google Takeout ZIP (fallback)"
    reg._save(stale)  # noqa: SLF001 — intentional persistence probe
    reg2 = SourceRegistry(tmp_path / "sync.sqlite3")
    takeout = next(s for s in reg2.list_sources() if s.source_id.value == "takeout")
    assert "primary" in takeout.label.lower()


def test_computed_recovery_and_pace_scores():
    intake = IntakeResult(
        sleep=Sleep(quality="ok", hours=5.0),
        soreness=[],
        meals=[Meal(description="beef")],
        subjective_readiness="moderate",
        todays_wod=WOD(movements=["run"], raw="averaged 10:30 for 3 miles"),
    )
    rec = score_recovery(intake, recent_text="hoping to recover from my sleep debt")
    assert rec["score"] is not None
    assert rec["factors"]["sleep_debt_language"] is True
    pace = score_running_pace(intake, recent_text=intake.todays_wod.raw or "")
    assert pace["score"] is not None
    assert pace["factors"]["pace"] == "10:30"


def test_backup_export_restore_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from backend.config import get_settings
    import backend.main as main_mod

    get_settings.cache_clear()
    # Create a small sqlite so export has content
    store = HealthMetricsStore(tmp_path / "aegis_health.sqlite3")
    main_mod._metrics = store
    (tmp_path / "geo.json").write_text('{"enabled": false}')

    data, meta = build_backup_zip(tmp_path)
    assert meta["count"] >= 1
    assert zipfile.is_zipfile(io.BytesIO(data))

    export = client.get("/api/backup/export")
    assert export.status_code == 200
    assert export.headers["content-type"].startswith("application/zip")

    other = tmp_path / "restore-target"
    other.mkdir()
    result = restore_backup_zip(other, export.content)
    assert result["count"] >= 1
    assert any(p.name.endswith(".sqlite3") for p in other.iterdir())

    html = client.get("/").text
    assert 'id="backup-restore-btn"' in html
    assert "/api/backup/export" in html
