"""Deterministic diet scorer (SC-SCORE-01).

Pure, rule-based, no LLM. Higher score = better-fuelled. Driven by how many
meals were logged and how many of them carry a protein source (either the
explicit `meal.protein` field or a protein keyword in the description).
"""

from backend.intake.schema import IntakeResult, Meal

_PROTEIN_WORDS = {
    "chicken", "beef", "steak", "fish", "salmon", "tuna", "egg", "eggs",
    "tofu", "beans", "lentils", "turkey", "pork", "yogurt", "whey",
    "protein", "shake", "cottage",
}

# Meal-count base score (a logged eating pattern across the day).
_COUNT_SCORE = {0: 10, 1: 45, 2: 70, 3: 88}


def _clamp(n: int) -> int:
    return max(0, min(100, n))


def _has_protein(meal: Meal) -> bool:
    if meal.protein:
        return True
    desc = meal.description.lower()
    return any(w in desc for w in _PROTEIN_WORDS)


def score(intake: IntakeResult) -> dict:
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
