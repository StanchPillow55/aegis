"""S5a / S5b — FITINDEX confirm UX + Google Takeout preview/provenance."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from backend.health.store import HealthMetricsStore
from backend.main import app

client = TestClient(app)


def _takeout_zip_bytes() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "Takeout/Fit/Daily activity metrics/Daily activity metrics.csv",
            "Date,Heart Rate (bpm),Step count,Calories (kcal)\n2026-09-07,60,9000,2200\n",
        )
    return buf.getvalue()


def test_s5a_fitindex_confirm_and_discard_ui_api(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from backend.config import get_settings
    import backend.main as main_mod

    get_settings.cache_clear()
    main_mod._metrics = HealthMetricsStore()

    html = client.get("/").text
    assert 'id="fitindex-draft"' in html
    assert 'id="fitindex-confirm-btn"' in html
    assert 'id="fitindex-discard-btn"' in html
    assert 'id="fitindex-manual-btn"' in html
    js = client.get("/static/app.js").text
    assert "showFitindexDraft" in js
    assert "/api/fitindex/confirm/" in js
    assert "/api/fitindex/discard/" in js

    draft = client.post(
        "/api/fitindex/csv",
        json={"csv": "weight_kg,body_fat_pct,day\n80.5,17.9,2026-09-07\n"},
    )
    assert draft.status_code == 200
    draft_id = draft.json()["draft_id"]
    assert draft.json()["confirmed"] is False

    # Discard path
    other = client.post(
        "/api/fitindex/manual",
        json={"weight_kg": 79.0, "body_fat_pct": 18.0, "notes": "temp"},
    )
    discard_id = other.json()["draft_id"]
    gone = client.post(f"/api/fitindex/discard/{discard_id}")
    assert gone.status_code == 200
    assert gone.json()["discarded"] is True
    assert client.post(f"/api/fitindex/discard/{discard_id}").status_code == 404

    # Confirm with edits
    confirm = client.post(
        f"/api/fitindex/confirm/{draft_id}",
        json={
            "confirmed": True,
            "weight_kg": 80.2,
            "body_fat_pct": 17.7,
            "day": "2026-09-07",
            "notes": "reviewed",
        },
    )
    assert confirm.status_code == 200
    assert main_mod._metrics.latest("weight_kg").value == 80.2
    assert main_mod._metrics.latest("body_fat_pct").value == 17.7


def test_s5b_takeout_preview_then_confirm(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from backend.config import get_settings
    import backend.main as main_mod
    from backend.sync import SourceRegistry

    get_settings.cache_clear()
    main_mod._metrics = HealthMetricsStore()
    main_mod._sync = SourceRegistry(tmp_path / "sync.sqlite3")

    html = client.get("/").text
    assert 'id="takeout-preview-btn"' in html
    assert 'id="takeout-summary"' in html
    assert "Primary metric import" in html
    js = client.get("/static/app.js").text
    assert "/api/takeout/preview" in js
    assert "showTakeoutSummary" in js
    assert "primary_metric_path" in js

    data = _takeout_zip_bytes()
    preview = client.post(
        "/api/takeout/preview",
        files={"file": ("takeout.zip", data, "application/zip")},
    )
    assert preview.status_code == 200
    body = preview.json()
    assert body["dry_run"] is True
    assert body["written"] == 0
    assert body["would_write"] >= 2
    assert "steps" in body["metrics"]
    assert body["provenance"]["primary_metric_path"] is True
    assert body["provenance"]["source"] == "takeout"
    # Preview must not persist
    assert main_mod._metrics.latest("steps") is None

    confirm = client.post(
        "/api/takeout/zip",
        files={"file": ("takeout.zip", data, "application/zip")},
    )
    assert confirm.status_code == 200
    written = confirm.json()
    assert written["written"] >= 2
    assert written["dry_run"] is False
    assert written["provenance"]["primary_metric_path"] is True
    assert main_mod._metrics.latest("steps").value == 9000
