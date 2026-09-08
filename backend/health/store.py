"""Durable health metrics store with provenance (manual + fixture ingestion)."""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from backend.health.schema import (
    SCHEMA_VERSION,
    DataQuality,
    DataSource,
    Provenance,
)
from backend.sync.fixtures import load_fixture_bundle


class MetricPoint(BaseModel):
    point_id: str
    metric: str
    value: float
    unit: str | None = None
    observed_at: float
    recorded_at: float
    day: str | None = None
    provenance: Provenance
    meta: dict[str, Any] = Field(default_factory=dict)


class ManualMetricIn(BaseModel):
    metric: str
    value: float
    unit: str | None = None
    day: str | None = None
    observed_at: float | None = None
    notes: str | None = None


class FitindexManualIn(BaseModel):
    weight_kg: float | None = None
    body_fat_pct: float | None = None
    day: str | None = None
    notes: str | None = None
    # review gate: client must set confirmed=true after user edits
    confirmed: bool = False


class FitindexReview(BaseModel):
    draft_id: str
    proposed: dict[str, Any]
    confirmed: bool = False


class HealthMetricsStore:
    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is None:
            from backend.config import get_settings

            db_path = Path(get_settings().data_dir) / "aegis_health.sqlite3"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS metric_points (
                    point_id TEXT PRIMARY KEY,
                    metric TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT,
                    observed_at REAL NOT NULL,
                    recorded_at REAL NOT NULL,
                    day TEXT,
                    provenance_json TEXT NOT NULL,
                    meta_json TEXT NOT NULL,
                    schema_version INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_metric_day ON metric_points(metric, day)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS fitindex_drafts (
                    draft_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )
            conn.commit()

    def upsert_point(
        self,
        *,
        metric: str,
        value: float,
        provenance: Provenance,
        unit: str | None = None,
        observed_at: float | None = None,
        day: str | None = None,
        meta: dict[str, Any] | None = None,
        point_id: str | None = None,
    ) -> MetricPoint:
        now = time.time()
        observed = observed_at if observed_at is not None else now
        pid = point_id or uuid.uuid4().hex[:16]
        point = MetricPoint(
            point_id=pid,
            metric=metric,
            value=float(value),
            unit=unit,
            observed_at=observed,
            recorded_at=now,
            day=day,
            provenance=provenance,
            meta=meta or {},
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO metric_points(
                    point_id, metric, value, unit, observed_at, recorded_at, day,
                    provenance_json, meta_json, schema_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    point.point_id,
                    point.metric,
                    point.value,
                    point.unit,
                    point.observed_at,
                    point.recorded_at,
                    point.day,
                    point.provenance.model_dump_json(),
                    json.dumps(point.meta),
                    SCHEMA_VERSION,
                ),
            )
            conn.commit()
        return point

    def list_metrics(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT metric FROM metric_points ORDER BY metric"
            ).fetchall()
        return [r["metric"] for r in rows]

    def latest(self, metric: str) -> MetricPoint | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM metric_points WHERE metric = ?
                ORDER BY observed_at DESC LIMIT 1
                """,
                (metric,),
            ).fetchone()
        return self._row(row) if row else None

    def series(
        self,
        metric: str,
        *,
        start: float | None = None,
        end: float | None = None,
        limit: int = 500,
    ) -> list[MetricPoint]:
        limit = max(1, min(limit, 5000))
        clauses = ["metric = ?"]
        params: list[Any] = [metric]
        if start is not None:
            clauses.append("observed_at >= ?")
            params.append(start)
        if end is not None:
            clauses.append("observed_at <= ?")
            params.append(end)
        params.append(limit)
        sql = (
            "SELECT * FROM metric_points WHERE "
            + " AND ".join(clauses)
            + " ORDER BY observed_at ASC LIMIT ?"
        )
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row(r) for r in rows]

    def count(self) -> int:
        with self._connect() as conn:
            return int(conn.execute("SELECT COUNT(*) AS n FROM metric_points").fetchone()["n"])

    def _row(self, row: sqlite3.Row) -> MetricPoint:
        return MetricPoint(
            point_id=row["point_id"],
            metric=row["metric"],
            value=float(row["value"]),
            unit=row["unit"],
            observed_at=float(row["observed_at"]),
            recorded_at=float(row["recorded_at"]),
            day=row["day"],
            provenance=Provenance.model_validate_json(row["provenance_json"]),
            meta=json.loads(row["meta_json"] or "{}"),
        )

    def ingest_fixture(self, path: Path | None = None) -> dict[str, Any]:
        bundle = load_fixture_bundle(path)
        prov = Provenance(
            source=DataSource.FIXTURE,
            recorded_at=time.time(),
            observed_at=time.time(),
            quality=DataQuality.MEDIUM,
            extractor="fixture",
            notes="fixture bundle ingest",
        )
        written = 0
        for metric, points in (bundle.get("metrics") or {}).items():
            for p in points:
                day = p.get("date")
                # noon UTC-ish epoch from YYYY-MM-DD for ordering
                observed = _day_to_epoch(day) if day else time.time()
                self.upsert_point(
                    metric=metric,
                    value=float(p["value"]),
                    unit=p.get("unit"),
                    day=day,
                    observed_at=observed,
                    provenance=prov.model_copy(update={"observed_at": observed}),
                    meta={"activity": False},
                )
                written += 1
        for act in bundle.get("activities") or []:
            day = act.get("date")
            observed = _day_to_epoch(day) if day else time.time()
            self.upsert_point(
                metric="activity_minutes",
                value=float(act.get("minutes") or 0),
                day=day,
                observed_at=observed,
                provenance=prov.model_copy(update={"observed_at": observed}),
                meta={"name": act.get("name"), "activity": True},
            )
            written += 1
        return {"written": written, "metrics": self.list_metrics(), "total": self.count()}

    def add_manual(self, body: ManualMetricIn) -> MetricPoint:
        now = time.time()
        observed = body.observed_at if body.observed_at is not None else now
        prov = Provenance(
            source=DataSource.MANUAL_TEXT,
            recorded_at=now,
            observed_at=observed,
            quality=DataQuality.HIGH,
            extractor="manual",
            notes=body.notes,
        )
        return self.upsert_point(
            metric=body.metric,
            value=body.value,
            unit=body.unit,
            day=body.day,
            observed_at=observed,
            provenance=prov,
        )

    # --- FITINDEX review workflow ---
    def fitindex_propose(self, body: FitindexManualIn) -> FitindexReview:
        draft_id = uuid.uuid4().hex[:12]
        proposed = body.model_dump()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO fitindex_drafts(draft_id, payload_json, created_at) VALUES (?, ?, ?)",
                (draft_id, json.dumps(proposed), time.time()),
            )
            conn.commit()
        return FitindexReview(draft_id=draft_id, proposed=proposed, confirmed=False)

    def fitindex_discard(self, draft_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM fitindex_drafts WHERE draft_id = ?", (draft_id,)
            )
            conn.commit()
            if cur.rowcount < 1:
                raise KeyError(draft_id)
        return {"draft_id": draft_id, "discarded": True}

    def fitindex_confirm(self, draft_id: str, edits: FitindexManualIn | None = None) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM fitindex_drafts WHERE draft_id = ?", (draft_id,)
            ).fetchone()
        if row is None:
            raise KeyError(draft_id)
        data = json.loads(row["payload_json"])
        if edits is not None:
            data.update({k: v for k, v in edits.model_dump().items() if v is not None or k == "confirmed"})
        if not data.get("confirmed") and not (edits and edits.confirmed):
            raise ValueError("User must confirm FITINDEX draft before save (confirmed=true)")
        written: list[str] = []
        day = data.get("day")
        observed = _day_to_epoch(day) if day else time.time()
        prov = Provenance(
            source=DataSource.FITINDEX,
            recorded_at=time.time(),
            observed_at=observed,
            quality=DataQuality.HIGH,
            extractor="manual_review",
            notes=data.get("notes"),
        )
        if data.get("weight_kg") is not None:
            self.upsert_point(
                metric="weight_kg",
                value=float(data["weight_kg"]),
                day=day,
                observed_at=observed,
                provenance=prov,
            )
            written.append("weight_kg")
        if data.get("body_fat_pct") is not None:
            self.upsert_point(
                metric="body_fat_pct",
                value=float(data["body_fat_pct"]),
                day=day,
                observed_at=observed,
                provenance=prov,
            )
            written.append("body_fat_pct")
        with self._connect() as conn:
            conn.execute("DELETE FROM fitindex_drafts WHERE draft_id = ?", (draft_id,))
            conn.commit()
        return {"draft_id": draft_id, "written": written}

    def ingest_fitindex_csv(self, text: str) -> FitindexReview:
        """Parse simple CSV (header weight_kg,body_fat_pct,day) into a review draft."""
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if not lines:
            raise ValueError("Empty CSV")
        header = [h.strip().lower() for h in lines[0].split(",")]
        row = [c.strip() for c in lines[1].split(",")]
        mapping = dict(zip(header, row))
        body = FitindexManualIn(
            weight_kg=float(mapping["weight_kg"]) if mapping.get("weight_kg") else None,
            body_fat_pct=float(mapping["body_fat_pct"]) if mapping.get("body_fat_pct") else None,
            day=mapping.get("day") or None,
            notes="csv_upload",
            confirmed=False,
        )
        return self.fitindex_propose(body)


def _day_to_epoch(day: str) -> float:
    # YYYY-MM-DD → approximate noon UTC
    try:
        y, m, d = [int(x) for x in day.split("-")]
        import datetime as dt

        return dt.datetime(y, m, d, 12, 0, tzinfo=dt.timezone.utc).timestamp()
    except Exception:
        return time.time()
