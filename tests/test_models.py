"""Test that core models validate correctly."""

from datetime import date, datetime

from src.backend.models.intake import (
    DailyLog, IntakeResult, Meal, Sleep, Soreness, WOD,
    PerformanceLog, Hydration, ScoreSet, WorkoutType,
)


def test_minimal_intake():
    """Minimum valid intake: just sleep."""
    intake = IntakeResult(sleep=Sleep(quality="good"))
    assert intake.sleep.quality == "good"
    assert intake.soreness == []
    assert intake.meals == []


def test_full_intake():
    """Fully populated intake."""
    intake = IntakeResult(
        sleep=Sleep(quality="good", hours=7.5),
        soreness=[Soreness(body_part="quads", severity=2)],
        meals=[Meal(description="chicken and rice", protein_g=40)],
        hydration=Hydration(water_oz=80, alcohol_drinks=1),
        todays_wod=WOD(
            workout_type=WorkoutType.FOR_TIME,
            movements=["thrusters", "pull-ups"],
            raw="Fran: 21-15-9 thrusters and pull-ups",
        ),
        performance=PerformanceLog(
            total_time_seconds=522,
            rx=True,
            hr_max=182,
            hr_avg=168,
            rpe=8,
            feel="strong",
        ),
        subjective_readiness="high",
    )
    assert intake.performance.total_time_seconds == 522
    assert intake.todays_wod.workout_type == WorkoutType.FOR_TIME


def test_daily_log():
    """DailyLog wraps intake + scores."""
    intake = IntakeResult(sleep=Sleep(quality="good", hours=8))
    scores = ScoreSet(sleep=90, soreness=100, diet=70, hydration=85, readiness=82)
    log = DailyLog(
        id="2025-01-15-abc123",
        date=date(2025, 1, 15),
        created_at=datetime(2025, 1, 15, 8, 0),
        intake=intake,
        scores=scores,
    )
    assert log.scores.readiness == 82
