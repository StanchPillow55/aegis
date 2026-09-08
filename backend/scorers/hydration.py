"""Hydration factor scorer (legacy port — not a top-level product score)."""

from __future__ import annotations

from backend.intake.schema import IntakeResult


def _clamp(n: int) -> int:
    return max(0, min(100, n))


def score_hydration(intake: IntakeResult) -> dict:
    h = intake.hydration
    if h is None:
        return {
            "score": None,
            "factors": {"reported": False},
            "rationale": "Hydration not reported.",
        }

    water_score = 50
    if h.water_oz is not None:
        if h.water_oz >= 80:
            water_score = 95
        elif h.water_oz >= 64:
            water_score = 85
        elif h.water_oz >= 48:
            water_score = 70
        elif h.water_oz >= 32:
            water_score = 50
        else:
            water_score = 30

    alcohol_penalty = 0
    if h.alcohol_drinks is not None:
        alcohol_penalty = min(40, int(h.alcohol_drinks * 15))

    value = _clamp(water_score - alcohol_penalty)
    return {
        "score": value,
        "factors": {
            "reported": True,
            "water_oz": h.water_oz,
            "water_score": water_score,
            "alcohol_drinks": h.alcohol_drinks,
            "alcohol_penalty": alcohol_penalty,
        },
        "rationale": f"Hydration factor {value}/100.",
    }
