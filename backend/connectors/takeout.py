"""Google Takeout ZIP → health metrics (future-compatible fallback).

Parses Daily activity metrics CSVs inside a Takeout archive. Does not require
a live Google account. Fixture sync remains available separately for demos.
"""

from __future__ import annotations

import csv
import io
import time
import zipfile
from pathlib import Path
from typing import BinaryIO

from backend.health.schema import DataQuality, DataSource, Provenance
from backend.health.store import HealthMetricsStore, _day_to_epoch

# Common Takeout column → canonical metric
_COLUMN_MAP = {
    "heart rate (bpm)": "resting_hr",
    "heart rate": "resting_hr",
    "resting heart rate": "resting_hr",
    "step count": "steps",
    "steps": "steps",
    "distance (m)": "distance",
    "distance": "distance",
    "calories (kcal)": "calories",
    "calories": "calories",
    "active minutes": "active_minutes",
    "move minutes": "active_minutes",
}


def ingest_takeout_zip(
    store: HealthMetricsStore,
    zip_path: Path | str | BinaryIO,
    *,
    notes: str = "Takeout ZIP fallback import",
) -> dict:
    """Ingest CSV rows from a Takeout ZIP into the metrics store.

    Returns counts and list of metrics written. Empty/unknown CSVs are skipped
    without raising (partial success).
    """
    written = 0
    metrics_seen: set[str] = set()
    files_parsed = 0
    now = time.time()
    prov = Provenance(
        source=DataSource.TAKEOUT,
        recorded_at=now,
        observed_at=now,
        quality=DataQuality.LOW,
        extractor="takeout_zip",
        notes=notes,
    )

    def _open_zip():
        if hasattr(zip_path, "read"):
            return zipfile.ZipFile(zip_path)
        return zipfile.ZipFile(Path(zip_path))

    with _open_zip() as zf:
        for name in zf.namelist():
            if name.endswith("/") or not name.lower().endswith(".csv"):
                continue
            text = zf.read(name).decode("utf-8", errors="replace")
            if not text.strip():
                continue
            reader = csv.DictReader(io.StringIO(text))
            if not reader.fieldnames:
                continue
            files_parsed += 1
            for row in reader:
                day = row.get("Date") or row.get("date") or row.get("Start date")
                observed = _day_to_epoch(day) if day else now
                row_prov = prov.model_copy(update={"observed_at": observed})
                for col, raw in row.items():
                    if col is None or raw is None or str(raw).strip() == "":
                        continue
                    key = col.strip().lower()
                    metric = _COLUMN_MAP.get(key)
                    if metric is None:
                        continue
                    try:
                        value = float(str(raw).replace(",", ""))
                    except ValueError:
                        continue
                    store.upsert_point(
                        metric=metric,
                        value=value,
                        day=day,
                        observed_at=observed,
                        provenance=row_prov,
                        meta={"takeout_file": name, "column": col},
                    )
                    written += 1
                    metrics_seen.add(metric)

    return {
        "written": written,
        "metrics": sorted(metrics_seen),
        "files_parsed": files_parsed,
        "mode": "takeout_zip",
        "quality": DataQuality.LOW.value,
    }


def ingest_takeout_bytes(store: HealthMetricsStore, data: bytes) -> dict:
    return ingest_takeout_zip(store, io.BytesIO(data))
