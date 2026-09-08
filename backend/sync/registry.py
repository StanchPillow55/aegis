"""Source registry + sync status (Slice 1).

Fixture/manual sources are fully runnable. External connectors (Fitbit,
Calendar, weather) are registered as disabled stubs that fail soft until
OAuth/adapters land.
"""

from __future__ import annotations

import json
import sqlite3
import time
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, Field

from backend.health.schema import SCHEMA_VERSION

STALE_AFTER_SECONDS = 24 * 3600


class SourceId(str, Enum):
    MANUAL = "manual"
    FIXTURE = "fixture"
    FITBIT = "fitbit"
    CALENDAR = "calendar"
    FITINDEX = "fitindex"
    TAKEOUT = "takeout"
    GOOGLE_HEALTH = "google_health"
    WEATHER = "weather"


class SyncError(BaseModel):
    code: str
    message: str
    at: float


class SourceStatus(BaseModel):
    source_id: SourceId
    label: str
    enabled: bool = True
    supports_background: bool = False
    last_success_at: float | None = None
    last_attempt_at: float | None = None
    last_error: SyncError | None = None
    record_count: int = 0
    coverage: dict[str, Any] = Field(default_factory=dict)
    stale: bool = False
    stale_after_seconds: int = STALE_AFTER_SECONDS
    kind: str = "local"  # local | external


class SyncHistoryEntry(BaseModel):
    source_id: SourceId
    attempted_at: float
    success: bool
    record_count: int = 0
    error: SyncError | None = None
    detail: str | None = None


class SyncConfig(BaseModel):
    background_enabled: bool = False
    interval_seconds: int = 3600
    sources: dict[str, bool] = Field(default_factory=dict)
    max_retries: int = 3
    retry_backoff_seconds: float = 2.0


class SyncResult(BaseModel):
    source_id: SourceId
    success: bool
    record_count: int = 0
    detail: str = ""
    error: SyncError | None = None
    status: SourceStatus | None = None


def _default_sources() -> dict[str, SourceStatus]:
    return {
        SourceId.MANUAL.value: SourceStatus(
            source_id=SourceId.MANUAL,
            label="Manual text entry",
            enabled=True,
            supports_background=False,
            kind="local",
            coverage={"modes": ["text"]},
        ),
        SourceId.FIXTURE.value: SourceStatus(
            source_id=SourceId.FIXTURE,
            label="Local fixtures",
            enabled=True,
            supports_background=True,
            kind="local",
            coverage={"modes": ["json_fixture"]},
        ),
        SourceId.FITBIT.value: SourceStatus(
            source_id=SourceId.FITBIT,
            label="Fitbit (legacy fixture — not primary)",
            enabled=False,
            supports_background=True,
            kind="external",
            coverage={"metrics": [], "primary": False, "legacy_fixture": True},
        ),
        SourceId.CALENDAR.value: SourceStatus(
            source_id=SourceId.CALENDAR,
            label="Google Calendar (read-only OAuth)",
            enabled=False,
            supports_background=True,
            kind="external",
            coverage={"fields": ["name", "location", "description", "start", "end"]},
        ),
        SourceId.FITINDEX.value: SourceStatus(
            source_id=SourceId.FITINDEX,
            label="FITINDEX (CSV + OCR + manual — no scale OAuth)",
            enabled=True,
            supports_background=False,
            kind="local",
            coverage={"modes": ["csv", "ocr", "manual"], "scale_oauth": False},
        ),
        SourceId.TAKEOUT.value: SourceStatus(
            source_id=SourceId.TAKEOUT,
            label="Google Health / Takeout (primary metrics)",
            enabled=False,
            supports_background=False,
            kind="external",
            coverage={"primary_metric_path": True, "modes": ["zip_preview", "zip_confirm"]},
        ),
        SourceId.GOOGLE_HEALTH.value: SourceStatus(
            source_id=SourceId.GOOGLE_HEALTH,
            label="Google Health API (live OAuth scaffold)",
            enabled=False,
            supports_background=True,
            kind="external",
            coverage={
                "primary_metric_path": True,
                "oauth": True,
                "scopes": ["fitness.activity", "fitness.heart_rate", "fitness.sleep", "fitness.body"],
            },
        ),
        SourceId.WEATHER.value: SourceStatus(
            source_id=SourceId.WEATHER,
            label="Open-Meteo weather/AQI",
            enabled=False,
            supports_background=True,
            kind="external",
        ),
    }


