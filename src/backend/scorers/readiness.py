"""Overall readiness scorer. Weighted blend of all sub-scores."""

from src.backend.models.intake import IntakeResult
from src.backend.scorers.sleep import score_sleep
from src.backend.scorers.soreness import score_soreness
from src.backend.scorers.diet import score_diet
from src.backend.scorers.hydration import score_hydration

_WEIGHTS = {"sleep": 0.30, "soreness": 0.30, "subjective": 0.20, "diet": 0.10, "hydration": 0.10}
_SUBJECTIVE_MAP = {"low": 25, "moderate": 60, "high": 90}
_SUBJECTIVE_POS = {"great", "good", "ready", "fresh", "strong"}
_SUBJECTIVE_NEG = {"low", "poor", "bad", "tired", "exhausted", "drained", "flat"}


def _clamp(n: int) -> int:
    return max(0, min(100, n))


def _subjective_score(label: str | None) -> int:
    s = (label or "").lower().strip()
    if s in _SUBJECTIVE_MAP:
        return _SUBJECTIVE_MAP[s]
    if any(w in s for w in _SUBJECTIVE_NEG):
        return 25
    if any(w in s for w in _SUBJECTIVE_POS):
        return 80
    return 55  # unknown / not stated


def score_readiness(intake: IntakeResult) -> dict:
    sleep_s = score_sleep(intake)["score"]
    soreness_s = score_soreness(intake)["score"]
    diet_s = score_diet(intake)["score"]
    hydration_s = score_hydration(intake)["score"]
    subjective_s = _subjective_score(intake.subjective_readiness)

    components = {
        "sleep": sleep_s,
        "soreness": soreness_s,
        "diet": diet_s,
        "hydration": hydration_s,
        "subjective": subjective_s,
    }

    value = _clamp(round(
        sleep_s * _WEIGHTS["sleep"]
        + soreness_s * _WEIGHTS["soreness"]
        + diet_s * _WEIGHTS["diet"]
        + hydration_s * _WEIGHTS["hydration"]
        + subjective_s * _WEIGHTS["subjective"]
    ))

    return {"score": value, "factors": {"components": components, "weights": _WEIGHTS}}
