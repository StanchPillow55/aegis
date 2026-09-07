from fastapi import APIRouter, HTTPException, Header
from typing import List
from src.backend.models.safety import Alert
from src.backend.safety.anomaly_detector import get_active_alerts, resolve_alert

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

@router.get("", response_model=List[Alert])
def list_active_alerts(x_user_id: str = Header(default="default_user")):
    """Get all active, unacknowledged alerts."""
    return get_active_alerts(x_user_id)

@router.post("/{alert_id}/acknowledge")
def ack_alert(alert_id: str, x_user_id: str = Header(default="default_user")):
    """Acknowledge an alert to clear it from the active list."""
    success = resolve_alert(alert_id, x_user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"status": "success"}
