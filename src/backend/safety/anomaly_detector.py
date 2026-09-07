from typing import List, Optional
from datetime import datetime, timezone
import uuid

from src.backend.models.health_metrics import HealthMetric, MetricType
from src.backend.models.safety import SafetyThreshold, Alert, ThresholdCondition, Severity
from src.backend.storage.sqlite_store import _get_connection

def get_system_defaults() -> List[SafetyThreshold]:
    return [
        SafetyThreshold(
            id=str(uuid.uuid4()),
            metric_type=MetricType.heart_rate,
            condition=ThresholdCondition.above,
            value=200.0,
            severity=Severity.critical,
            message="Heart rate exceeded 200bpm — consider stopping and resting",
            is_system_default=True
        ),
        SafetyThreshold(
            id=str(uuid.uuid4()),
            metric_type=MetricType.spo2,
            condition=ThresholdCondition.below,
            value=90.0,
            severity=Severity.critical,
            message="Blood oxygen is dangerously low — seek medical attention",
            is_system_default=True
        ),
        SafetyThreshold(
            id=str(uuid.uuid4()),
            metric_type=MetricType.resting_heart_rate,
            condition=ThresholdCondition.delta_above,
            value=15.0, # 15% above
            window_hours=168, # 7 days
            severity=Severity.warning,
            message="Resting HR is elevated compared to baseline",
            is_system_default=True
        ),
        SafetyThreshold(
            id=str(uuid.uuid4()),
            metric_type=MetricType.hrv,
            condition=ThresholdCondition.delta_below,
            value=-30.0, # 30% below
            window_hours=168,
            severity=Severity.warning,
            message="HRV is significantly below baseline",
            is_system_default=True
        )
    ]

def _row_to_alert(row) -> Alert:
    a = Alert(
        id=row["id"],
        severity=Severity(row["severity"]),
        metric_type=MetricType(row["metric_type"]),
        current_value=row["metric_value"],
        threshold_value=row["threshold_value"],
        message=row["message"],
        timestamp=datetime.fromisoformat(row["timestamp"])
    )
    a.acknowledged = not bool(row["is_active"])
    return a

def save_alert(alert: Alert, user_id: str) -> None:
    conn = _get_connection()
    conn.execute("""
        INSERT INTO safety_alerts (
            id, user_id, severity, message, metric_type, metric_value, 
            threshold_value, timestamp, is_active, resolved_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        alert.id, user_id, alert.severity.value, alert.message, 
        alert.metric_type.value, alert.current_value, alert.threshold_value,
        alert.timestamp.isoformat(), int(not alert.acknowledged),
        datetime.now(timezone.utc).isoformat() if alert.acknowledged else None
    ))
    conn.commit()
    conn.close()

def get_active_alerts(user_id: str) -> List[Alert]:
    conn = _get_connection()
    rows = conn.execute("SELECT * FROM safety_alerts WHERE user_id = ? AND is_active = 1", (user_id,)).fetchall()
    conn.close()
    return [_row_to_alert(r) for r in rows]

def get_alert_history(user_id: str, limit: int = 50) -> List[Alert]:
    conn = _get_connection()
    rows = conn.execute("SELECT * FROM safety_alerts WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?", (user_id, limit)).fetchall()
    conn.close()
    return [_row_to_alert(r) for r in rows]

def resolve_alert(alert_id: str, user_id: str) -> bool:
    conn = _get_connection()
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        "UPDATE safety_alerts SET is_active = 0, resolved_at = ? WHERE id = ? AND user_id = ?",
        (now, alert_id, user_id)
    )
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return affected

def check_metric_against_thresholds(
    metric: HealthMetric, 
    thresholds: List[SafetyThreshold],
    user_id: str,
    baseline_value: Optional[float] = None
) -> Optional[Alert]:
    """Check a single metric against a list of thresholds."""
    for t in thresholds:
        if t.metric_type != metric.metric_type:
            continue
            
        triggered = False
        if t.condition == ThresholdCondition.above and metric.value > t.value:
            triggered = True
        elif t.condition == ThresholdCondition.below and metric.value < t.value:
            triggered = True
        elif t.condition == ThresholdCondition.delta_above and baseline_value is not None:
            pct_change = ((metric.value - baseline_value) / baseline_value) * 100
            if pct_change > t.value:
                triggered = True
        elif t.condition == ThresholdCondition.delta_below and baseline_value is not None:
            pct_change = ((metric.value - baseline_value) / baseline_value) * 100
            if pct_change < t.value: # e.g. -35 < -30
                triggered = True
                
        if triggered:
            alert = Alert(
                id=str(uuid.uuid4()),
                severity=t.severity,
                metric_type=metric.metric_type,
                current_value=metric.value,
                threshold_value=t.value,
                message=t.message,
                timestamp=datetime.now(timezone.utc)
            )
            save_alert(alert, user_id)
            return alert
            
    return None
