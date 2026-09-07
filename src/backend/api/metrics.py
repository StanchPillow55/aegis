import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query, Header, HTTPException

from src.backend.storage.sqlite_store import _get_connection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/metrics", tags=["metrics"])

@router.get("")
def get_metrics(
    x_user_id: str = Header(...),
    metric_type: Optional[str] = None,
    days: int = Query(30, ge=1, le=365)
):
    conn = _get_connection()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    query = "SELECT timestamp, metric_type, value, unit FROM health_metrics WHERE user_id = ? AND timestamp >= ?"
    params = [x_user_id, cutoff]
    
    if metric_type:
        query += " AND metric_type = ?"
        params.append(metric_type)
        
    query += " ORDER BY timestamp ASC"
    
    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for r in rows:
        results.append({
            "timestamp": r["timestamp"],
            "metric_type": r["metric_type"],
            "value": r["value"],
            "unit": r["unit"]
        })
    return results
