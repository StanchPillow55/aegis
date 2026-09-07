"""Directive composition helpers."""

from __future__ import annotations

from backend.intake.schema import IntakeResult
from backend.scorers import score_all


def compose_directive(
    intake: IntakeResult,
    *,
    context_notes: list[str] | None = None,
) -> dict:
    """Return scores + one plain-language directive string."""
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

    evidence = (
        f"readiness {readiness}/100 (sleep {sleep_s}, soreness {soreness_s}, diet {diet_s})"
    )
    if context_notes:
        evidence += f"; memory hits: {len(context_notes)}"

    directive = (
        f"{action} Focus: "
        f"{'; '.join(focus_bits) if focus_bits else 'consistency over novelty'}. "
        f"Evidence: {evidence}."
    )

    return {
        "directive": directive,
        "scores": scores,
        "evidence": {
            "readiness": readiness,
            "sleep": sleep_s,
            "soreness": soreness_s,
            "diet": diet_s,
            "context": context_notes or [],
        },
    }
