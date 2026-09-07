from enum import Enum
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field
from src.backend.models.health_metrics import MetricType

class GoalStatus(str, Enum):
    active = "active"
    completed = "completed"
    abandoned = "abandoned"
    paused = "paused"

class GoalType(str, Enum):
    metric_target = "metric_target"
    habit = "habit"
    activity = "activity"
    custom = "custom"

class GoalDirection(str, Enum):
    increase = "increase"
    decrease = "decrease"
    maintain = "maintain"

class CompletionConfirmedBy(str, Enum):
    user = "user"
    ai_suggested = "ai_suggested"

class Goal(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    goal_type: GoalType
    metric_type: Optional[MetricType] = None
    target_value: Optional[float] = None
    current_value: Optional[float] = None
    direction: Optional[GoalDirection] = None
    unit: Optional[str] = None
    timeframe_start: Optional[datetime] = None
    timeframe_end: Optional[datetime] = None
    status: GoalStatus = GoalStatus.active
    created_at: datetime
    completed_at: Optional[datetime] = None
    completion_confirmed_by: Optional[CompletionConfirmedBy] = None
    progress_pct: Optional[float] = None
    success_criteria: Optional[str] = None
    notes: Optional[str] = None

class GoalProgress(BaseModel):
    id: str
    goal_id: str
    date: date
    value: float
    note: Optional[str] = None

class CheckInSource(str, Enum):
    auto_detected = "auto_detected"
    user_reported = "user_reported"

class GoalCheckIn(BaseModel):
    id: str
    goal_id: str
    timestamp: datetime
    source: CheckInSource
    message: str
    requires_confirmation: bool = False
