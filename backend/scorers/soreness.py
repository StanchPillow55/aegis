"""Deterministic soreness scorer (SC-SCORE-01).

Pure, rule-based, no LLM. This scores RECOVERY: more / more-severe soreness ->
LOWER score. No soreness reported -> fully recovered (100).
"""

from backend.intake.schema import IntakeResult, Soreness

# Per-area penalty by severity keyword.
_SEVERITY_PENALTY = {"mild": 10, "moderate": 30, "severe": 55}
_UNKNOWN_SEVERITY_PENALTY = 25  # an area was named but no severity given
_PENALTY_CAP = 90  # never drive recovery fully to 0 from soreness alone

# Keyword escalation when severity isn't a clean label.
_SEVERE_WORDS = {"severe", "cooked", "wrecked", "destroyed", "extreme", "intense", "very"}
_MILD_WORDS = {"mild", "slight", "little", "minor", "bit"}


def _clamp(n: int) -> int:
    return max(0, min(100, n))


def _area_penalty(area: Soreness) -> int:
    text = f"{area.severity or ''} {area.note or ''}".lower()
    sev = (area.severity or "").lower().strip()
    if sev in _SEVERITY_PENALTY:
        return _SEVERITY_PENALTY[sev]
    if any(w in text for w in _SEVERE_WORDS):
        return _SEVERITY_PENALTY["severe"]
    if any(w in text for w in _MILD_WORDS):
        return _SEVERITY_PENALTY["mild"]
    return _UNKNOWN_SEVERITY_PENALTY


def score(intake: IntakeResult) -> dict:
    soreness = intake.soreness

    if not soreness:
        return {
            "score": 100,
            "factors": {"sore_areas": 0, "areas": [], "total_penalty": 0},
            "rationale": "Soreness scored 100/100: no soreness reported — fully recovered.",
        }

    per_area = [
        {"area": s.area, "severity": s.severity, "penalty": _area_penalty(s)}
        for s in soreness
    ]
    total_penalty = min(_PENALTY_CAP, sum(a["penalty"] for a in per_area))
    value = _clamp(100 - total_penalty)

    factors = {
        "sore_areas": len(soreness),
        "areas": per_area,
        "total_penalty": total_penalty,
    }
    worst = max(per_area, key=lambda a: a["penalty"])
    rationale = (
        f"Soreness scored {value}/100: {len(soreness)} sore area(s) "
        f"(worst: {worst['area']}, penalty {worst['penalty']}), "
        f"total penalty {total_penalty}."
    )
    return {"score": value, "factors": factors, "rationale": rationale}
