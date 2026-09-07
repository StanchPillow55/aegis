"""Diet scorer. Higher = better fuelled."""

from src.backend.models.intake import IntakeResult, Meal

_PROTEIN_WORDS = {
    "chicken", "beef", "steak", "fish", "salmon", "tuna", "egg", "eggs",
    "tofu", "beans", "lentils", "turkey", "pork", "yogurt", "whey",
    "protein", "shake", "cottage",
}
_COUNT_SCORE = {0: 10, 1: 45, 2: 70, 3: 88}


def _clamp(n: int) -> int:
    return max(0, min(100, n))


def _has_protein(meal: Meal) -> bool:
    if meal.protein_g:
        return True
    desc = meal.description or ""
    return any(w in desc.lower() for w in _PROTEIN_WORDS)


def score_diet(intake: IntakeResult) -> dict:
    meals = intake.meals or []
    n = len(meals)
    count_score = _COUNT_SCORE.get(n, 95 if n >= 4 else 10)
    protein_count = sum(1 for m in meals if _has_protein(m))
    protein_ratio = (protein_count / n) if n else 0.0
    protein_bonus = round(protein_ratio * 10)
    value = _clamp(count_score + protein_bonus)

    return {"score": value, "factors": {"meal_count": n, "protein_meals": protein_count, "protein_bonus": protein_bonus}}
