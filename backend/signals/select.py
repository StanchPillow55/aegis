"""Signal registry + dynamic selection (GL1)."""

from __future__ import annotations

from typing import Any, Iterable

from backend.intake.schema import IntakeResult
from backend.scorers.canonical import score_canonical
from backend.signals.protocol import SignalContext, SignalResult
from backend.signals.providers import default_providers


class SignalRegistry:
    def __init__(self, providers: Iterable | None = None) -> None:
        self._providers = list(providers or default_providers())
        self._by_id = {p.id: p for p in self._providers}

    def get(self, signal_id: str):
        return self._by_id[signal_id]

    def list_ids(self) -> list[str]:
        return [p.id for p in self._providers]

    def compute_all(self, ctx: SignalContext) -> list[SignalResult]:
        return [p.compute(ctx) for p in self._providers]

    def select(self, ctx: SignalContext) -> list[SignalResult]:
        """Return selected signals for the current context.

        Rules:
        - No active goals → core FR/Sleep/Diet/WP + overall (MVP dashboard contract).
        - Active goals → providers marked relevant; always ensure at least the core
          four if nothing matched; overall only if include_overall or no selections.
        """
        include_overall = ctx.include_overall
        if include_overall is None:
            include_overall = not bool(ctx.active_goals)

        selected: list[SignalResult] = []
        seen: set[str] = set()

        for p in self._providers:
            if p.id == "overall":
                continue
            ok, why = p.relevant(ctx)
            result = p.compute(ctx)
            result.relevance = why
            if ok:
                result.selected = True
                selected.append(result)
                seen.add(p.id)

        if not ctx.active_goals:
            # MVP default set
            for sid in ("front_rack", "sleep", "diet", "workout_preparation"):
                if sid not in seen:
                    p = self._by_id[sid]
                    r = p.compute(ctx)
                    r.selected = True
                    r.relevance = "default core set (no active goals)"
                    selected.append(r)
                    seen.add(sid)
            include_overall = True if ctx.include_overall is None else include_overall

        if not selected:
            # Fallback: always show core four
            for sid in ("front_rack", "sleep", "diet", "workout_preparation"):
                p = self._by_id[sid]
                r = p.compute(ctx)
                r.selected = True
                r.relevance = "fallback core set"
                selected.append(r)
                seen.add(sid)

        if include_overall and "overall" in self._by_id:
            r = self._by_id["overall"].compute(ctx)
            r.selected = True
            r.relevance = "optional overall summary"
            selected.append(r)

        # Stable-ish order: core first, then others, overall last
        order = {
            "front_rack": 0,
            "sleep": 1,
            "diet": 2,
            "workout_preparation": 3,
            "overall": 100,
        }
        selected.sort(key=lambda s: (order.get(s.id, 50), s.id))
        return selected


_REGISTRY = SignalRegistry()


def get_registry() -> SignalRegistry:
    return _REGISTRY


def build_context(
    intake: IntakeResult,
    *,
    goal_store: Any | None = None,
    recent_text: str = "",
    view: str = "directive",
    include_overall: bool | None = None,
) -> SignalContext:
    active_goals: list[Any] = []
    active_tasks: list[Any] = []
    if goal_store is not None:
        try:
            from backend.goals.graph import GraphGoalStatus, TaskStatus

            active_goals = [
                g
                for g in goal_store.list_goals()
                if getattr(g, "status", None) == GraphGoalStatus.IN_PROGRESS
            ]
            active_tasks = [
                t
                for t in goal_store.list_tasks()
                if getattr(t, "status", None)
                not in {TaskStatus.COMPLETED, TaskStatus.CANCELED, TaskStatus.SKIPPED}
            ]
        except Exception:
            active_goals = []
            active_tasks = []
    return SignalContext(
        intake=intake,
        active_goals=active_goals,
        active_tasks=active_tasks,
        recent_text=recent_text,
        view=view,
        include_overall=include_overall,
    )


def select_signals(ctx: SignalContext, registry: SignalRegistry | None = None) -> list[SignalResult]:
    reg = registry or get_registry()
    return reg.select(ctx)


def signals_payload(ctx: SignalContext, registry: SignalRegistry | None = None) -> dict[str, Any]:
    reg = registry or get_registry()
    selected = reg.select(ctx)
    available = reg.compute_all(ctx)
    return {
        "selected": [
            {
                "id": s.id,
                "label": s.label,
                "score": s.score,
                "available": s.available,
                "relevance": s.relevance,
                "rationale": s.rationale,
                "factors": s.factors,
            }
            for s in selected
        ],
        "available_ids": [s.id for s in available],
        "overall_optional": not any(s.id == "overall" and s.selected for s in selected)
        or bool(ctx.active_goals),
        "compat_scores": score_canonical(ctx.intake),
    }
