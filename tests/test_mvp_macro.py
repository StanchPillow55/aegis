"""MVP-MACRO-01 — Macro Pool ledger (simple daily protein target)."""

from __future__ import annotations

from backend.intake.schema import IntakeResult, Meal
from backend.scorers.diet import score as score_diet_basic


DEFAULT_PROTEIN_TARGET_G = 140


def macro_pool_status(intake: IntakeResult, protein_target_g: int = DEFAULT_PROTEIN_TARGET_G) -> dict:
    protein = sum(int(m.protein_g or 0) for m in intake.meals)
    fill = min(1.0, protein / protein_target_g) if protein_target_g else 0.0
    # Blend classic diet score with pool fill
    base = score_diet_basic(intake)["score"]
    pool_score = int(round(fill * 100))
    score = int(round(0.4 * base + 0.6 * pool_score))
    return {
        "score": score,
        "protein_g": protein,
        "protein_target_g": protein_target_g,
        "fill_ratio": round(fill, 2),
        "remaining_protein_g": max(0, protein_target_g - protein),
        "rationale": f"Macro Pool protein {protein}/{protein_target_g}g (fill {fill:.0%}).",
    }


def test_macro_pool_not_meal_count_only():
    low = IntakeResult.model_validate(
        {
            "soreness": [],
            "sleep": {"quality": "good", "hours": 8},
            "meals": [Meal(description="salad"), Meal(description="rice"), Meal(description="apple")],
            "todays_wod": {"movements": [], "raw": None},
            "subjective_readiness": "high",
        }
    )
    high = IntakeResult.model_validate(
        {
            "soreness": [],
            "sleep": {"quality": "good", "hours": 8},
            "meals": [Meal(description="chicken", protein_g=50), Meal(description="eggs", protein_g=24)],
            "todays_wod": {"movements": [], "raw": None},
            "subjective_readiness": "high",
        }
    )
    assert macro_pool_status(high)["score"] > macro_pool_status(low)["score"]
    assert macro_pool_status(high)["protein_g"] >= 70
