"""GET /api/directive — today's training recommendation."""

from datetime import date

from fastapi import APIRouter, Header

from src.backend.storage.sqlite_store import get_log_by_date
from src.backend.storage.chroma_store import get_similar_days

router = APIRouter(prefix="/api", tags=["directive"])


@router.get("/directive")
async def todays_directive(x_user_id: str = Header(default="default_user")):
    """Generate today's training recommendation based on current state."""
    today_log = get_log_by_date(x_user_id, date.today())

    if not today_log or not today_log.scores:
        return {
            "directive": "No data logged today yet. Log your daily update to get a recommendation.",
            "has_data": False,
        }

    scores = today_log.scores
    readiness = scores.readiness
    
    # Find similar historical days for context
    similar = get_similar_days(x_user_id, today_log, n=3)

    # Rule-based directive generation
    directives = []
    
    if readiness >= 80:
        directives.append("You're in a great spot. Full send on today's workout.")
    elif readiness >= 60:
        directives.append("Solid readiness. Train as programmed.")
    elif readiness >= 40:
        directives.append("Moderate readiness. Consider scaling intensity by 10-15%.")
    else:
        directives.append("Low readiness. Prioritize recovery — active rest or mobility work.")

    # Soreness-specific guidance
    if today_log.intake.soreness:
        high_soreness = [s for s in today_log.intake.soreness if s.severity >= 3]
        if high_soreness:
            areas = ", ".join(s.body_part for s in high_soreness)
            directives.append(f"Watch {areas} — consider movement substitutions that reduce load on these areas.")

    # Sleep warning
    if scores.sleep < 50:
        directives.append("Poor sleep recovery. Keep volume moderate and avoid max-effort lifts.")

    # Hydration warning
    if scores.hydration < 50:
        directives.append("Hydration is low. Prioritize water intake before and during training.")

    return {
        "directive": " ".join(directives),
        "readiness_score": readiness,
        "scores": scores.model_dump(),
        "similar_days": similar[:2],
        "has_data": True,
    }
