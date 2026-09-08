"""GL5 — Goal Graph LLM tools: read-only vs mutation-preview."""

from __future__ import annotations

from typing import Any, Callable

from backend.goals.graph import (
    GoalGraphStore,
    GraphGoalCreate,
    SuggestionCreate,
    SuggestionDecision,
    SuggestionKind,
)
from backend.goals.progress import build_progress_view, explain_progress, propose_task_from_chart
from backend.health.store import HealthMetricsStore
from backend.providers.memory import LocalMemoryProvider
from backend.sync import SourceRegistry


READ_TOOLS = frozenset(
    {
        "list_goal_tree",
        "goal_progress",
        "task_inbox",
        "tasks_for_goal",
        "search_journal",
        "search_conversations",
        "compare_periods",
        "explain_chart",
        "find_stale_evidence",
    }
)

MUTATE_PREVIEW_TOOLS = frozenset(
    {
        "propose_create_task",
        "propose_create_goal",
        "propose_rewrite_goal",
        "confirm_suggestion",
    }
)


class GoalGraphTools:
    """Tools for screen-aware chat. Mutations never apply silently."""

    def __init__(
        self,
        *,
        graph: GoalGraphStore | None = None,
        metrics: HealthMetricsStore | None = None,
        memory: LocalMemoryProvider | None = None,
        sync: SourceRegistry | None = None,
        chat_store: Any | None = None,
    ) -> None:
        self.graph = graph or GoalGraphStore()
        self.metrics = metrics or HealthMetricsStore()
        self.memory = memory or LocalMemoryProvider()
        self.sync = sync or SourceRegistry()
        self.chat_store = chat_store

    def classify(self, tool: str) -> str:
        if tool in READ_TOOLS:
            return "read"
        if tool in MUTATE_PREVIEW_TOOLS:
            return "mutate_preview"
        raise KeyError(tool)

    def list_tools(self) -> dict[str, Any]:
        return {
            "read": sorted(READ_TOOLS),
            "mutate_preview": sorted(MUTATE_PREVIEW_TOOLS),
            "note": "mutate_preview tools create pending suggestions; confirm_suggestion requires explicit decision.",
        }

    # --- Read ---
    def list_goal_tree(self) -> dict[str, Any]:
        return {"goal_tree": self.graph.goal_tree()}

    def goal_progress(self, goal_id: str | None = None) -> dict[str, Any]:
        goals = self.graph.list_goals()
        if goal_id:
            goals = [g for g in goals if g.id == goal_id]
        return {
            "goals": [
                {
                    "id": g.id,
                    "title": g.title,
                    "metric": g.metric,
                    "target": g.target,
                    "status": g.status.value,
                }
                for g in goals
            ]
        }

    def task_inbox(self) -> dict[str, Any]:
        return {
            "tasks": [t.model_dump() for t in self.graph.tasks_by_view("inbox")]
        }

    def tasks_for_goal(self, goal_id: str) -> dict[str, Any]:
        return {
            "goal_id": goal_id,
            "tasks": [t.model_dump() for t in self.graph.list_tasks(goal_id=goal_id)],
        }

    def search_journal(self, query: str) -> dict[str, Any]:
        hits = self.memory.search(query, k=5, dedupe=True)
        return {
            "query": query,
            "hits": [
                {
                    "log_id": h.log_id,
                    "content": (h.content or "")[:200],
                    "provenance": h.provenance,
                }
                for h in hits
            ],
        }

    def search_conversations(self, query: str) -> dict[str, Any]:
        if self.chat_store is None:
            return {"query": query, "hits": [], "limitation": "chat store not wired"}
        return {
            "query": query,
            "hits": self.chat_store.search(query, limit=8),
            "source": "chat_store",
        }

    def compare_periods(
        self, metric: str, horizon_a: str = "week", horizon_b: str = "month"
    ) -> dict[str, Any]:
        a = build_progress_view(
            metric, horizon=horizon_a, metrics=self.metrics, graph=self.graph, sync=self.sync
        )
        b = build_progress_view(
            metric, horizon=horizon_b, metrics=self.metrics, graph=self.graph, sync=self.sync
        )
        return {
            "metric": metric,
            "period_a": {"horizon": horizon_a, "count": a["chart"]["range"].get("count"), "trend": a["trend"]},
            "period_b": {"horizon": horizon_b, "count": b["chart"]["range"].get("count"), "trend": b["trend"]},
            "kind": "derived_comparison",
        }

    def explain_chart(self, metric: str, horizon: str = "month") -> dict[str, Any]:
        view = build_progress_view(
            metric, horizon=horizon, metrics=self.metrics, graph=self.graph, sync=self.sync
        )
        return explain_progress(view)

    def find_stale_evidence(self) -> dict[str, Any]:
        stale = [s.model_dump() for s in self.sync.list_sources() if s.enabled and s.stale]
        missing_metrics = []
        for g in self.graph.list_goals():
            if g.metric and self.metrics.latest(g.metric) is None:
                missing_metrics.append({"goal_id": g.id, "metric": g.metric})
        return {"stale_sources": stale, "goals_missing_metric": missing_metrics}

    # --- Mutate preview ---
    def propose_create_task(
        self,
        *,
        title: str,
        goal_id: str,
        reason: str = "Proposed via chat tool",
        confirm: bool = False,
    ) -> dict[str, Any]:
        if confirm:
            # Still HITL: create pending suggestion, do not write task directly
            pass
        sug = self.graph.propose_suggestion(
            SuggestionCreate(
                kind=SuggestionKind.CREATE_TASK,
                title=title,
                reason=reason,
                evidence=["tool:propose_create_task"],
                assumptions=["Requires human approval before task exists."],
                confidence="medium",
                affected_goal_id=goal_id,
                payload={"title": title, "description": reason},
            )
        )
        return {
            "mode": "mutate_preview",
            "applied": False,
            "suggestion": sug.model_dump(),
            "detail": "Pending suggestion created — approve in UI or confirm_suggestion.",
        }

    def propose_create_goal(
        self, *, title: str, metric: str | None = None, reason: str = "Proposed via chat"
    ) -> dict[str, Any]:
        sug = self.graph.propose_suggestion(
            SuggestionCreate(
                kind=SuggestionKind.CREATE_GOAL,
                title=title,
                reason=reason,
                evidence=["tool:propose_create_goal"],
                assumptions=["Goal not created until approved."],
                confidence="medium",
                payload={"title": title, "metric": metric},
            )
        )
        return {
            "mode": "mutate_preview",
            "applied": False,
            "suggestion": sug.model_dump(),
        }

    def propose_rewrite_goal(
        self, *, goal_id: str, new_title: str, reason: str = "Rewrite proposed via chat"
    ) -> dict[str, Any]:
        self.graph.get_goal(goal_id)  # ensure exists
        sug = self.graph.propose_suggestion(
            SuggestionCreate(
                kind=SuggestionKind.REWRITE_GOAL,
                title=f"Rewrite: {new_title}",
                reason=reason,
                evidence=["tool:propose_rewrite_goal"],
                assumptions=["Title change requires approval."],
                confidence="medium",
                affected_goal_id=goal_id,
                payload={"title": new_title},
            )
        )
        return {
            "mode": "mutate_preview",
            "applied": False,
            "suggestion": sug.model_dump(),
        }

    def confirm_suggestion(
        self, *, suggestion_id: str, decision: str = "approved", user_confirmed: bool = False
    ) -> dict[str, Any]:
        if not user_confirmed:
            return {
                "mode": "mutate_preview",
                "applied": False,
                "detail": "Set user_confirmed=true after explicit UI confirmation.",
                "suggestion_id": suggestion_id,
            }
        dec = SuggestionDecision(decision)
        after = self.graph.decide_suggestion(suggestion_id, dec)
        return {
            "mode": "mutate_preview",
            "applied": after.decision
            in {SuggestionDecision.APPROVED, SuggestionDecision.EDITED},
            "suggestion": after.model_dump(),
        }

    def propose_task_from_chart(self, metric: str, horizon: str = "month") -> dict[str, Any]:
        out = propose_task_from_chart(graph=self.graph, metric=metric, horizon=horizon)
        out["mode"] = "mutate_preview"
        return out

    def dispatch(self, tool: str, **kwargs: Any) -> dict[str, Any]:
        mode = self.classify(tool)
        fn: Callable[..., dict[str, Any]] = getattr(self, tool)
        # Strip confirm for read tools
        if mode == "read":
            kwargs.pop("confirm", None)
            kwargs.pop("user_confirmed", None)
        result = fn(**kwargs)
        if isinstance(result, dict):
            result.setdefault("tool", tool)
            result.setdefault("mode", mode)
        return result
