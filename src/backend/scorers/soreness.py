"""Soreness scorer. Higher = less sore = more recovered."""

from src.backend.models.intake import IntakeResult

_SEVERITY_PENALTY = {1: 8, 2: 18, 3: 30, 4: 45, 5: 60}
_PENALTY_CAP = 90


def _clamp(n: int) -> int:
    return max(0, min(100, n))


def score_soreness(intake: IntakeResult) -> dict:
    soreness = intake.soreness or []
    if not soreness:
        return {"score": 100, "factors": {"sore_areas": 0, "total_penalty": 0}}

    per_area = []
    for s in soreness:
        sev = s.severity if s.severity is not None else 2
        sev = max(1, min(5, sev))
        penalty = _SEVERITY_PENALTY[sev]
        per_area.append({"body_part": s.body_part, "severity": sev, "penalty": penalty})

    total_penalty = min(_PENALTY_CAP, sum(a["penalty"] for a in per_area))
    value = _clamp(100 - total_penalty)

    return {"score": value, "factors": {"sore_areas": len(soreness), "areas": per_area, "total_penalty": total_penalty}}
