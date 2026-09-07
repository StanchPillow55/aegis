"""Deterministic diet scorer (SC-SCORE-01) with Macro Pool blend.

Pure, rule-based, no LLM. Meal-pattern base score blended with protein Macro
Pool fill when protein_g is present on meals.
"""

from backend.intake.schema import IntakeResult, Meal

_PROTEIN_WORDS = {
    "chicken", "beef", "steak", "fish", "salmon", "tuna", "egg", "eggs",
    "tofu", "beans", "lentils", "turkey", "pork", "yogurt", "whey",
    "protein", "shake", "cottage",
}

# Meal-count base score (a logged eating pattern across the day).
_COUNT_SCORE = {0: 10, 1: 45, 2: 70, 3: 88}

DEFAULT_PROTEIN_TARGET_G = 140


def _clamp(n: int) -> int:
    return max(0, min(100, n))


def _has_protein(meal: Meal) -> bool:
    if meal.protein_g:
        return True
    desc = meal.description.lower()
    return any(w in desc for w in _PROTEIN_WORDS)


def score_basic(intake: IntakeResult) -> dict:
    """Meal-count + protein-keyword heuristic (no Macro Pool blend)."""
    meals = intake.meals
    n = len(meals)
    count_score = _COUNT_SCORE.get(n, 95 if n >= 4 else 10)

    protein_count = sum(1 for m in meals if _has_protein(m))
    protein_ratio = (protein_count / n) if n else 0.0
    protein_bonus = round(protein_ratio * 10)  # up to +10

    value = _clamp(count_score + protein_bonus)

    factors = {
        "meal_count": n,
        "count_score": count_score,
        "protein_meals": protein_count,
        "protein_ratio": round(protein_ratio, 2),
        "protein_bonus": protein_bonus,
    }
    rationale = (
        f"Diet scored {value}/100: {n} meal(s) logged (base {count_score}), "
        f"{protein_count} with a protein source (+{protein_bonus})."
    )
    return {"score": value, "factors": factors, "rationale": rationale}


def score(intake: IntakeResult, protein_target_g: int = DEFAULT_PROTEIN_TARGET_G) -> dict:
    """Canonical diet score = Macro Pool blend over basic meal pattern."""
    from backend.scorers.macro_pool import macro_pool_status

    basic = score_basic(intake)
    pool = macro_pool_status(intake, protein_target_g=protein_target_g)
    # When no protein grams logged, keep basic meal-pattern score (missing-data-safe)
    has_grams = any(m.protein_g for m in intake.meals)
    if not has_grams:
        return {
            "score": basic["score"],
            "factors": {
                **basic["factors"],
                "macro_pool": pool,
                "blend": "basic_only_missing_protein_g",
            },
            "rationale": basic["rationale"]
            + " Macro Pool not blended (no protein_g on meals).",
        }
    return {
        "score": pool["score"],
        "factors": {
            **basic["factors"],
            "macro_pool": pool,
            "blend": "0.4_basic_0.6_pool",
        },
        "rationale": pool["rationale"],
    }
