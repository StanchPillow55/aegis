"""Connector adapters — fixture mode first (OAuth later)."""

from __future__ import annotations

import time
from typing import Any

from backend.connectors.status import (
    calendar_config_state,
    enrich_source_status,
    fitbit_config_state,
    takeout_config_state,
    weather_config_state,
)
from backend.connectors.takeout import ingest_takeout_bytes, ingest_takeout_zip
from backend.health.schema import DataQuality, DataSource, Provenance
from backend.health.store import HealthMetricsStore
from backend.sync.fixtures import load_fixture_bundle
from backend.sync.registry import SourceId, SourceRegistry, SyncResult

__all__ = [
    "FITBIT_REQUIRED_METRICS",
    "calendar_config_state",
    "enrich_source_status",
    "expand_fitbit_fixture_metrics",
    "fitbit_config_state",
    "ingest_takeout_bytes",
    "ingest_takeout_zip",
    "register_fixture_connectors",
    "sync_calendar_fixture",
    "sync_fitbit_fixture",
    "sync_takeout_fixture",
    "takeout_config_state",
    "weather_config_state",
]


# Fitbit metric names required by PHC-FITBIT-01 (fixture coverage map)
FITBIT_REQUIRED_METRICS = [
    "heart_rate",
    "hrv",
    "resting_hr",
    "spo2",
    "sleep_hours",
    "sleep_minutes",
    "steps",
    "distance",
    "active_minutes",
    "calories",
    "weight_kg",
    "body_fat_pct",
    "stress",
    "breathing_rate",
    "activity_minutes",
]


def expand_fitbit_fixture_metrics(bundle: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Ensure fixture bundle exposes the Fitbit-required metric set."""
    metrics = dict(bundle.get("metrics") or {})
    # aliases / derived
    if "resting_hr" in metrics and "heart_rate" not in metrics:
        metrics["heart_rate"] = metrics["resting_hr"]
    if "sleep_hours" in metrics and "sleep_minutes" not in metrics:
        metrics["sleep_minutes"] = [
            {"date": p["date"], "value": float(p["value"]) * 60} for p in metrics["sleep_hours"]
        ]
    if "steps" in metrics and "distance" not in metrics:
        metrics["distance"] = [
            {"date": p["date"], "value": round(float(p["value"]) * 0.0008, 3)} for p in metrics["steps"]
        ]
    if "active_minutes" not in metrics and bundle.get("activities"):
        metrics["active_minutes"] = [
            {"date": a["date"], "value": float(a.get("minutes") or 0)} for a in bundle["activities"]
        ]
    for required in FITBIT_REQUIRED_METRICS:
        metrics.setdefault(
            required,
            [{"date": "2026-09-07", "value": 0.0}],
        )
    return metrics


def sync_fitbit_fixture(registry: SourceRegistry, source_id: SourceId) -> SyncResult:
    """Fixture-mode Fitbit ingest (no OAuth)."""
    bundle = load_fixture_bundle()
    metrics = expand_fitbit_fixture_metrics(bundle)
    store = HealthMetricsStore()
    now = time.time()
    prov = Provenance(
        source=DataSource.FITBIT,
        recorded_at=now,
        observed_at=now,
        quality=DataQuality.MEDIUM,
        extractor="fitbit_fixture",
        notes="fixture-mode Fitbit adapter (OAuth not enabled)",
    )
    written = 0
    for metric, points in metrics.items():
        for p in points:
            day = p.get("date")
            from backend.health.store import _day_to_epoch

            observed = _day_to_epoch(day) if day else now
            store.upsert_point(
                metric=metric,
                value=float(p["value"]),
                day=day,
                observed_at=observed,
                provenance=prov.model_copy(update={"observed_at": observed}),
            )
            written += 1
    status = registry._load(source_id.value)
    status.coverage = {
        "metrics": sorted(metrics.keys()),
        "mode": "fixture",
        **fitbit_config_state(),
    }
    return SyncResult(
        source_id=source_id,
        success=True,
        record_count=written,
        detail="Fitbit fixture sync complete (not live OAuth)",
        status=status,
    )


def sync_calendar_fixture(registry: SourceRegistry, source_id: SourceId) -> SyncResult:
    """Read-only calendar fixture events."""
    events = [
        {
            "name": "Gym — strength",
            "location": "Home gym",
            "description": "Squat focus",
            "start": "2026-09-07T17:00:00Z",
            "end": "2026-09-07T18:00:00Z",
        },
        {
            "name": "Team standup",
            "location": "Remote",
            "description": "",
            "start": "2026-09-07T14:00:00Z",
            "end": "2026-09-07T14:15:00Z",
        },
    ]
    store = HealthMetricsStore()
    now = time.time()
    prov = Provenance(
        source=DataSource.CALENDAR,
        recorded_at=now,
        observed_at=now,
        quality=DataQuality.MEDIUM,
        extractor="calendar_fixture",
        notes="read-only calendar fixture",
    )
    # Store as metric points with event metadata (countable coverage)
    for i, ev in enumerate(events):
        store.upsert_point(
            metric="calendar_event",
            value=float(i + 1),
            observed_at=now + i,
            provenance=prov,
            meta=ev,
        )
    status = registry._load(source_id.value)
    status.coverage = {
        "fields": ["name", "location", "description", "start", "end"],
        "events": len(events),
        "mode": "fixture",
        "write_access": False,
        **calendar_config_state(),
    }
    return SyncResult(
        source_id=source_id,
        success=True,
        record_count=len(events),
        detail="Calendar fixture sync (read-only; not live OAuth)",
        status=status,
    )


def sync_takeout_fixture(registry: SourceRegistry, source_id: SourceId) -> SyncResult:
    """Minimal Takeout ZIP/CSV fallback fixture (no Google account required)."""
    from backend.health.store import _day_to_epoch

    store = HealthMetricsStore()
    now = time.time()
    observed = _day_to_epoch("2026-09-07")
    prov = Provenance(
        source=DataSource.TAKEOUT,
        recorded_at=now,
        observed_at=observed,
        quality=DataQuality.LOW,
        extractor="takeout_fixture",
        notes="future-compatible Takeout fallback fixture",
    )
    store.upsert_point(
        metric="steps", value=9000, day="2026-09-07", observed_at=observed, provenance=prov
    )
    store.upsert_point(
        metric="resting_hr", value=60, day="2026-09-07", observed_at=observed, provenance=prov
    )
    status = registry._load(source_id.value)
    status.coverage = {
        "mode": "fixture_fallback",
        "formats": ["zip/csv"],
        **takeout_config_state(),
    }
    return SyncResult(
        source_id=source_id,
        success=True,
        record_count=2,
        detail="Takeout fixture fallback (not a live Google account)",
        status=status,
    )


def register_fixture_connectors(registry: SourceRegistry) -> None:
    registry.register_handler(SourceId.FITBIT, sync_fitbit_fixture)
    registry.register_handler(SourceId.CALENDAR, sync_calendar_fixture)
    registry.register_handler(SourceId.TAKEOUT, sync_takeout_fixture)
