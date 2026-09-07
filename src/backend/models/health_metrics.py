from enum import Enum
from datetime import datetime, date
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class MetricType(str, Enum):
    heart_rate = "heart_rate"
    resting_heart_rate = "resting_heart_rate"
    hrv = "hrv"
    spo2 = "spo2"
    steps = "steps"
    distance = "distance"
    calories = "calories"
    active_minutes = "active_minutes"
    sleep_duration = "sleep_duration"
    sleep_stages = "sleep_stages"
    stress_score = "stress_score"
    breathing_rate = "breathing_rate"
    weight = "weight"
    body_fat_pct = "body_fat_pct"
    muscle_mass = "muscle_mass"
    bone_mass = "bone_mass"
    bmi = "bmi"
    visceral_fat = "visceral_fat"
    body_water_pct = "body_water_pct"
    metabolic_age = "metabolic_age"
    environment = "environment"

class DataSource(str, Enum):
    fitbit = "fitbit"
    fitindex = "fitindex"
    calendar = "calendar"
    manual = "manual"
    environment = "environment"
    google_health = "google_health"

class HealthMetric(BaseModel):
    id: str
    timestamp: datetime
    metric_type: MetricType
    value: float
    unit: str
    source: DataSource
    metadata: Dict[str, Any] = Field(default_factory=dict)

class BodyComposition(BaseModel):
    id: str
    date: date
    weight: float = Field(..., ge=50, le=500)
    body_fat_pct: Optional[float] = Field(None, ge=3, le=60)
    muscle_mass_pct: Optional[float] = Field(None, ge=20, le=60)
    bone_mass: Optional[float] = Field(None, ge=1, le=20)
    bmi: Optional[float] = Field(None, ge=10, le=50)
    visceral_fat: Optional[float] = None
    body_water_pct: Optional[float] = None
    metabolic_age: Optional[int] = None
    source: DataSource

class CalendarEvent(BaseModel):
    id: str
    start_time: datetime
    end_time: datetime
    title: str
    location: Optional[str] = None
    description: Optional[str] = None
    all_day: bool = False
    derived_signals: Dict[str, Any] = Field(default_factory=dict)

class SyncStatus(BaseModel):
    source: DataSource
    last_sync_at: Optional[datetime] = None
    next_sync_at: Optional[datetime] = None
    enabled: bool = True
    error_count: int = 0
    last_error: Optional[str] = None
