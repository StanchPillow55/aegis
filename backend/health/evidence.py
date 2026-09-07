"""Evidence assembly: today vs history, conflicts, dedup helpers."""

from __future__ import annotations

from typing import Any

from backend.health.schema import (
    SAFETY_DISCLAIMER,
    EvidenceBundle,
    EvidenceConflict,
    HistoryHit,
    Provenance,
)
from backend.intake.schema import IntakeResult


def intake_as_today(intake: IntakeResult, *, log_id: str, extractor: str | None = None) -> dict[str, Any]:
    return {
        "log_id": log_id,
        "intake": intake.model_dump(),
        "extractor": extractor,
        "authoritative": True,
    }


def detect_conflicts(
    today: IntakeResult,
    history_hits: list[HistoryHit],
) -> list[EvidenceConflict]:
    """Flag simple field conflicts between today and nearest history intakes."""
    conflicts: list[EvidenceConflict] = []
    for hit in history_hits:
        if not hit.intake:
            continue
        hist_sleep = hit.intake.get("sleep") or {}
        # Sleep hours
        today_hours = today.sleep.hours
        hist_hours = hist_sleep.get("hours")
        if (
            today_hours is not None
            and hist_hours is not None
            and float(today_hours) != float(hist_hours)
        ):
            conflicts.append(
                EvidenceConflict(
                    field="sleep.hours",
                    today=today_hours,
                    history=hist_hours,
                    history_record_id=hit.record_id,
                    resolution="today_wins",
                )
            )
        today_quality = (today.sleep.quality or "").lower().strip()
        hist_quality = str(hist_sleep.get("quality") or "").lower().strip()
        if today_quality and hist_quality and today_quality != hist_quality:
            conflicts.append(
                EvidenceConflict(
                    field="sleep.quality",
                    today=today.sleep.quality,
                    history=hist_sleep.get("quality"),
                    history_record_id=hit.record_id,
                    resolution="today_wins",
                )
            )
        today_ready = (today.subjective_readiness or "").lower().strip()
        hist_ready = str(hit.intake.get("subjective_readiness") or "").lower().strip()
        if today_ready and hist_ready and today_ready != hist_ready:
            conflicts.append(
                EvidenceConflict(
                    field="subjective_readiness",
                    today=today.subjective_readiness,
                    history=hit.intake.get("subjective_readiness"),
                    history_record_id=hit.record_id,
                    resolution="today_wins",
                )
            )
    # Dedup identical conflict fields keeping first history id
    seen: set[str] = set()
    unique: list[EvidenceConflict] = []
    for c in conflicts:
        key = f"{c.field}:{c.today}:{c.history}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(c)
    return unique


def build_evidence_bundle(
    *,
    intake: IntakeResult,
    log_id: str,
    history: list[HistoryHit],
    extractor: str | None = None,
) -> EvidenceBundle:
    return EvidenceBundle(
        today=intake_as_today(intake, log_id=log_id, extractor=extractor),
        history=history,
        conflicts=detect_conflicts(intake, history),
        disclaimer=SAFETY_DISCLAIMER,
        resolution_policy="today_wins",
    )


def provenance_to_dict(p: Provenance | None) -> dict[str, Any] | None:
    return p.model_dump() if p is not None else None
