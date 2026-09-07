"""Sleep scorer. Higher = better recovered."""

from src.backend.models.intake import IntakeResult

_POSITIVE = {"great", "excellent", "amazing", "good", "solid", "deep", "well", "restful"}
_NEUTRAL = {"ok", "okay", "fair", "decent", "average", "meh", "fine", "alright"}
_NEGATIVE = {"poor", "bad", "terrible", "awful", "horrible", "broken", "rough", "barely"}


def _clamp(n: int) -> int:
    return max(0, min(100, n))


def _quality_score(quality: str | None) -> tuple[int, str]:
    q = (quality or "").lower()
    if any(w in q for w in _NEGATIVE):
        return 20, "poor"
    if any(w in q for w in _POSITIVE):
        return 88, "good"
    if any(w in q for w in _NEUTRAL):
        return 60, "neutral"
    if q:
        return 55, "unrecognized"
    return 50, "unknown"


def _hours_score(hours: float) -> int:
    if 7 <= hours <= 9:
        return 95
    if 6 <= hours < 7 or 9 < hours <= 10:
        return 75
    if 5 <= hours < 6:
        return 50
    if hours < 5:
        return 25
    return 60  # oversleep (>10h)


def score_sleep(intake: IntakeResult) -> dict:
    sleep = intake.sleep
    if not sleep:
        return {"score": 50, "factors": {"quality": "not reported", "quality_band": "unknown", "quality_score": 50, "hours": None}}

    qscore, qband = _quality_score(sleep.quality)

    factors = {"quality": sleep.quality, "quality_band": qband, "quality_score": qscore, "hours": sleep.hours}

    if sleep.hours is not None:
        hscore = _hours_score(sleep.hours)
        factors["hours_score"] = hscore
        value = _clamp(round(0.5 * qscore + 0.5 * hscore))
    else:
        value = _clamp(qscore)

    return {"score": value, "factors": factors}
