from fastapi import APIRouter, HTTPException, Header
from typing import List
from src.backend.models.safety import SafetyThreshold, ThresholdCondition, Severity
from src.backend.models.health_metrics import MetricType
from src.backend.safety.anomaly_detector import get_system_defaults
from src.backend.storage.sqlite_store import _get_connection

router = APIRouter(prefix="/api/settings", tags=["settings"])

def _seed_defaults_if_empty(conn):
    count = conn.execute("SELECT COUNT(*) FROM safety_thresholds WHERE is_system_default=1").fetchone()[0]
    if count == 0:
        for t in get_system_defaults():
            conn.execute(
                "INSERT OR IGNORE INTO safety_thresholds (id, metric_type, condition, value, window_hours, severity, message, is_system_default, user_modified) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (t.id, t.metric_type.value, t.condition.value, t.value, t.window_hours, t.severity.value, t.message, 1, 0)
            )
        conn.commit()

def _row_to_threshold(row) -> SafetyThreshold:
    return SafetyThreshold(
        id=row["id"],
        metric_type=MetricType(row["metric_type"]),
        condition=ThresholdCondition(row["condition"]),
        value=row["value"],
        window_hours=row["window_hours"],
        severity=Severity(row["severity"]),
        message=row["message"],
        is_system_default=bool(row["is_system_default"]),
        user_modified=bool(row["user_modified"])
    )

@router.get("/thresholds", response_model=List[SafetyThreshold])
def list_thresholds(x_user_id: str = Header(default="default_user")):
    """List all safety thresholds (system defaults + user modifications)."""
    conn = _get_connection()
    _seed_defaults_if_empty(conn)
    rows = conn.execute(
        "SELECT * FROM safety_thresholds WHERE is_system_default=1 OR user_id=?", 
        (x_user_id,)
    ).fetchall()
    conn.close()
    return [_row_to_threshold(r) for r in rows]

@router.post("/thresholds", response_model=SafetyThreshold)
def create_threshold(threshold: SafetyThreshold, x_user_id: str = Header(default="default_user")):
    """Create a new custom safety threshold."""
    conn = _get_connection()
    conn.execute(
        "INSERT INTO safety_thresholds (id, user_id, metric_type, condition, value, window_hours, severity, message, is_system_default, user_modified) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 1)",
        (threshold.id, x_user_id, threshold.metric_type.value, threshold.condition.value, threshold.value, threshold.window_hours, threshold.severity.value, threshold.message)
    )
    conn.commit()
    conn.close()
    
    threshold.is_system_default = False
    threshold.user_modified = True
    return threshold

@router.delete("/thresholds/{threshold_id}")
def delete_threshold(threshold_id: str, x_user_id: str = Header(default="default_user")):
    """Delete a custom safety threshold."""
    conn = _get_connection()
    cursor = conn.execute(
        "DELETE FROM safety_thresholds WHERE id=? AND (user_id=? OR is_system_default=0)",
        (threshold_id, x_user_id)
    )
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    if not affected:
        raise HTTPException(status_code=404, detail="Threshold not found or cannot be deleted")
        
    return {"status": "success"}
