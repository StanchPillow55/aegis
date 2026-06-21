"""SC-SCORE-01 — deterministic readiness scorer tests.

Boundary cases (great vs poor sleep, high vs low soreness) assert expected
score ranges AND that every result carries a non-empty rationale + factors.
All scorers are pure and rule-based — no network, no LLM.
"""

import pytest

from backend.intake.schema import IntakeResult, Meal, Sleep, Soreness, WOD
from backend.scorers import (
    score_all,
    score_diet,
    score_readiness,
    score_sleep,
    score_soreness,
)


def make_intake(
    *,
    soreness=None,
    sleep=None,
    meals=None,
    subjective_readiness="moderate",
) -> IntakeResult:
    """Build an IntakeResult with sane defaults, overriding what a test cares about."""
    return IntakeResult(
        soreness=soreness or [],
        sleep=sleep or Sleep(quality="unknown", hours=None),
        meals=meals or [],
        todays_wod=WOD(movements=["cleans", "pull-ups"]),
        subjective_readiness=subjective_readiness,
    )


def assert_well_formed(result: dict):
    assert isinstance(result["score"], int)
    assert 0 <= result["score"] <= 100
    assert isinstance(result["rationale"], str) and result["rationale"].strip()
    assert isinstance(result["factors"], dict) and result["factors"]


# --- Sleep boundaries ---------------------------------------------------------

def test_sleep_great_scores_high():
    result = score_sleep(make_intake(sleep=Sleep(quality="great", hours=8)))
    assert_well_formed(result)
    assert result["score"] >= 85


def test_sleep_poor_scores_low():
    result = score_sleep(make_intake(sleep=Sleep(quality="badly", hours=4)))
    assert_well_formed(result)
    assert result["score"] <= 35


def test_sleep_great_beats_poor():
    great = score_sleep(make_intake(sleep=Sleep(quality="great", hours=8)))["score"]
    poor = score_sleep(make_intake(sleep=Sleep(quality="poor", hours=4)))["score"]
    assert great > poor


# --- Soreness boundaries ------------------------------------------------------

def test_no_soreness_full_recovery():
    result = score_soreness(make_intake(soreness=[]))
    assert_well_formed(result)
    assert result["score"] == 100


def test_high_soreness_scores_low():
    result = score_soreness(
        make_intake(
            soreness=[
                Soreness(body_part="quads", severity=5),
                Soreness(body_part="hamstrings", severity=5),
            ]
        )
    )
    assert_well_formed(result)
    assert result["score"] <= 40


def test_low_beats_high_soreness():
    low = score_soreness(
        make_intake(soreness=[Soreness(body_part="calves", severity=1)])
    )["score"]
    high = score_soreness(
        make_intake(soreness=[Soreness(body_part="back", severity=5)])
    )["score"]
    assert low > high


# --- Diet ---------------------------------------------------------------------

def test_diet_three_protein_meals_beats_none():
    fed = score_diet(
        make_intake(
            meals=[
                Meal(description="eggs and oats"),
                Meal(description="chicken and rice"),
                Meal(description="salmon and potatoes"),
            ]
        )
    )
    fasted = score_diet(make_intake(meals=[]))
    assert_well_formed(fed)
    assert_well_formed(fasted)
    assert fed["score"] >= 85
    assert fasted["score"] <= 20
    assert fed["score"] > fasted["score"]


# --- Readiness (aggregate) ----------------------------------------------------

def test_readiness_good_day_beats_bad_day():
    good = score_readiness(
        make_intake(
            sleep=Sleep(quality="great", hours=8),
            soreness=[],
            meals=[Meal(description="chicken and rice"), Meal(description="eggs")],
            subjective_readiness="high",
        )
    )
    bad = score_readiness(
        make_intake(
            sleep=Sleep(quality="poor", hours=4),
            soreness=[Soreness(body_part="quads", severity=5)],
            meals=[],
            subjective_readiness="low",
        )
    )
    assert_well_formed(good)
    assert_well_formed(bad)
    assert good["score"] >= 80
    assert bad["score"] <= 40
    assert good["score"] > bad["score"]


# --- Aggregate API ------------------------------------------------------------

def test_score_all_returns_four_well_formed_dimensions():
    result = score_all(
        make_intake(
            sleep=Sleep(quality="poor", hours=5),
            soreness=[Soreness(body_part="forearms", severity=3)],
            meals=[Meal(description="chicken and rice")],
            subjective_readiness="low",
        )
    )
    assert set(result) == {"sleep", "diet", "soreness", "readiness"}
    for dimension in result.values():
        assert_well_formed(dimension)
