"""Directive composition helpers."""

from __future__ import annotations

from typing import Any

from backend.health.schema import SAFETY_DISCLAIMER, EvidenceBundle
from backend.intake.schema import IntakeResult
from backend.reasoner.wod import negotiate_wod
from backend.scorers.canonical import score_canonical
from backend.signals import build_context, select_signals


def compose_directive(
    intake: IntakeResult,
    *,
    context_notes: list[str] | None = None,
    evidence_bundle: EvidenceBundle | None = None,
    goal_store: Any | None = None,
    recent_text: str = "",
) -> dict:
    """Return canonical scores + goal-relevant signals + WOD + directive + disclaimer."""
    scores = score_canonical(intake)
    wod_decision = negotiate_wod(intake)

    fr = scores["front_rack"]["score"]
    sleep_s = scores["sleep"]["score"]
    diet_s = scores["diet"]["score"]
    wp = scores["workout_preparation"]["score"]
    overall = scores["overall"]["score"]

    sig_ctx = build_context(
        intake,
        goal_store=goal_store,
        recent_text=recent_text,
        view="directive",
    )
    selected = select_signals(sig_ctx)
    signals = {
        "selected": [
            {
                "id": s.id,
                "label": s.label,
                "score": s.score,
                "available": s.available,
                "relevance": s.relevance,
                "rationale": s.rationale,
            }
            for s in selected
        ],
        "overall_optional": bool(sig_ctx.active_goals)
        and not any(s.id == "overall" for s in selected),
    }

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
    selected_scores = {s.id: s.score for s in selected if s.score is not None}
    if selected_scores.get("sleep", sleep_s) < 55:
        focus_bits.append("protect a longer sleep window tonight")
    if selected_scores.get("front_rack", fr) < 55:
        focus_bits.append("front-rack mobility primer before loading")
    if selected_scores.get("diet", diet_s) < 55:
        focus_bits.append("add a clear protein source to your next meal")
    if intake.todays_wod.movements:
        focus_bits.append("WOD decision: " + status)

    hist_n = len(evidence_bundle.history) if evidence_bundle else len(context_notes or [])
    conflict_n = len(evidence_bundle.conflicts) if evidence_bundle else 0
    signal_bits = ", ".join(
        f"{s.id}={s.score if s.score is not None else 'n/a'}" for s in selected[:6]
    )
    evidence = (
        f"signals [{signal_bits}]; "
        f"compat overall {overall}/100 (front-rack {fr}, sleep {sleep_s}, diet {diet_s}, "
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
        "signals_selected": [s.id for s in selected],
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
        "signals": signals,
        "wod_decision": wod_decision,
        "evidence": score_evidence,
    }
