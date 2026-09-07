"""Macro Pool ledger — protein target fill blended into diet scoring."""

from __future__ import annotations

from backend.intake.schema import IntakeResult
from backend.scorers.diet import score_basic

DEFAULT_PROTEIN_TARGET_G = 140


def macro_pool_status(
    intake: IntakeResult, protein_target_g: int = DEFAULT_PROTEIN_TARGET_G
) -> dict:
    """Daily protein pool vs target, blended with meal-pattern diet score."""
    protein = sum(int(m.protein_g or 0) for m in intake.meals)
    fill = min(1.0, protein / protein_target_g) if protein_target_g else 0.0
    base = score_basic(intake)["score"]
    pool_score = int(round(fill * 100))
    score = int(round(0.4 * base + 0.6 * pool_score))
    return {
        "score": score,
        "protein_g": protein,
        "protein_target_g": protein_target_g,
        "fill_ratio": round(fill, 2),
        "remaining_protein_g": max(0, protein_target_g - protein),
        "base_diet_score": base,
        "pool_score": pool_score,
        "rationale": (
            f"Macro Pool protein {protein}/{protein_target_g}g "
            f"(fill {fill:.0%}); blended diet score {score}/100."
        ),
    }
