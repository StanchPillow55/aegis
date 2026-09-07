"""Deterministic readiness scorers (SC-SCORE-01).

Four pure, rule-based scorers (no LLM) plus `score_all` to aggregate them.
Each scorer has the signature `(intake: IntakeResult) -> dict` returning
`{"score": int (0-100), "factors": dict, "rationale": str}`.
"""

from backend.intake.schema import IntakeResult
from backend.scorers.diet import score as score_diet
from backend.scorers.readiness import score as score_readiness
from backend.scorers.sleep import score as score_sleep
from backend.scorers.soreness import score as score_soreness

__all__ = [
    "score_sleep",
    "score_diet",
    "score_soreness",
    "score_readiness",
    "score_all",
]


def score_all(intake: IntakeResult) -> dict:
    """Run all four scorers and return them keyed by dimension."""
    return {
        "sleep": score_sleep(intake),
        "diet": score_diet(intake),
        "soreness": score_soreness(intake),
        "readiness": score_readiness(intake),
    }
