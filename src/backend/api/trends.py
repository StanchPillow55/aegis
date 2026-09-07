"""GET /api/trends — aggregated score trends for charts."""

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Query, Header

from src.backend.storage.sqlite_store import get_scores_range
from src.backend.patterns.trends import weekly_averages, trend_direction

router = APIRouter(prefix="/api", tags=["trends"])


@router.get("/trends/scores")
async def score_trends(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    x_user_id: str = Header(...),
):
    """Get time-series scores for the main trend chart."""
    end_date = date.fromisoformat(end) if end else date.today()
    start_date = date.fromisoformat(start) if start else end_date - timedelta(days=30)
    
    scores = get_scores_range(x_user_id, start_date, end_date)
    return {"scores": scores}


@router.get("/trends/weekly")
async def weekly_trend(weeks: int = Query(4)):
    """Get weekly average scores."""
    return {"weeks": weekly_averages(weeks=weeks)}


@router.get("/trends/direction")
async def trend_directions():
    """Get trend direction (up/down/flat) for each dimension."""
    dimensions = ["sleep", "soreness", "diet", "hydration", "readiness"]
    return {dim: trend_direction(dim) for dim in dimensions}
