"""Alert engine with default thresholds, overrides, and history."""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from backend.health.store import HealthMetricsStore


DEFAULT_THRESHOLDS = {
    "heart_rate_high": {"metric": "heart_rate", "op": ">", "value": 200, "severity": "critical"},
    "spo2_low": {"metric": "spo2", "op": "<", "value": 90, "severity": "critical"},
    "rhr_above_baseline": {
        "metric": "resting_hr",
        "op": "pct_above_baseline",
        "value": 15,
        "severity": "warning",
    },
    "hrv_below_baseline": {
        "metric": "hrv",
        "op": "pct_below_baseline",
        "value": 30,
        "severity": "warning",
    },
}


class AlertRule(BaseModel):
    rule_id: str
    metric: str
    op: str
    value: float
    severity: str = "warning"
    enabled: bool = True
    custom: bool = False


class AlertEvent(BaseModel):
    alert_id: str
    rule_id: str
    metric: str
    value: float
    threshold: float
    severity: str
    timestamp: float
    source: str | None = None
    caveat: str = "Observation only — not a diagnosis."
    active: bool = True


class AlertEngine:
    def __init__(self, db_path: Path | str | None = None, metrics: HealthMetricsStore | None = None) -> None:
        if db_path is None:
            from backend.config import get_settings

            db_path = Path(get_settings().data_dir) / "aegis_alerts.sqlite3"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.metrics = metrics or HealthMetricsStore()
        self._init()
        self._ensure_defaults()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS alert_rules (
                    rule_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS alert_events (
                    alert_id TEXT PRIMARY KEY,
                    fingerprint TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    active INTEGER NOT NULL
                )
                """
            )
            conn.commit()

    def _ensure_defaults(self) -> None:
        with self._connect() as conn:
            for rid, spec in DEFAULT_THRESHOLDS.items():
                row = conn.execute(
                    "SELECT 1 FROM alert_rules WHERE rule_id = ?", (rid,)
                ).fetchone()
                if row is None:
                    rule = AlertRule(rule_id=rid, custom=False, **spec)
                    conn.execute(
                        "INSERT INTO alert_rules(rule_id, payload_json) VALUES (?, ?)",
                        (rid, rule.model_dump_json()),
                    )
            conn.commit()

    def list_rules(self) -> list[AlertRule]:
        with self._connect() as conn:
            rows = conn.execute("SELECT payload_json FROM alert_rules").fetchall()
        return [AlertRule.model_validate_json(r["payload_json"]) for r in rows]

    def upsert_rule(self, rule: AlertRule) -> AlertRule:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO alert_rules(rule_id, payload_json) VALUES (?, ?)",
                (rule.rule_id, rule.model_dump_json()),
            )
            conn.commit()
        return rule

    def set_enabled(self, rule_id: str, enabled: bool) -> AlertRule:
        rules = {r.rule_id: r for r in self.list_rules()}
        if rule_id not in rules:
            raise KeyError(rule_id)
        rule = rules[rule_id].model_copy(update={"enabled": enabled})
        return self.upsert_rule(rule)

    def _baseline(self, metric: str) -> float | None:
        pts = self.metrics.series(metric, limit=30)
        if len(pts) < 2:
            return None
        # exclude latest point
        vals = [p.value for p in pts[:-1]]
        return sum(vals) / len(vals) if vals else None

    def _triggered(self, rule: AlertRule, value: float) -> bool:
        if rule.op == ">":
            return value > rule.value
        if rule.op == "<":
            return value < rule.value
        if rule.op == "pct_above_baseline":
            base = self._baseline(rule.metric)
            if base is None or base == 0:
                return False
            return ((value - base) / base) * 100 > rule.value
        if rule.op == "pct_below_baseline":
            base = self._baseline(rule.metric)
            if base is None or base == 0:
                return False
            return ((base - value) / base) * 100 > rule.value
        return False

    def evaluate(self) -> list[AlertEvent]:
        fired: list[AlertEvent] = []
        for rule in self.list_rules():
            if not rule.enabled:
                continue
            latest = self.metrics.latest(rule.metric)
            if latest is None:
                continue
            if not self._triggered(rule, latest.value):
                continue
            fp = f"{rule.rule_id}:{latest.value}:{latest.day or int(latest.observed_at)}"
            with self._connect() as conn:
                existing = conn.execute(
                    "SELECT payload_json FROM alert_events WHERE fingerprint = ? AND active = 1",
                    (fp,),
                ).fetchone()
            if existing:
                continue  # duplicate suppression
            event = AlertEvent(
                alert_id=uuid.uuid4().hex[:12],
                rule_id=rule.rule_id,
                metric=rule.metric,
                value=latest.value,
                threshold=rule.value,
                severity=rule.severity,
                timestamp=time.time(),
                source=(latest.provenance.source.value if latest.provenance else None),
            )
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO alert_events(alert_id, fingerprint, payload_json, active) VALUES (?, ?, ?, 1)",
                    (event.alert_id, fp, event.model_dump_json()),
                )
                conn.commit()
            fired.append(event)
        return fired

    def active(self) -> list[AlertEvent]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM alert_events WHERE active = 1 ORDER BY alert_id"
            ).fetchall()
        return [AlertEvent.model_validate_json(r["payload_json"]) for r in rows]

    def history(self, limit: int = 50) -> list[AlertEvent]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM alert_events ORDER BY rowid DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [AlertEvent.model_validate_json(r["payload_json"]) for r in rows]
