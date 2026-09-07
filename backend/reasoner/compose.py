"""Directive composition helpers."""

from __future__ import annotations

from backend.health.schema import SAFETY_DISCLAIMER, EvidenceBundle
from backend.intake.schema import IntakeResult
from backend.scorers import score_all


def compose_directive(
    intake: IntakeResult,
    *,
    context_notes: list[str] | None = None,
    evidence_bundle: EvidenceBundle | None = None,
) -> dict:
    """Return scores + one plain-language directive string + disclaimer."""
    scores = score_all(intake)
    readiness = scores["readiness"]["score"]
    sleep_s = scores["sleep"]["score"]
    soreness_s = scores["soreness"]["score"]
    diet_s = scores["diet"]["score"]

    if readiness < 45:
        action = (
            "Take a recovery day: easy walk, mobility, and sleep priority. "
            "Skip heavy loading until readiness climbs."
        )
    elif readiness < 65:
        action = (
            "Train, but cap intensity. Keep skill/technique work, reduce volume ~20–30%, "
            "and stop short of failure."
        )
    else:
        action = (
            "Green light for a full session. Hit today's plan with normal intensity, "
            "then note how joints/soreness respond."
        )

    focus_bits: list[str] = []
    if sleep_s < 55:
        focus_bits.append("protect a longer sleep window tonight")
    if soreness_s < 55 and intake.soreness:
        parts = ", ".join(s.body_part for s in intake.soreness[:3])
        focus_bits.append(f"ease load on {parts}")
    if diet_s < 55:
        focus_bits.append("add a clear protein source to your next meal")
    if intake.todays_wod.movements:
        focus_bits.append(
            "planned movements: " + ", ".join(intake.todays_wod.movements[:6])
        )

    hist_n = 0
    conflict_n = 0
    if evidence_bundle is not None:
        hist_n = len(evidence_bundle.history)
        conflict_n = len(evidence_bundle.conflicts)
    elif context_notes:
        hist_n = len(context_notes)

    evidence = (
        f"readiness {readiness}/100 (sleep {sleep_s}, soreness {soreness_s}, diet {diet_s})"
    )
    if hist_n:
        evidence += f"; history hits: {hist_n}"
    if conflict_n:
        evidence += f"; conflicts: {conflict_n} (today wins)"

    directive = (
        f"{action} Focus: "
        f"{'; '.join(focus_bits) if focus_bits else 'consistency over novelty'}. "
        f"Evidence: {evidence}."
    )

    score_evidence = {
        "readiness": readiness,
        "sleep": sleep_s,
        "soreness": soreness_s,
        "diet": diet_s,
        "context": context_notes or [],
        "note": (
            "Top-level readiness/soreness labels are transitional; "
            "canonical scores are front_rack/sleep/diet/workout_preparation/overall."
        ),
    }
    if evidence_bundle is not None:
        score_evidence["today"] = evidence_bundle.today
        score_evidence["history"] = [h.model_dump() for h in evidence_bundle.history]
        score_evidence["conflicts"] = [c.model_dump() for c in evidence_bundle.conflicts]
        score_evidence["resolution_policy"] = evidence_bundle.resolution_policy

    return {
        "directive": directive,
        "disclaimer": SAFETY_DISCLAIMER,
        "scores": scores,
        "evidence": score_evidence,
    }