SyncHandler = Callable[["SourceRegistry", SourceId], SyncResult]


class SourceRegistry:
    """Persistent per-source sync registry backed by SQLite."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is None:
            from backend.config import get_settings

            settings = get_settings()
            db_path = Path(settings.data_dir) / "aegis_sync.sqlite3"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._handlers: dict[str, SyncHandler] = {}
        self._init_db()
        self._ensure_defaults()
        self.register_handler(SourceId.FIXTURE, _sync_fixture)
        self.register_handler(SourceId.MANUAL, _sync_manual_noop)
        # Fixture-mode connectors (OAuth later)
        try:
            from backend.connectors import register_fixture_connectors

            register_fixture_connectors(self)
        except Exception:
            pass

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sync_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sources (
                    source_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sync_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL,
                    attempted_at REAL NOT NULL,
                    success INTEGER NOT NULL,
                    record_count INTEGER NOT NULL DEFAULT 0,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "INSERT OR REPLACE INTO sync_meta(key, value) VALUES ('schema_version', ?)",
                (str(SCHEMA_VERSION),),
            )
            # default config
            row = conn.execute(
                "SELECT value FROM sync_meta WHERE key = 'config'"
            ).fetchone()
            if not row:
                cfg = SyncConfig()
                conn.execute(
                    "INSERT INTO sync_meta(key, value) VALUES ('config', ?)",
                    (cfg.model_dump_json(),),
                )
            conn.commit()

    def _ensure_defaults(self) -> None:
        defaults = _default_sources()
        with self._connect() as conn:
            for sid, status in defaults.items():
                existing = conn.execute(
                    "SELECT payload_json FROM sources WHERE source_id = ?", (sid,)
                ).fetchone()
                if existing is None:
                    conn.execute(
                        "INSERT INTO sources(source_id, payload_json) VALUES (?, ?)",
                        (sid, status.model_dump_json()),
                    )
                else:
                    # Refresh policy labels/coverage without wiping sync timestamps.
                    cur = SourceStatus.model_validate_json(existing["payload_json"])
                    changed = False
                    if cur.label != status.label:
                        cur.label = status.label
                        changed = True
                    for key, val in (status.coverage or {}).items():
                        if cur.coverage.get(key) != val:
                            cur.coverage[key] = val
                            changed = True
                    if changed:
                        conn.execute(
                            "UPDATE sources SET payload_json = ? WHERE source_id = ?",
                            (cur.model_dump_json(), sid),
                        )
            conn.commit()

    def register_handler(self, source_id: SourceId | str, handler: SyncHandler) -> None:
        key = source_id.value if isinstance(source_id, SourceId) else source_id
        self._handlers[key] = handler

    def get_config(self) -> SyncConfig:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM sync_meta WHERE key = 'config'"
            ).fetchone()
        return SyncConfig.model_validate_json(row["value"])

    def set_config(self, config: SyncConfig) -> SyncConfig:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO sync_meta(key, value) VALUES ('config', ?)",
                (config.model_dump_json(),),
            )
            conn.commit()
        return config

    def _load(self, source_id: str) -> SourceStatus:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM sources WHERE source_id = ?", (source_id,)
            ).fetchone()
        if row is None:
            raise KeyError(source_id)
        status = SourceStatus.model_validate_json(row["payload_json"])
        return self._apply_staleness(status)

    def _save(self, status: SourceStatus) -> SourceStatus:
        status = self._apply_staleness(status)
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO sources(source_id, payload_json) VALUES (?, ?)",
                (status.source_id.value, status.model_dump_json()),
            )
            conn.commit()
        return status

    def _apply_staleness(self, status: SourceStatus) -> SourceStatus:
        if status.last_success_at is None:
            # Never synced: stale only if enabled external/background source
            status.stale = bool(status.enabled and status.supports_background)
            return status
        age = time.time() - status.last_success_at
        status.stale = age > status.stale_after_seconds
        return status

    def list_sources(self) -> list[SourceStatus]:
        with self._connect() as conn:
            rows = conn.execute("SELECT source_id FROM sources ORDER BY source_id").fetchall()
        return [self._load(r["source_id"]) for r in rows]

    def set_enabled(self, source_id: SourceId | str, enabled: bool) -> SourceStatus:
        key = source_id.value if isinstance(source_id, SourceId) else source_id
        status = self._load(key)
        status.enabled = enabled
        return self._save(status)

    def history(self, *, source_id: SourceId | str | None = None, limit: int = 50) -> list[SyncHistoryEntry]:
        limit = max(1, min(limit, 200))
        with self._connect() as conn:
            if source_id is None:
                rows = conn.execute(
                    "SELECT payload_json FROM sync_history ORDER BY attempted_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            else:
                key = source_id.value if isinstance(source_id, SourceId) else source_id
                rows = conn.execute(
                    """
                    SELECT payload_json FROM sync_history
                    WHERE source_id = ? ORDER BY attempted_at DESC LIMIT ?
                    """,
                    (key, limit),
                ).fetchall()
        return [SyncHistoryEntry.model_validate_json(r["payload_json"]) for r in rows]

    def _append_history(self, entry: SyncHistoryEntry) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sync_history(source_id, attempted_at, success, record_count, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    entry.source_id.value,
                    entry.attempted_at,
                    1 if entry.success else 0,
                    entry.record_count,
                    entry.model_dump_json(),
                ),
            )
            conn.commit()

    def sync_one(self, source_id: SourceId | str, *, force: bool = False) -> SyncResult:
        key = source_id.value if isinstance(source_id, SourceId) else source_id
        sid = SourceId(key)
        status = self._load(key)
        now = time.time()
        status.last_attempt_at = now

        if not status.enabled and not force:
            err = SyncError(code="disabled", message=f"{key} is disabled", at=now)
            status.last_error = err
            self._save(status)
            entry = SyncHistoryEntry(
                source_id=sid,
                attempted_at=now,
                success=False,
                error=err,
                detail="skipped: disabled",
            )
            self._append_history(entry)
            return SyncResult(source_id=sid, success=False, error=err, detail="disabled", status=status)

        handler = self._handlers.get(key)
        if handler is None:
            err = SyncError(
                code="not_configured",
                message=f"No sync handler for {key} (fixture/manual only in Slice 1)",
                at=now,
            )
            status.last_error = err
            self._save(status)
            entry = SyncHistoryEntry(
                source_id=sid, attempted_at=now, success=False, error=err, detail=err.message
            )
            self._append_history(entry)
            return SyncResult(source_id=sid, success=False, error=err, detail=err.message, status=status)

        try:
            result = handler(self, sid)
        except Exception as exc:  # fail soft
            err = SyncError(code="sync_failed", message=str(exc), at=now)
            status.last_error = err
            self._save(status)
            entry = SyncHistoryEntry(
                source_id=sid, attempted_at=now, success=False, error=err, detail=str(exc)
            )
            self._append_history(entry)
            return SyncResult(source_id=sid, success=False, error=err, detail=str(exc), status=status)

        status = self._load(key)
        status.last_attempt_at = now
        if result.success:
            status.last_success_at = now
            status.last_error = None
            status.record_count = max(status.record_count, result.record_count)
            if result.status and result.status.coverage:
                status.coverage = result.status.coverage
        else:
            status.last_error = result.error or SyncError(
                code="sync_failed", message=result.detail or "failed", at=now
            )
        status = self._save(status)
        entry = SyncHistoryEntry(
            source_id=sid,
            attempted_at=now,
            success=result.success,
            record_count=result.record_count,
            error=result.error,
            detail=result.detail,
        )
        self._append_history(entry)
        result.status = status
        return result

    def sync_one_with_retries(
        self,
        source_id: SourceId | str,
        *,
        force: bool = False,
        max_retries: int | None = None,
        backoff_seconds: float | None = None,
        sleep_fn: Callable[[float], None] | None = None,
    ) -> SyncResult:
        """Sync one source with exponential backoff on soft failure.

        Disabled sources are not retried. ``not_configured`` failures are not
        retried (configuration will not change mid-loop). Transient
        ``sync_failed`` errors retry up to ``max_retries`` times.
        """
        cfg = self.get_config()
        attempts = max(1, int(max_retries if max_retries is not None else cfg.max_retries))
        base = float(
            backoff_seconds
            if backoff_seconds is not None
            else cfg.retry_backoff_seconds
        )
        sleeper = sleep_fn or time.sleep
        last: SyncResult | None = None
        for attempt in range(1, attempts + 1):
            last = self.sync_one(source_id, force=force)
            if last.success:
                last.detail = (last.detail or "") + (
                    f" (attempt {attempt}/{attempts})" if attempt > 1 else ""
                )
                return last
            code = last.error.code if last.error else ""
            if code in {"disabled", "not_configured"}:
                return last
            if attempt >= attempts:
                break
            sleeper(base * (2 ** (attempt - 1)))
        assert last is not None
        last.detail = (last.detail or "failed") + f" (exhausted {attempts} attempts)"
        return last

    def sync_all(self, *, only_enabled: bool = True) -> list[SyncResult]:
        results: list[SyncResult] = []
        for status in self.list_sources():
            if only_enabled and not status.enabled:
                continue
            # Skip pure manual no-op unless explicitly called
            if status.source_id == SourceId.MANUAL:
                continue
            results.append(self.sync_one(status.source_id))
        return results

    def stale_sources(self) -> list[SourceStatus]:
        return [s for s in self.list_sources() if s.enabled and s.stale]

    def snapshot(self) -> dict[str, Any]:
        return {
            "config": self.get_config().model_dump(),
            "sources": [s.model_dump() for s in self.list_sources()],
            "stale": [s.source_id.value for s in self.stale_sources()],
            "history": [h.model_dump() for h in self.history(limit=20)],
        }


def _sync_fixture(registry: SourceRegistry, source_id: SourceId) -> SyncResult:
    """Load bundled fixture metrics into the health metrics store."""
    from backend.health.store import HealthMetricsStore
    from backend.sync.fixtures import load_fixture_bundle

    bundle = load_fixture_bundle()
    store = HealthMetricsStore()
    ingested = store.ingest_fixture()
    status = registry._load(source_id.value)
    status.coverage = {
        "modes": ["json_fixture"],
        "metrics": sorted(bundle.get("metrics", {}).keys()),
        "sample_days": bundle.get("sample_days", 0),
        "stored_metrics": ingested.get("metrics", []),
    }
    count = int(ingested.get("written") or bundle.get("record_count", 0))
    return SyncResult(
        source_id=source_id,
        success=True,
        record_count=count,
        detail=f"Ingested fixture bundle ({count} points)",
        status=status,
    )


def _sync_manual_noop(registry: SourceRegistry, source_id: SourceId) -> SyncResult:
    return SyncResult(
        source_id=source_id,
        success=True,
        record_count=0,
        detail="Manual source has no batch sync; use /api/intake or /api/directive",
    )
