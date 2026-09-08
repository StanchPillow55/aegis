"""Performance factor scorer (legacy port — not a top-level product score)."""

from __future__ import annotations

from backend.intake.schema import IntakeResult


def _clamp(n: int) -> int:
    return max(0, min(100, n))


_FEEL_POSITIVE = {"strong", "great", "good", "fast", "sharp", "solid", "smooth"}
_FEEL_NEUTRAL = {"ok", "okay", "decent", "average", "fine"}
_FEEL_NEGATIVE = {"bad", "sluggish", "gassed", "weak", "awful", "terrible", "slow", "heavy"}


def score_performance(intake: IntakeResult) -> dict:
    perf = intake.performance
    if perf is None:
        return {
            "score": None,
            "factors": {"logged": False},
            "rationale": "Performance not logged.",
        }

    components: list[int] = []
    if perf.rpe is not None:
        if perf.rpe <= 7:
            components.append(90)
        elif perf.rpe <= 8:
            components.append(75)
        elif perf.rpe <= 9:
            components.append(55)
        else:
            components.append(35)
    if perf.rx is True:
        components.append(90)
    elif perf.rx is False:
        components.append(60)
    if perf.feel:
        feel_lower = perf.feel.lower()
        if any(w in feel_lower for w in _FEEL_POSITIVE):
            components.append(90)
        elif any(w in feel_lower for w in _FEEL_NEGATIVE):
            components.append(30)
        elif any(w in feel_lower for w in _FEEL_NEUTRAL):
            components.append(60)
    if perf.hr_max is not None:
        if 160 <= perf.hr_max <= 185:
            components.append(85)
        elif perf.hr_max > 185:
            components.append(60)
        else:
            components.append(70)

    if not components:
        return {
            "score": 50,
            "factors": {"logged": True, "insufficient_data": True},
            "rationale": "Performance logged but insufficient fields.",
        }

    value = _clamp(round(sum(components) / len(components)))
    return {
        "score": value,
        "factors": {"logged": True, "components": components},
        "rationale": f"Performance factor {value}/100.",
    }
