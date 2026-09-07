"""PHC-TAKEOUT-01 — Takeout ZIP fallback stub with fixture."""

import io
import zipfile
from pathlib import Path

from backend.health.schema import DataQuality, DataSource, Provenance
from backend.health.store import HealthMetricsStore


def _build_takeout_zip(path: Path) -> Path:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "Takeout/Fit/Daily activity metrics/Daily activity metrics.csv",
            "Date,Heart Rate (bpm),Step count\n2026-09-07,60,9000\n",
        )
    path.write_bytes(buf.getvalue())
    return path


def ingest_takeout_zip(store: HealthMetricsStore, zip_path: Path) -> dict:
    import csv
    import zipfile
    import time
    from backend.health.store import _day_to_epoch

    written = 0
    prov = Provenance(
        source=DataSource.TAKEOUT,
        recorded_at=time.time(),
        observed_at=time.time(),
        quality=DataQuality.LOW,
        extractor="takeout_zip",
        notes="future-compatible fallback",
    )
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if not name.lower().endswith(".csv"):
                continue
            text = zf.read(name).decode("utf-8", errors="replace")
            reader = csv.DictReader(io.StringIO(text))
            for row in reader:
                day = row.get("Date") or row.get("date")
                observed = _day_to_epoch(day) if day else time.time()
                if row.get("Heart Rate (bpm)"):
                    store.upsert_point(
                        metric="resting_hr",
                        value=float(row["Heart Rate (bpm)"]),
                        day=day,
                        observed_at=observed,
                        provenance=prov,
                    )
                    written += 1
                if row.get("Step count"):
                    store.upsert_point(
                        metric="steps",
                        value=float(row["Step count"]),
                        day=day,
                        observed_at=observed,
                        provenance=prov,
                    )
                    written += 1
    return {"written": written}


def test_takeout_zip_fixture(tmp_path: Path):
    zpath = _build_takeout_zip(tmp_path / "takeout.zip")
    store = HealthMetricsStore(tmp_path / "t.sqlite3")
    result = ingest_takeout_zip(store, zpath)
    assert result["written"] >= 2
    assert store.latest("steps").value == 9000
