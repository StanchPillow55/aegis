"""Canonical health record + provenance + evidence bundle (Slice 0).

IntakeResult remains the daily NL-parse contract. HealthRecord wraps any
stored observation (intake log today; future Fitbit/FITINDEX rows later) with
required provenance so evidence can cite source, time, and quality.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from backend.intake.schema import IntakeResult


SCHEMA_VERSION = 1

SAFETY_DISCLAIMER = (
    "Aegis provides non-medical training decision support only. "
    "It does not diagnose conditions or prescribe treatment. "
    "Stop if you feel pain (vs normal training soreness) and consult a "
    "qualified professional for injury or health concerns. "
    "Alerts and scores are observations based on available data, which may be incomplete or stale."
)


class DataSource(str, Enum):
    MANUAL_TEXT = "manual_text"
    HEURISTIC_EXTRACT = "heuristic_extract"
    OLLAMA_EXTRACT = "ollama_extract"
    FIXTURE = "fixture"
    # Reserved for later connectors (not implemented in Slice 0):
    FITBIT = "fitbit"
    FITINDEX = "fitindex"
    CALENDAR = "calendar"
    TAKEOUT = "takeout"
    WEATHER = "weather"


class DataQuality(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class Provenance(BaseModel):
    """Required metadata on every persisted health record."""

    source: DataSource = DataSource.MANUAL_TEXT
    recorded_at: float = Field(..., description="Epoch seconds when stored locally")
    observed_at: float | None = Field(
        None, description="Epoch seconds when the underlying event occurred, if known"
    )
    quality: DataQuality = DataQuality.UNKNOWN
    extractor: str | None = Field(
        None, description="e.g. heuristic|ollama|manual"
    )
    notes: str | None = None
    schema_version: int = SCHEMA_VERSION


class HealthRecord(BaseModel):
    """Persisted unit of health evidence (intake log in Slice 0)."""

    record_id: str
    kind: str = Field("intake_log", description="Record type discriminator")
    content: str
    intake: IntakeResult | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance
    content_hash: str = Field(..., description="Hash of normalized content for dedup")


class EvidenceConflict(BaseModel):
    field: str
    today: Any
    history: Any
    history_record_id: str | None = None
    resolution: str = "today_wins"


class HistoryHit(BaseModel):
    record_id: str
    timestamp: float
    content: str
    score: float
    intake: dict[str, Any] | None = None
    provenance: Provenance | None = None
    content_hash: str | None = None


class EvidenceBundle(BaseModel):
    """Structured evidence for directive / chat — today is authoritative."""

    today: dict[str, Any]
    history: list[HistoryHit] = Field(default_factory=list)
    conflicts: list[EvidenceConflict] = Field(default_factory=list)
    disclaimer: str = SAFETY_DISCLAIMER
    resolution_policy: str = "today_wins"
