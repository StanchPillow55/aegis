"""Deterministic readiness scorer (SC-SCORE-01).

Pure, rule-based, no LLM. The overall training-readiness signal: a weighted
blend of the sleep, soreness, and diet subscores plus the athlete's own
`subjective_readiness` label. Recovery factors (sleep, soreness) dominate;
diet is a smaller contributor.
"""

from backend.intake.schema import IntakeResult
from backend.scorers.diet import score as _score_diet
from backend.scorers.sleep import score as _score_sleep
from backend.scorers.soreness import score as _score_soreness

# Component weights (must sum to 1.0).
_WEIGHTS = {"sleep": 0.30, "soreness": 0.30, "subjective": 0.25, "diet": 0.15}

_SUBJECTIVE = {"low": 25, "moderate": 60, "medium": 60, "high": 90}
_SUBJECTIVE_POS = {"great", "good", "ready", "fresh", "strong"}
_SUBJECTIVE_NEG = {"low", "poor", "bad", "tired", "exhausted", "drained", "flat"}


def _clamp(n: int) -> int:
    return max(0, min(100, n))


def _subjective_score(label: str | None) -> tuple[int, str]:
    s = (label or "").lower().strip()
    if s in _SUBJECTIVE:
        return _SUBJECTIVE[s], s
    if any(w in s for w in _SUBJECTIVE_NEG):
        return 25, "low"
    if "high" in s:
        return 90, "high"
    if any(w in s for w in _SUBJECTIVE_POS):
        return 80, "good"
    if s:
        return 55, "unrecognized"
    return 55, "unknown"


def score(intake: IntakeResult) -> dict:
    sleep_s = _score_sleep(intake)["score"]
    soreness_s = _score_soreness(intake)["score"]
    diet_s = _score_diet(intake)["score"]
    subjective_s, subjective_band = _subjective_score(intake.subjective_readiness)

    components = {
        "sleep": sleep_s,
        "soreness": soreness_s,
        "subjective": subjective_s,
        "diet": diet_s,
    }
    value = _clamp(round(sum(components[k] * w for k, w in _WEIGHTS.items())))

    factors = {
        "components": components,
        "weights": _WEIGHTS,
        "subjective_label": intake.subjective_readiness,
        "subjective_band": subjective_band,
    }
    rationale = (
        f"Readiness scored {value}/100 = weighted blend of "
        f"sleep {sleep_s} (×{_WEIGHTS['sleep']}), "
        f"soreness {soreness_s} (×{_WEIGHTS['soreness']}), "
        f"subjective {subjective_s} (×{_WEIGHTS['subjective']}), "
        f"diet {diet_s} (×{_WEIGHTS['diet']})."
    )
    return {"score": value, "factors": factors, "rationale": rationale}
