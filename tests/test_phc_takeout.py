"""PHC-TAKEOUT-01 — Takeout ZIP production parser + API."""

import io
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from backend.connectors.takeout import ingest_takeout_zip
from backend.health.store import HealthMetricsStore
from backend.main import app

client = TestClient(app)


def _build_takeout_zip(path: Path) -> Path:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "Takeout/Fit/Daily activity metrics/Daily activity metrics.csv",
            "Date,Heart Rate (bpm),Step count,Calories (kcal)\n2026-09-07,60,9000,2200\n",
        )
    path.write_bytes(buf.getvalue())
    return path


def test_takeout_zip_fixture(tmp_path: Path):
    zpath = _build_takeout_zip(tmp_path / "takeout.zip")
    store = HealthMetricsStore(tmp_path / "t.sqlite3")
    result = ingest_takeout_zip(store, zpath)
    assert result["written"] >= 2
    assert "steps" in result["metrics"]
    assert store.latest("steps").value == 9000
    assert store.latest("resting_hr").value == 60


def test_takeout_zip_api(tmp_path: Path):
    zpath = _build_takeout_zip(tmp_path / "takeout.zip")
    data = zpath.read_bytes()
    res = client.post(
        "/api/takeout/zip",
        files={"file": ("takeout.zip", data, "application/zip")},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["written"] >= 2
    assert body["mode"] == "takeout_zip"
