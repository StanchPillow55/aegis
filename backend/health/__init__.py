"""Health domain package — schema, provenance, evidence, metrics store."""

from backend.health.evidence import build_evidence_bundle, detect_conflicts
from backend.health.schema import (
    SAFETY_DISCLAIMER,
    SCHEMA_VERSION,
    DataQuality,
    DataSource,
    EvidenceBundle,
    EvidenceConflict,
    HealthRecord,
    HistoryHit,
    Provenance,
)
from backend.health.store import HealthMetricsStore, ManualMetricIn

__all__ = [
    "SAFETY_DISCLAIMER",
    "SCHEMA_VERSION",
    "DataQuality",
    "DataSource",
    "EvidenceBundle",
    "EvidenceConflict",
    "HealthRecord",
    "HealthMetricsStore",
    "HistoryHit",
    "ManualMetricIn",
    "Provenance",
    "build_evidence_bundle",
    "detect_conflicts",
]
