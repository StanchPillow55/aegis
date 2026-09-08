"""Built-in signal providers wrapping canonical scorers + future stubs."""

from __future__ import annotations

from typing import Callable

from backend.intake.schema import IntakeResult
from backend.scorers.canonical import (
    score_front_rack,
    score_overall,
    score_workout_preparation,
)
from backend.scorers.diet import score as score_diet
from backend.scorers.hydration import score_hydration
from backend.scorers.performance import score_performance
from backend.scorers.sleep import score as score_sleep
from backend.signals.protocol import SignalContext, SignalResult


def _keywords(*words: str) -> set[str]:
    return {w.lower() for w in words}


PROVIDER_KEYWORDS: dict[str, set[str]] = {
    "front_rack": _keywords(
        "front-rack", "front rack", "shoulder", "wrist", "mobility", "overhead", "jerk", "clean"
    ),
    "sleep": _keywords("sleep", "slept", "insomnia", "rest", "overnight"),
    "diet": _keywords(
        "diet", "ate", "meal", "protein", "nutrition", "beef", "rice", "food", "calories"
    ),
    "workout_preparation": _keywords(
        "wod", "workout", "train", "training", "squat", "run", "lift", "session"
    ),
    "body_composition": _keywords("body fat", "weight", "bf%", "composition", "fitindex"),
    "running_pace": _keywords("run", "pace", "mile", "km", "conditioning", "jog"),
    "hydration": _keywords("hydrat", "water", "thirst"),
    "recovery": _keywords("recover", "hrv", "sore", "soreness", "fatigue"),
    "activity_volume": _keywords("steps", "active minutes", "walk", "activity"),
}


def _text_blob(ctx: SignalContext) -> str:
    parts: list[str] = [ctx.recent_text or ""]
    for g in ctx.active_goals:
        parts.append(getattr(g, "title", "") or "")
        parts.append(getattr(g, "description", "") or "")
        parts.append(getattr(g, "metric", "") or "")
        parts.append(getattr(g, "original_wording", "") or "")
    for t in ctx.active_tasks:
        parts.append(getattr(t, "title", "") or "")
        parts.append(getattr(t, "description", "") or "")
    intake = ctx.intake
    if intake is not None:
        for meal in getattr(intake, "meals", []) or []:
            if hasattr(meal, "description"):
                parts.append(str(meal.description or ""))
            else:
                parts.append(str(meal))
        try:
            parts.append(str(intake.model_dump()))
        except Exception:
            parts.append(str(intake))
    return " ".join(p for p in parts if p).lower()


def _metric_match(ctx: SignalContext, signal_id: str) -> bool:
    for g in ctx.active_goals:
        metric = (getattr(g, "metric", None) or "").lower()
        if metric and (metric == signal_id or signal_id in metric or metric in signal_id):
            return True
    return False


def _keyword_match(ctx: SignalContext, signal_id: str) -> bool:
    blob = _text_blob(ctx)
    for kw in PROVIDER_KEYWORDS.get(signal_id, ()):
        if kw in blob:
            return True
    return False


class ScorerProvider:
    """Wrap a ``(intake) -> {score, factors, rationale}`` scorer."""

    def __init__(
        self,
        *,
        id: str,
        label: str,
        fn: Callable[[IntakeResult], dict],
        always_core: bool = False,
    ) -> None:
        self.id = id
        self.label = label
        self._fn = fn
        self.always_core = always_core

    def compute(self, ctx: SignalContext) -> SignalResult:
        raw = self._fn(ctx.intake)
        return SignalResult(
            id=self.id,
            label=self.label,
            score=raw.get("score"),
            factors=dict(raw.get("factors") or {}),
            rationale=str(raw.get("rationale") or ""),
            available=raw.get("score") is not None,
        )

    def relevant(self, ctx: SignalContext) -> tuple[bool, str]:
        if self.always_core and not ctx.active_goals:
            return True, "core signal (no active goals)"
        if self.always_core and ctx.view == "directive" and not ctx.active_goals:
            return True, "directive core"
        if _metric_match(ctx, self.id):
            return True, "matches active goal metric"
        if _keyword_match(ctx, self.id):
            return True, "matches goal/task/journal keywords"
        if self.always_core and ctx.include_overall is not False and not ctx.active_goals:
            return True, "default core set"
        # With active goals: core providers still available but not auto-selected
        # unless keyword/metric match — except we keep a minimal always-on set for directive.
        if self.always_core and ctx.view == "directive":
            # Prefer goal-relevant; still include core if nothing else matched later
            return False, "core available; not goal-linked"
        return False, "not linked to active goals/context"


class StubProvider:
    """Future signal with no scorer yet — available=False until data lands."""

    def __init__(self, *, id: str, label: str) -> None:
        self.id = id
        self.label = label
        self.always_core = False

    def compute(self, ctx: SignalContext) -> SignalResult:
        return SignalResult(
            id=self.id,
            label=self.label,
            score=None,
            factors={},
            rationale=f"{self.label} signal not yet computed in this build.",
            available=False,
        )

    def relevant(self, ctx: SignalContext) -> tuple[bool, str]:
        if _metric_match(ctx, self.id) or _keyword_match(ctx, self.id):
            return True, "goal/context mentions signal (provider stub)"
        return False, "not linked"


def default_providers() -> list:
    return [
        ScorerProvider(id="front_rack", label="Front-rack", fn=score_front_rack, always_core=True),
        ScorerProvider(id="sleep", label="Sleep", fn=score_sleep, always_core=True),
        ScorerProvider(id="diet", label="Diet", fn=score_diet, always_core=True),
        ScorerProvider(
            id="workout_preparation",
            label="Workout preparation",
            fn=score_workout_preparation,
            always_core=True,
        ),
        ScorerProvider(id="overall", label="Overall", fn=score_overall, always_core=False),
        ScorerProvider(id="hydration", label="Hydration", fn=score_hydration, always_core=False),
        ScorerProvider(
            id="performance", label="Performance", fn=score_performance, always_core=False
        ),
        StubProvider(id="body_composition", label="Body composition"),
        StubProvider(id="running_pace", label="Running pace"),
        StubProvider(id="recovery", label="Recovery"),
        StubProvider(id="activity_volume", label="Activity volume"),
    ]
