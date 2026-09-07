from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from src.backend.models.health_metrics import MetricType

class ThresholdCondition(str, Enum):
    above = "above"
    below = "below"
    delta_above = "delta_above"
    delta_below = "delta_below"

class Severity(str, Enum):
    critical = "critical"
    warning = "warning"
    info = "info"

class SafetyThreshold(BaseModel):
    id: str
    metric_type: MetricType
    condition: ThresholdCondition
    value: float
    window_hours: Optional[int] = None
    severity: Severity
    message: str
    is_system_default: bool = False
    user_modified: bool = False

class Alert(BaseModel):
    id: str
    severity: Severity
    metric_type: MetricType
    current_value: float
    threshold_value: float
    message: str
    timestamp: datetime
    acknowledged: bool = False
