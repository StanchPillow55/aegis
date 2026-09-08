"""Google Takeout ZIP → health metrics (future-compatible fallback).

Supports:
- Daily activity metrics CSV (Google Takeout Fit export)
- Google Fit JSON "Data Points" files (legacy prototype format)

Does not require a live Google account. Fixture sync remains available separately.
"""

from __future__ import annotations

import csv
import io
import json
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO

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

_JSON_NAME_MAP = {
    "heart_rate_variability": ("hrv", "ms"),
    "hrv": ("hrv", "ms"),
    "heart_rate": ("heart_rate", "bpm"),
    "step_count": ("steps", "steps"),
    "calories": ("calories", "kcal"),
    "sleep_segment": ("sleep_minutes", "minutes"),
}


def _json_metric_for_name(filename: str) -> tuple[str, str] | None:
    name_lower = filename.lower()
    for key, mapped in _JSON_NAME_MAP.items():
        if key in name_lower:
            return mapped
    return None


def _ingest_json_member(
    store: HealthMetricsStore,
    *,
    name: str,
    raw: bytes,
    prov: Provenance,
) -> tuple[int, set[str]]:
    written = 0
    metrics_seen: set[str] = set()
    mapped = _json_metric_for_name(name)
    if mapped is None:
        return 0, metrics_seen
    metric, unit = mapped
    try:
        data = json.loads(raw.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return 0, metrics_seen
    points = data.get("Data Points") or data.get("dataPoints") or []
    if not isinstance(points, list):
        return 0, metrics_seen
    for pt in points:
        try:
            start_n = int(pt["startTimeNanos"])
            observed = start_n / 1e9
            day = datetime.fromtimestamp(observed, tz=timezone.utc).date().isoformat()
            if metric == "sleep_minutes":
                end_n = int(pt["endTimeNanos"])
                value = (end_n - start_n) / 1e9 / 60.0
            else:
                value = float(pt["fitValue"][0]["value"]["fpVal"])
            store.upsert_point(
                metric=metric,
                value=value,
                day=day,
                observed_at=observed,
                provenance=prov.model_copy(update={"observed_at": observed, "extractor": "takeout_json"}),
                meta={"takeout_file": name, "unit": unit},
            )
            written += 1
            metrics_seen.add(metric)
            if metric == "sleep_minutes":
                store.upsert_point(
                    metric="sleep_hours",
                    value=round(value / 60.0, 2),
                    day=day,
                    observed_at=observed,
                    provenance=prov.model_copy(
                        update={"observed_at": observed, "extractor": "takeout_json"}
                    ),
                    meta={"takeout_file": name, "derived_from": "sleep_minutes"},
                )
                written += 1
                metrics_seen.add("sleep_hours")
        except (KeyError, TypeError, ValueError, IndexError):
            continue
    return written, metrics_seen


def ingest_takeout_zip(
    store: HealthMetricsStore,
    zip_path: Path | str | BinaryIO,
    *,
    notes: str = "Google Health / Takeout primary import",
    dry_run: bool = False,
) -> dict:
    """Ingest CSV + Google Fit JSON from a Takeout ZIP into the metrics store.

    When ``dry_run=True``, parse and summarize without writing points (preview/confirm UX).
    """
    written = 0
    would_write = 0
    metrics_seen: set[str] = set()
    sample_rows: list[dict[str, Any]] = []
    files_parsed = 0
    json_files = 0
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
            if name.endswith("/"):
                continue
            lower = name.lower()
            if lower.endswith(".json"):
                raw = zf.read(name)
                if dry_run:
                    mapped = _json_metric_for_name(name)
                    if mapped is None:
                        continue
                    metric, _unit = mapped
                    try:
                        data = json.loads(raw.decode("utf-8", errors="replace"))
                    except json.JSONDecodeError:
                        continue
                    points = data.get("Data Points") or data.get("dataPoints") or []
                    if not isinstance(points, list) or not points:
                        continue
                    json_files += 1
                    files_parsed += 1
                    metrics_seen.add(metric)
                    n = len(points)
                    would_write += n
                    if len(sample_rows) < 5:
                        sample_rows.append(
                            {"file": name, "metric": metric, "points": n, "mode": "json"}
                        )
                    continue
                w, ms = _ingest_json_member(store, name=name, raw=raw, prov=prov)
                if w:
                    json_files += 1
                    files_parsed += 1
                    written += w
                    metrics_seen |= ms
                continue
            if not lower.endswith(".csv"):
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
                for col, raw_val in row.items():
                    if col is None or raw_val is None or str(raw_val).strip() == "":
                        continue
                    key = col.strip().lower()
                    metric = _COLUMN_MAP.get(key)
                    if metric is None:
                        continue
                    try:
                        value = float(str(raw_val).replace(",", ""))
                    except ValueError:
                        continue
                    would_write += 1
                    metrics_seen.add(metric)
                    if dry_run:
                        if len(sample_rows) < 8:
                            sample_rows.append(
                                {
                                    "file": name,
                                    "metric": metric,
                                    "value": value,
                                    "day": day,
                                    "mode": "csv",
                                }
                            )
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

    return {
        "written": written,
        "would_write": would_write if dry_run else written,
        "metrics": sorted(metrics_seen),
        "files_parsed": files_parsed,
        "json_files": json_files,
        "mode": "takeout_zip_preview" if dry_run else "takeout_zip",
        "dry_run": dry_run,
        "quality": DataQuality.LOW.value,
        "provenance": {
            "source": DataSource.TAKEOUT.value,
            "extractor": "takeout_zip",
            "primary_metric_path": True,
            "quality": DataQuality.LOW.value,
            "notes": notes,
        },
        "sample": sample_rows if dry_run else [],
    }


def ingest_takeout_bytes(
    store: HealthMetricsStore, data: bytes, *, dry_run: bool = False
) -> dict:
    return ingest_takeout_zip(store, io.BytesIO(data), dry_run=dry_run)
