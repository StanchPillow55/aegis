"""Computed Goal Graph signals previously stubbed (recovery, pace, body, activity)."""

from __future__ import annotations

import re
from typing import Any

from backend.intake.schema import IntakeResult
from backend.scorers import soreness as soreness_scorer
from backend.scorers.sleep import score as score_sleep


def _clamp(n: int) -> int:
    return max(0, min(100, n))


_PACE_RE = re.compile(
    r"(?:averaged|avg|pace|at)\s*(\d{1,2}):(\d{2})\b|\b(\d{1,2}):(\d{2})\s*(?:/|\sper\s)?\s*(?:mi|mile|km)",
    re.I,
)
_RUN_RE = re.compile(r"\b(run|ran|running|jog|jogging|miles?|km)\b", re.I)
_DIST_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(miles?|mi|km)\b", re.I)


def _blob(intake: IntakeResult, recent_text: str = "") -> str:
    parts = [recent_text or ""]
    wod = getattr(intake, "todays_wod", None)
    if wod is not None:
        parts.append(str(getattr(wod, "raw", "") or ""))
        movs = getattr(wod, "movements", None) or []
        parts.extend(str(m) for m in movs)
    return " ".join(p for p in parts if p)


def score_recovery(intake: IntakeResult, *, recent_text: str = "") -> dict[str, Any]:
    """Blend sleep + soreness into a recovery readiness signal."""
    sleep = score_sleep(intake)
    sore = soreness_scorer.score(intake)
    sleep_score = sleep.get("score")
    sore_score = sore.get("score")
    if sleep_score is None and sore_score is None:
        return {
            "score": None,
            "factors": {"reported": False},
            "rationale": "Recovery not computable — no sleep or soreness data.",
        }
    # Default missing half to neutral 70 so one channel still yields a score
    s = int(sleep_score if sleep_score is not None else 70)
    r = int(sore_score if sore_score is not None else 70)
    value = _clamp(int(round(0.55 * s + 0.45 * r)))
    debt = "sleep debt" in (recent_text or "").lower() or "recover" in (recent_text or "").lower()
    rationale = (
        f"Recovery scored {value}/100 from sleep ({s}) + soreness/recovery ({r})"
        + (" · journal mentions recovery/sleep debt." if debt else ".")
    )
    return {
        "score": value,
        "factors": {
            "sleep_score": sleep_score,
            "soreness_score": sore_score,
            "sleep_debt_language": debt,
        },
        "rationale": rationale,
    }


def score_running_pace(intake: IntakeResult, *, recent_text: str = "") -> dict[str, Any]:
    """Observational pace signal from journal/WOD text (not a race prediction)."""
    text = _blob(intake, recent_text)
    if not text.strip() or not _RUN_RE.search(text):
        return {
            "score": None,
            "factors": {"run_mentioned": False},
            "rationale": "Running pace not reported in this entry.",
        }
    m = _PACE_RE.search(text)
    dist = _DIST_RE.search(text)
    factors: dict[str, Any] = {"run_mentioned": True}
    if dist:
        factors["distance"] = float(dist.group(1))
        factors["distance_unit"] = dist.group(2)
    if not m:
        value = 62
        return {
            "score": value,
            "factors": factors,
            "rationale": (
                f"Running activity logged without numeric pace — observational score {value}/100."
            ),
        }
    mm = int(m.group(1) or m.group(3))
    ss = int(m.group(2) or m.group(4))
    sec = mm * 60 + ss
    factors["pace"] = f"{mm}:{ss:02d}"
    factors["pace_seconds"] = sec
    # Map common easy–moderate paces (~12:00→55, 10:00→72, 8:00→88). Observational only.
    if sec <= 0:
        value = 60
    else:
        # 480s (8:00) → 90, 600s (10:00) → 72, 720s (12:00) → 55
        value = _clamp(int(round(90 - (sec - 480) * 0.15)))
    return {
        "score": value,
        "factors": factors,
        "rationale": (
            f"Running pace {factors['pace']} observed — signal {value}/100 "
            "(non-prescriptive; based on journal text)."
        ),
    }


def score_body_composition(*, metrics: dict[str, Any] | None = None) -> dict[str, Any]:
    """Use latest FITINDEX/manual weight + body-fat when present."""
    metrics = metrics or {}
    weight = metrics.get("weight_kg")
    bf = metrics.get("body_fat_pct")
    if weight is None and bf is None:
        return {
            "score": None,
            "factors": {"reported": False},
            "rationale": "Body composition metrics not yet imported (CSV/OCR/manual).",
        }
    # Availability score: having both metrics is stronger evidence coverage, not "healthier"
    coverage = 50
    if weight is not None:
        coverage += 25
    if bf is not None:
        coverage += 25
    value = _clamp(coverage)
    return {
        "score": value,
        "factors": {
            "weight_kg": weight,
            "body_fat_pct": bf,
            "reported": True,
        },
        "rationale": (
            f"Body composition data present (weight={weight}, bf%={bf}) — "
            f"coverage signal {value}/100 (not a clinical assessment)."
        ),
    }


def score_activity_volume(*, metrics: dict[str, Any] | None = None) -> dict[str, Any]:
    """Steps / active minutes from Takeout/fixture metrics when present."""
    metrics = metrics or {}
    steps = metrics.get("steps")
    active = metrics.get("active_minutes")
    if steps is None and active is None:
        return {
            "score": None,
            "factors": {"reported": False},
            "rationale": "Activity volume metrics not available yet.",
        }
    step_score = None
    if steps is not None:
        s = float(steps)
        if s >= 10000:
            step_score = 95
        elif s >= 7500:
            step_score = 80
        elif s >= 5000:
            step_score = 65
        elif s >= 3000:
            step_score = 50
        else:
            step_score = 35
    active_score = None
    if active is not None:
        a = float(active)
        if a >= 45:
            active_score = 90
        elif a >= 30:
            active_score = 75
        elif a >= 15:
            active_score = 60
        else:
            active_score = 40
    parts = [p for p in (step_score, active_score) if p is not None]
    value = _clamp(int(round(sum(parts) / len(parts))))
    return {
        "score": value,
        "factors": {"steps": steps, "active_minutes": active, "reported": True},
        "rationale": f"Activity volume signal {value}/100 from imported metrics.",
    }
