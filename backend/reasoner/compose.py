"""Directive composition helpers."""

from __future__ import annotations

from backend.health.schema import SAFETY_DISCLAIMER, EvidenceBundle
from backend.intake.schema import IntakeResult
from backend.reasoner.wod import negotiate_wod
from backend.scorers.canonical import score_canonical


def compose_directive(
    intake: IntakeResult,
    *,
    context_notes: list[str] | None = None,
    evidence_bundle: EvidenceBundle | None = None,
) -> dict:
    """Return canonical scores + WOD decision + directive + disclaimer."""
    scores = score_canonical(intake)
    wod_decision = negotiate_wod(intake)

    fr = scores["front_rack"]["score"]
    sleep_s = scores["sleep"]["score"]
    diet_s = scores["diet"]["score"]
    wp = scores["workout_preparation"]["score"]
    overall = scores["overall"]["score"]

    status = wod_decision["status"]
    if status == "deferred":
        action = (
            "Defer today's loaded work. Prioritize sleep, nutrition, and easy movement."
        )
    elif status == "substituted":
        action = (
            "Train with substitutions that spare front-rack positions. "
            "Keep quality high on the revised plan."
        )
    elif status == "scaled":
        action = (
            "Train, but scale volume ~20–30% and stop short of failure."
        )
    else:
        action = (
            "Green light for the prescribed session. Note how joints respond afterward."
        )

    focus_bits: list[str] = []
    if sleep_s < 55:
        focus_bits.append("protect a longer sleep window tonight")
    if fr < 55:
        focus_bits.append("front-rack mobility primer before loading")
    if diet_s < 55:
        focus_bits.append("add a clear protein source to your next meal")
    if intake.todays_wod.movements:
        focus_bits.append("WOD decision: " + status)

    hist_n = len(evidence_bundle.history) if evidence_bundle else len(context_notes or [])
    conflict_n = len(evidence_bundle.conflicts) if evidence_bundle else 0
    evidence = (
        f"overall {overall}/100 (front-rack {fr}, sleep {sleep_s}, diet {diet_s}, "
        f"workout-prep {wp}); wod={status}"
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
        "front_rack": fr,
        "sleep": sleep_s,
        "diet": diet_s,
        "workout_preparation": wp,
        "overall": overall,
        "wod_status": status,
        "context": context_notes or [],
        # Keep transitional numbers for compatibility/debugging
        "transitional": {
            "readiness": scores["transitional"]["readiness"]["score"],
            "soreness": scores["transitional"]["soreness"]["score"],
        },
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
        "wod_decision": wod_decision,
        "evidence": score_evidence,
    }
