"""WOD negotiation based on front-rack / workout-prep scores."""

from __future__ import annotations

from backend.intake.schema import IntakeResult, WOD
from backend.scorers.canonical import score_front_rack, score_workout_preparation

FRONT_RACK_MOVEMENTS = {
    "clean",
    "cleans",
    "thruster",
    "thrusters",
    "front squat",
    "front squats",
    "wall ball",
    "wall balls",
    "jerk",
    "push jerk",
}


def negotiate_wod(intake: IntakeResult) -> dict:
    wod = intake.todays_wod
    fr = score_front_rack(intake)["score"]
    wp = score_workout_preparation(intake)["score"]
    movements = list(wod.movements)
    lower = [m.lower() for m in movements]
    fr_hits = [m for m in movements if any(x in m.lower() for x in FRONT_RACK_MOVEMENTS)]

    if not movements:
        return {
            "status": "as_prescribed",
            "original": wod.model_dump(),
            "modified": wod.model_dump(),
            "reasons": ["No WOD movements provided"],
            "scores": {"front_rack": fr, "workout_preparation": wp},
        }

    if wp < 40:
        return {
            "status": "deferred",
            "original": wod.model_dump(),
            "modified": WOD(movements=[], raw="Deferred — recovery priority").model_dump(),
            "reasons": [f"Workout preparation {wp}/100 below defer threshold"],
            "scores": {"front_rack": fr, "workout_preparation": wp},
        }

    if fr < 55 and fr_hits:
        substituted = []
        for m in movements:
            if any(x in m.lower() for x in FRONT_RACK_MOVEMENTS):
                substituted.append(f"{m}→goblet squat/DB press")
            else:
                substituted.append(m)
        return {
            "status": "substituted",
            "original": wod.model_dump(),
            "modified": WOD(movements=substituted, raw=wod.raw).model_dump(),
            "reasons": [
                f"Front-rack {fr}/100 limited for: {', '.join(fr_hits)}",
            ],
            "scores": {"front_rack": fr, "workout_preparation": wp},
        }

    if wp < 65:
        return {
            "status": "scaled",
            "original": wod.model_dump(),
            "modified": WOD(
                movements=movements,
                raw=(wod.raw or "") + " [scaled: -20–30% volume]",
            ).model_dump(),
            "reasons": [f"Workout preparation {wp}/100 → scale volume"],
            "scores": {"front_rack": fr, "workout_preparation": wp},
        }

    return {
        "status": "as_prescribed",
        "original": wod.model_dump(),
        "modified": wod.model_dump(),
        "reasons": ["Scores support prescribed work"],
        "scores": {"front_rack": fr, "workout_preparation": wp},
    }
