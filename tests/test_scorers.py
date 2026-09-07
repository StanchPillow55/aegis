"""Test deterministic scorers."""

from src.backend.models.intake import IntakeResult, Sleep, Soreness, Meal, Hydration, PerformanceLog
from src.backend.scorers import score_all


def _make_intake(**kwargs) -> IntakeResult:
    defaults = {"sleep": Sleep(quality="good", hours=8)}
    defaults.update(kwargs)
    return IntakeResult(**defaults)


def test_perfect_sleep():
    intake = _make_intake(sleep=Sleep(quality="great", hours=8))
    result = score_all(intake)
    assert result["sleep"]["score"] >= 85


def test_poor_sleep():
    intake = _make_intake(sleep=Sleep(quality="terrible", hours=4))
    result = score_all(intake)
    assert result["sleep"]["score"] <= 30


def test_no_soreness_is_100():
    intake = _make_intake()
    result = score_all(intake)
    assert result["soreness"]["score"] == 100


def test_severe_soreness():
    intake = _make_intake(soreness=[Soreness(body_part="back", severity=5)])
    result = score_all(intake)
    assert result["soreness"]["score"] <= 50


def test_hydration_good():
    intake = _make_intake(hydration=Hydration(water_oz=80, alcohol_drinks=0))
    result = score_all(intake)
    assert result["hydration"]["score"] >= 80


def test_hydration_with_alcohol():
    intake = _make_intake(hydration=Hydration(water_oz=60, alcohol_drinks=3))
    result = score_all(intake)
    assert result["hydration"]["score"] < 60


def test_performance_good_feel():
    intake = _make_intake(performance=PerformanceLog(feel="strong", rx=True, hr_max=175, rpe=7))
    result = score_all(intake)
    assert result["performance"]["score"] >= 75


def test_readiness_composite():
    intake = _make_intake(
        sleep=Sleep(quality="good", hours=8),
        soreness=[],
        meals=[Meal(description="chicken", protein_g=30)],
        hydration=Hydration(water_oz=80),
    )
    result = score_all(intake)
    assert 60 <= result["readiness"]["score"] <= 100
