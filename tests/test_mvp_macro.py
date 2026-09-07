"""MVP-MACRO-01 — Macro Pool ledger (simple daily protein target)."""

from __future__ import annotations

from backend.intake.schema import IntakeResult, Meal
from backend.scorers.diet import score as score_diet
from backend.scorers.macro_pool import macro_pool_status


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
    # Canonical diet score blends Macro Pool when protein_g present
    assert score_diet(high)["score"] == macro_pool_status(high)["score"]
    assert score_diet(high)["factors"]["blend"] == "0.4_basic_0.6_pool"
    assert score_diet(low)["factors"]["blend"] == "basic_only_missing_protein_g"


def test_macro_pool_in_canonical_scores():
    from backend.scorers.canonical import score_canonical

    intake = IntakeResult.model_validate(
        {
            "soreness": [],
            "sleep": {"quality": "good", "hours": 8},
            "meals": [Meal(description="chicken", protein_g=50)],
            "todays_wod": {"movements": [], "raw": None},
            "subjective_readiness": "high",
        }
    )
    scores = score_canonical(intake)
    assert "macro_pool" in scores
    assert scores["macro_pool"]["protein_g"] == 50
    assert "macro_pool" in scores["diet"]["factors"]
