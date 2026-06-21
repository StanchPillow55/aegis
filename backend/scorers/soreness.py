"""Deterministic soreness scorer (SC-SCORE-01).

Pure, rule-based, no LLM. This scores RECOVERY: more / more-severe soreness ->
LOWER score. No soreness reported -> fully recovered (100).
"""

from backend.intake.schema import IntakeResult, Soreness

# Per-area penalty by the 1-5 severity scale (frozen contract).
_SEVERITY_PENALTY = {1: 8, 2: 18, 3: 30, 4: 45, 5: 60}
_PENALTY_CAP = 90  # never drive recovery fully to 0 from soreness alone


def _clamp(n: int) -> int:
    return max(0, min(100, n))


def _area_penalty(area: Soreness) -> int:
    sev = max(1, min(5, area.severity))  # defensive clamp to the 1-5 scale
    return _SEVERITY_PENALTY[sev]


def score(intake: IntakeResult) -> dict:
    soreness = intake.soreness

    if not soreness:
        return {
            "score": 100,
            "factors": {"sore_areas": 0, "areas": [], "total_penalty": 0},
            "rationale": "Soreness scored 100/100: no soreness reported — fully recovered.",
        }

    per_area = [
        {"body_part": s.body_part, "severity": s.severity, "penalty": _area_penalty(s)}
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
        f"(worst: {worst['body_part']} sev {worst['severity']}, penalty {worst['penalty']}), "
        f"total penalty {total_penalty}."
    )
    return {"score": value, "factors": factors, "rationale": rationale}
