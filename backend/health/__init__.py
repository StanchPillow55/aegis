"""Health domain package — schema, provenance, evidence (Slice 0)."""

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

__all__ = [
    "SAFETY_DISCLAIMER",
    "SCHEMA_VERSION",
    "DataQuality",
    "DataSource",
    "EvidenceBundle",
    "EvidenceConflict",
    "HealthRecord",
    "HistoryHit",
    "Provenance",
    "build_evidence_bundle",
    "detect_conflicts",
]
