"""Core data models for aegis.

These are the authoritative shapes for the entire system. Everything builds
against these: extraction, scoring, storage, API responses, and the frontend.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ReadinessLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class WorkoutType(str, Enum):
    AMRAP = "amrap"
    FOR_TIME = "for_time"
    EMOM = "emom"
    STRENGTH = "strength"
    CHIPPER = "chipper"
    INTERVAL = "interval"
    OTHER = "other"


class Soreness(BaseModel):
    body_part: Optional[str] = Field(None, description="Body part, e.g. 'forearms', 'lower back'.")
    severity: Optional[int] = Field(None, ge=1, le=5, description="1 (barely sore) to 5 (severe).")
    notes: Optional[str] = Field(None, description="Additional context.")


class Sleep(BaseModel):
    quality: Optional[str] = Field(None, description="Subjective quality: 'good', 'poor', etc.")
    hours: Optional[float] = Field(None, description="Hours slept.")
    notes: Optional[str] = None


class Meal(BaseModel):
    description: Optional[str] = Field(None, description="What was eaten.")
    protein_g: Optional[int] = Field(None, description="Protein in grams.")
    calories: Optional[int] = None
    timing: Optional[str] = Field(None, description="'breakfast', 'post-workout', etc.")


class Hydration(BaseModel):
    water_oz: Optional[float] = Field(None, description="Ounces of water.")
    alcohol_drinks: Optional[int] = Field(None, description="Number of alcoholic drinks.")
    notes: Optional[str] = None


class WOD(BaseModel):
    workout_type: Optional[WorkoutType] = None
    movements: list[str] = Field(default_factory=list)
    prescribed_weight: Optional[str] = None
    time_cap: Optional[int] = Field(None, description="Time cap in minutes.")
    rounds: Optional[int] = None
    raw: Optional[str] = Field(None, description="Raw WOD text.")


class RoundSplit(BaseModel):
    round_number: int
    time_seconds: Optional[float] = None
    reps_completed: Optional[int] = None
    notes: Optional[str] = None


class PerformanceLog(BaseModel):
    total_time_seconds: Optional[float] = None
    total_rounds: Optional[int] = None
    total_reps: Optional[int] = None
    rx: Optional[bool] = None
    scaled_notes: Optional[str] = None
    hr_avg: Optional[int] = None
    hr_max: Optional[int] = None
    rpe: Optional[int] = Field(None, ge=1, le=10)
    splits: list[RoundSplit] = Field(default_factory=list)
    rep_breakdown: Optional[str] = None
    feel: Optional[str] = None
    notes: Optional[str] = None


class IntakeResult(BaseModel):
    """Full structured result of parsing one daily update."""
    soreness: Optional[list[Soreness]] = Field(default_factory=list)
    sleep: Optional[Sleep] = None
    meals: Optional[list[Meal]] = Field(default_factory=list)
    hydration: Optional[Hydration] = None
    todays_wod: Optional[WOD] = None
    performance: Optional[PerformanceLog] = None
    subjective_readiness: Optional[str] = None
    notes: Optional[str] = None


class ScoreSet(BaseModel):
    sleep: int = Field(..., ge=0, le=100)
    soreness: int = Field(..., ge=0, le=100)
    diet: int = Field(..., ge=0, le=100)
    hydration: int = Field(..., ge=0, le=100)
    performance: Optional[int] = Field(None, ge=0, le=100)
    readiness: int = Field(..., ge=0, le=100)


class DailyLog(BaseModel):
    """A complete persisted daily log."""
    id: str
    date: date
    created_at: datetime
    updated_at: Optional[datetime] = None
    raw_input: Optional[str] = None
    intake: IntakeResult
    scores: Optional[ScoreSet] = None
    summary_text: Optional[str] = None
