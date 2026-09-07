"""Structured LLM health-data query tools (no full DB dump)."""

from __future__ import annotations

from typing import Any

from backend.alerts import AlertEngine
from backend.goals import GoalStore
from backend.health.store import HealthMetricsStore
from backend.providers.memory import LocalMemoryProvider
from backend.sync import SourceRegistry


class HealthQueryTools:
    def __init__(
        self,
        metrics: HealthMetricsStore | None = None,
        alerts: AlertEngine | None = None,
        goals: GoalStore | None = None,
        sync: SourceRegistry | None = None,
        memory: LocalMemoryProvider | None = None,
    ) -> None:
        self.metrics = metrics or HealthMetricsStore()
        self.alerts = alerts or AlertEngine(metrics=self.metrics)
        self.goals = goals or GoalStore(metrics=self.metrics)
        self.sync = sync or SourceRegistry()
        self.memory = memory or LocalMemoryProvider()

    def list_metrics(self) -> dict[str, Any]:
        return {"metrics": self.metrics.list_metrics()}

    def latest(self, metric: str) -> dict[str, Any]:
        point = self.metrics.latest(metric)
        if point is None:
            return {"metric": metric, "value": None, "limitation": "No data"}
        return {
            "metric": metric,
            "value": point.value,
            "day": point.day,
            "observed_at": point.observed_at,
            "source": point.provenance.source.value,
            "quality": point.provenance.quality.value,
        }

    def series(self, metric: str, limit: int = 30) -> dict[str, Any]:
        pts = self.metrics.series(metric, limit=limit)
        return {
            "metric": metric,
            "points": [
                {
                    "value": p.value,
                    "day": p.day,
                    "observed_at": p.observed_at,
                    "source": p.provenance.source.value,
                }
                for p in pts
            ],
            "limitation": "Local store only; may be incomplete",
        }

    def compare_baseline(self, metric: str) -> dict[str, Any]:
        pts = self.metrics.series(metric, limit=30)
        if len(pts) < 2:
            return {"metric": metric, "limitation": "Insufficient history for baseline"}
        latest = pts[-1]
        base = sum(p.value for p in pts[:-1]) / (len(pts) - 1)
        delta_pct = ((latest.value - base) / base) * 100 if base else None
        return {
            "metric": metric,
            "latest": latest.value,
            "baseline": round(base, 2),
            "delta_pct": round(delta_pct, 2) if delta_pct is not None else None,
            "source": latest.provenance.source.value,
            "as_of": latest.day or latest.observed_at,
        }

    def summarize_range(self, metric: str) -> dict[str, Any]:
        pts = self.metrics.series(metric, limit=100)
        if not pts:
            return {"metric": metric, "limitation": "No points"}
        vals = [p.value for p in pts]
        return {
            "metric": metric,
            "count": len(vals),
            "min": min(vals),
            "max": max(vals),
            "avg": round(sum(vals) / len(vals), 2),
            "from": pts[0].day,
            "to": pts[-1].day,
            "sources": sorted({p.provenance.source.value for p in pts}),
        }

    def source_freshness(self) -> dict[str, Any]:
        return {
            "sources": [
                {
                    "source_id": s.source_id.value,
                    "enabled": s.enabled,
                    "last_success_at": s.last_success_at,
                    "stale": s.stale,
                    "last_error": s.last_error.model_dump() if s.last_error else None,
                }
                for s in self.sync.list_sources()
            ]
        }

    def active_alerts(self) -> dict[str, Any]:
        self.alerts.evaluate()
        return {"alerts": [a.model_dump() for a in self.alerts.active()]}

    def goal_progress(self) -> dict[str, Any]:
        out = []
        for g in self.goals.list():
            out.append(self.goals.evaluate(g.goal_id))
        return {"goals": out}

    def search_conversations(self, query: str) -> dict[str, Any]:
        # Conversation store not fully built — search intake memory as proxy
        hits = self.memory.search(query, k=5)
        return {
            "query": query,
            "hits": [
                {"log_id": h.log_id, "content": h.content, "timestamp": h.timestamp}
                for h in hits
            ],
            "limitation": "Searches intake memory until chat history store lands",
        }

    def evidence(self, query: str) -> dict[str, Any]:
        hits = self.memory.search(query, k=5, dedupe=True)
        return {
            "history": [
                {
                    "record_id": h.log_id,
                    "content": h.content,
                    "provenance": h.provenance,
                    "score": h.score,
                }
                for h in hits
            ]
        }

    def dispatch(self, tool: str, **kwargs: Any) -> dict[str, Any]:
        mapping = {
            "list_metrics": self.list_metrics,
            "latest": self.latest,
            "series": self.series,
            "compare_baseline": self.compare_baseline,
            "summarize_range": self.summarize_range,
            "source_freshness": self.source_freshness,
            "active_alerts": self.active_alerts,
            "goal_progress": self.goal_progress,
            "search_conversations": self.search_conversations,
            "evidence": self.evidence,
        }
        if tool not in mapping:
            return {"error": f"Unknown tool {tool}", "available": sorted(mapping)}
        fn = mapping[tool]
        return fn(**kwargs) if kwargs else fn()
