"""GET /api/logs — retrieve daily logs by date range."""

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Query, Header

from src.backend.storage.sqlite_store import get_log_by_date, get_logs_range

router = APIRouter(prefix="/api", tags=["logs"])


@router.get("/logs")
async def list_logs(
    start: Optional[str] = Query(None, description="Start date (ISO format)"),
    end: Optional[str] = Query(None, description="End date (ISO format)"),
    days: int = Query(7, description="Number of days back from end (default 7)"),
    x_user_id: str = Header(...),
):
    """Get logs for a date range. Defaults to last 7 days."""
    end_date = date.fromisoformat(end) if end else date.today()
    start_date = date.fromisoformat(start) if start else end_date - timedelta(days=days)

    logs = get_logs_range(x_user_id, start_date, end_date)
    return {
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "count": len(logs),
        "logs": [
            {
                "id": log.id,
                "date": log.date.isoformat(),
                "scores": log.scores.model_dump() if log.scores else None,
                "intake": log.intake.model_dump(),
                "raw_input": log.raw_input,
            }
            for log in logs
        ],
    }


@router.get("/logs/{log_date}")
async def get_log(log_date: str, x_user_id: str = Header(default="default_user")):
    """Get a single day's log."""
    d = date.fromisoformat(log_date)
    log = get_log_by_date(x_user_id, d)
    if not log:
        return {"error": "No log found for this date"}, 404
    return {
        "id": log.id,
        "date": log.date.isoformat(),
        "scores": log.scores.model_dump() if log.scores else None,
        "intake": log.intake.model_dump(),
        "raw_input": log.raw_input,
    }
