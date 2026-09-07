"""Canonical health scorers + transitional readiness bridge."""

from __future__ import annotations

from backend.intake.schema import IntakeResult
from backend.scorers import score_all as score_transitional
from backend.scorers.diet import score as score_diet
from backend.scorers.sleep import score as score_sleep
from backend.scorers.soreness import score as score_soreness


def score_front_rack(intake: IntakeResult) -> dict:
    """Front-rack mobility readiness from upper-body soreness / mentions."""
    upper = {
        "shoulder",
        "shoulders",
        "wrist",
        "wrists",
        "elbow",
        "elbows",
        "thoracic",
        "upper back",
        "forearm",
        "forearms",
    }
    relevant = [s for s in intake.soreness if any(u in s.body_part.lower() for u in upper)]
    if not relevant:
        # No front-rack limitation stated → assume open
        return {
            "score": 90,
            "factors": {"areas": [], "note": "no front-rack limitation reported"},
            "rationale": "Front-rack scored 90/100: no limiting upper-body soreness reported.",
        }
    # Reuse soreness penalties on relevant areas only
    from backend.scorers.soreness import _SEVERITY_PENALTY, _PENALTY_CAP, _clamp

    per = [
        {"body_part": s.body_part, "severity": s.severity, "penalty": _SEVERITY_PENALTY[max(1, min(5, s.severity))]}
        for s in relevant
    ]
    penalty = min(_PENALTY_CAP, sum(a["penalty"] for a in per))
    value = _clamp(100 - penalty)
    return {
        "score": value,
        "factors": {"areas": per, "total_penalty": penalty},
        "rationale": f"Front-rack scored {value}/100 from upper-body limitation penalties ({penalty}).",
    }


def score_workout_preparation(intake: IntakeResult) -> dict:
    """Readiness for today's specific WOD = blend of sleep, soreness, subjective, front-rack."""
    sleep_s = score_sleep(intake)["score"]
    soreness_s = score_soreness(intake)["score"]
    fr = score_front_rack(intake)["score"]
    transitional = score_transitional(intake)
    subjective = transitional["readiness"]["factors"]["components"]["subjective"]
    # Heavier weight on movement-specific readiness when WOD present
    if intake.todays_wod.movements:
        weights = {"sleep": 0.25, "soreness": 0.25, "front_rack": 0.25, "subjective": 0.25}
    else:
        weights = {"sleep": 0.3, "soreness": 0.3, "front_rack": 0.1, "subjective": 0.3}
    comps = {
        "sleep": sleep_s,
        "soreness": soreness_s,
        "front_rack": fr,
        "subjective": subjective,
    }
    value = max(0, min(100, round(sum(comps[k] * weights[k] for k in weights))))
    return {
        "score": value,
        "factors": {"components": comps, "weights": weights, "wod": intake.todays_wod.movements},
        "rationale": f"Workout preparation scored {value}/100 for today's plan.",
    }


def score_overall(intake: IntakeResult) -> dict:
    fr = score_front_rack(intake)["score"]
    sleep_s = score_sleep(intake)["score"]
    diet_s = score_diet(intake)["score"]
    wp = score_workout_preparation(intake)["score"]
    value = max(0, min(100, round(0.25 * fr + 0.25 * sleep_s + 0.25 * diet_s + 0.25 * wp)))
    return {
        "score": value,
        "factors": {
            "front_rack": fr,
            "sleep": sleep_s,
            "diet": diet_s,
            "workout_preparation": wp,
        },
        "rationale": f"Overall health/fitness scored {value}/100 from canonical four scores.",
    }


def score_canonical(intake: IntakeResult) -> dict:
    """Product-contract scores (+ transitional block for compatibility)."""
    from backend.scorers.macro_pool import macro_pool_status

    transitional = score_transitional(intake)
    diet = score_diet(intake)
    return {
        "front_rack": score_front_rack(intake),
        "sleep": score_sleep(intake),
        "diet": diet,
        "macro_pool": macro_pool_status(intake),
        "workout_preparation": score_workout_preparation(intake),
        "overall": score_overall(intake),
        # transitional — not permanent top-level contract
        "transitional": transitional,
    }
