"""Deterministic readiness scorers. Pure rule-based, no LLM."""
from src.backend.scorers.sleep import score_sleep
from src.backend.scorers.soreness import score_soreness
from src.backend.scorers.diet import score_diet
from src.backend.scorers.hydration import score_hydration
from src.backend.scorers.performance import score_performance
from src.backend.scorers.readiness import score_readiness

def score_all(intake) -> dict:
    """Run all scorers and return results keyed by dimension."""
    return {
        "sleep": score_sleep(intake),
        "soreness": score_soreness(intake),
        "diet": score_diet(intake),
        "hydration": score_hydration(intake),
        "performance": score_performance(intake),
        "readiness": score_readiness(intake),
    }

__all__ = [
    "score_sleep", "score_soreness", "score_diet",
    "score_hydration", "score_performance", "score_readiness",
    "score_all",
]
