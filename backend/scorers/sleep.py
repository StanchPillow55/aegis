"""Deterministic sleep scorer (SC-SCORE-01).

Pure, rule-based, no LLM. Higher score = better-recovered sleep. Blends a
qualitative read of `sleep.quality` with `sleep.hours` when reported.
"""

from backend.intake.schema import IntakeResult

# Quality keyword buckets (substring match, lowercased).
_POSITIVE = {
    "great",
    "excellent",
    "amazing",
    "good",
    "solid",
    "deep",
    "well",
    "restful",
}
_NEUTRAL = {"ok", "okay", "fair", "decent", "average", "meh", "fine", "alright"}
_NEGATIVE = {
    "poor",
    "bad",
    "terrible",
    "awful",
    "horrible",
    "broken",
    "rough",
    "badly",
    "barely",
}


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


def score(intake: IntakeResult) -> dict:
    sleep = intake.sleep
    qscore, qband = _quality_score(sleep.quality)

    factors: dict = {
        "quality": sleep.quality,
        "quality_band": qband,
        "quality_score": qscore,
        "hours": sleep.hours,
    }

    if sleep.hours is not None:
        hscore = _hours_score(sleep.hours)
        factors["hours_score"] = hscore
        value = _clamp(round(0.5 * qscore + 0.5 * hscore))
        basis = f"quality ('{sleep.quality}'={qscore}) + {sleep.hours}h ({hscore})"
    else:
        value = _clamp(qscore)
        basis = f"quality ('{sleep.quality}'={qscore}); no hours reported"

    rationale = f"Sleep scored {value}/100 from {basis}."
    return {"score": value, "factors": factors, "rationale": rationale}
