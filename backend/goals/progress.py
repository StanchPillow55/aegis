"""GL4 — long-term progress workspace helpers (horizons, explain, chart→task)."""

from __future__ import annotations

import time
from typing import Any, Literal

from backend.charts import ChartSeries, ChartSpec
from backend.goals import GoalStore
from backend.goals.graph import (
    GoalGraphStore,
    SuggestionCreate,
    SuggestionKind,
    TaskType,
)
from backend.health.store import HealthMetricsStore
from backend.sync import SourceRegistry

Horizon = Literal["today", "week", "month", "year", "all"]

HORIZON_SECONDS: dict[str, float | None] = {
    "today": 24 * 3600,
    "week": 7 * 24 * 3600,
    "month": 30 * 24 * 3600,
    "year": 365 * 24 * 3600,
    "all": None,
}


def horizon_window(horizon: str, *, now: float | None = None) -> tuple[float | None, float]:
    end = now if now is not None else time.time()
    key = (horizon or "month").lower()
    if key not in HORIZON_SECONDS:
        raise ValueError(f"Unknown horizon: {horizon}")
    span = HORIZON_SECONDS[key]
    start = None if span is None else end - span
    return start, end


def _graph_bands(graph: GoalGraphStore | None, metric: str) -> list[dict[str, Any]]:
    if graph is None:
        return []
    bands = []
    for g in graph.list_goals():
        if g.metric != metric or g.target is None:
            continue
        bands.append(
            {
                "goal_id": g.id,
                "metric": g.metric,
                "target": g.target,
                "direction": g.direction.value if g.direction else None,
                "status": g.status.value,
                "title": g.title,
            }
        )
    return bands


def _milestones(graph: GoalGraphStore | None, metric: str) -> list[dict[str, Any]]:
    if graph is None:
        return []
    goal_ids = {g.id for g in graph.list_goals() if g.metric == metric}
    out: list[dict[str, Any]] = []
    for t in graph.list_tasks():
        if t.goal_id not in goal_ids:
            continue
        if t.task_type != TaskType.MILESTONE and "milestone" not in t.title.lower():
            continue
        out.append(
            {
                "task_id": t.id,
                "goal_id": t.goal_id,
                "title": t.title,
                "status": t.status.value,
                "due_date": t.due_date,
            }
        )
    return out


def _stale_sources(sync: SourceRegistry | None) -> list[dict[str, Any]]:
    if sync is None:
        return []
    stale = []
    for s in sync.list_sources():
        d = s.model_dump() if hasattr(s, "model_dump") else dict(s)
        if d.get("stale") or (d.get("enabled") and not d.get("last_success_at")):
            stale.append(
                {
                    "source_id": d.get("source_id"),
                    "stale": bool(d.get("stale")),
                    "detail": d.get("detail") or d.get("integration_state"),
                }
            )
    return stale


def build_progress_view(
    metric: str,
    *,
    horizon: str = "month",
    metrics: HealthMetricsStore | None = None,
    goals: GoalStore | None = None,
    graph: GoalGraphStore | None = None,
    sync: SourceRegistry | None = None,
) -> dict[str, Any]:
    store = metrics or HealthMetricsStore()
    gstore = goals or GoalStore(metrics=store)
    start, end = horizon_window(horizon)
    pts = store.series(metric, start=start, end=end, limit=500)
    series_points = [
        {
            "x": p.day or p.observed_at,
            "y": p.value,
            "source": p.provenance.source.value,
            "quality": p.provenance.quality.value,
            "timestamp": p.observed_at,
        }
        for p in pts
    ]
    # Compat metric-target bands + graph goal bands
    bands = [b for b in gstore.chart_bands() if b["metric"] == metric]
    bands.extend(_graph_bands(graph, metric))

    missing: list[str] = []
    if not pts:
        missing.append(metric)

    sources_seen = sorted({p["source"] for p in series_points})
    qualities = sorted({p["quality"] for p in series_points})
    provenance = [
        {
            "kind": "observed",
            "sources": sources_seen,
            "qualities": qualities,
            "point_count": len(series_points),
        }
    ]

    chart = ChartSpec(
        type="metric_trend",
        title=f"{metric} · {horizon}",
        metric=metric,
        series=[ChartSeries(label=metric, points=series_points)],
        range={
            "horizon": horizon,
            "start": start,
            "end": end,
            "count": len(series_points),
        },
        goal_bands=bands,
        missing=missing,
        source_note="Local SQLite; bands from goals when target/metric match",
    )

    trend = "flat"
    if len(series_points) >= 2:
        delta = series_points[-1]["y"] - series_points[0]["y"]
        if delta > 0:
            trend = "up"
        elif delta < 0:
            trend = "down"

    return {
        "metric": metric,
        "horizon": horizon,
        "chart": chart.model_dump(),
        "milestones": _milestones(graph, metric),
        "stale_sources": _stale_sources(sync),
        "provenance": provenance,
        "missing": missing,
        "trend": trend,
        "goal_bands": bands,
        "language": {
            "observation": "Chart points are stored metric observations with provenance.",
            "interpretation": "Trend labels are derived summaries, not clinical conclusions.",
        },
    }


def explain_progress(view: dict[str, Any]) -> dict[str, Any]:
    """Evidence-bound chart explanation (observations vs interpretation)."""
    metric = view.get("metric")
    horizon = view.get("horizon")
    chart = view.get("chart") or {}
    points = []
    for s in chart.get("series") or []:
        points.extend(s.get("points") or [])
    missing = view.get("missing") or []
    bands = view.get("goal_bands") or []
    stale = view.get("stale_sources") or []
    trend = view.get("trend") or "flat"

    lines: list[str] = []
    if missing:
        lines.append(
            f"Insufficient evidence: no stored points for {metric} in the {horizon} horizon."
        )
    else:
        first, last = points[0], points[-1]
        lines.append(
            f"Observed: {metric} moved from {first.get('y')} to {last.get('y')} "
            f"across {len(points)} point(s) in the {horizon} window "
            f"(sources: {', '.join(sorted({p.get('source') for p in points if p.get('source')})) or 'unknown'})."
        )
        lines.append(
            f"Derived trend label: {trend}. This is an interpretation of available points, "
            "not proof of long-term progress."
        )

    if bands:
        titles = [b.get("title") or b.get("goal_id") for b in bands]
        targets = [str(b.get("target")) for b in bands]
        lines.append(
            f"Goal band(s) overlaid for {', '.join(map(str, titles))} "
            f"at target(s) {', '.join(targets)}."
        )
    else:
        lines.append("No goal target band matched this metric.")

    if stale:
        lines.append(
            "Data quality warning — possibly stale sources: "
            + ", ".join(s.get("source_id") or "?" for s in stale)
            + "."
        )

    lines.append("Not medical advice — informational decision support only.")
    return {
        "metric": metric,
        "horizon": horizon,
        "explanation": " ".join(lines),
        "evidence": {
            "point_count": len(points),
            "missing": missing,
            "goal_bands": bands,
            "stale_sources": stale,
            "provenance": view.get("provenance") or [],
        },
        "kind": "derived_interpretation_over_observations",
    }


def propose_task_from_chart(
    *,
    graph: GoalGraphStore,
    metric: str,
    horizon: str,
    goal_id: str | None = None,
    title: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Create a PENDING create_task suggestion from chart context (HITL only)."""
    goals = graph.list_goals()
    target = None
    if goal_id:
        target = next((g for g in goals if g.id == goal_id), None)
        if target is None:
            raise KeyError(goal_id)
    else:
        matches = [g for g in goals if g.metric == metric]
        target = matches[0] if matches else (goals[0] if goals else None)
    if target is None:
        raise ValueError("No goals available to attach a chart-derived task")

    sug_title = title or f"Review {metric} ({horizon})"
    sug_reason = reason or (
        f"Suggested from progress chart for {metric} over {horizon}. "
        "Not created until you approve."
    )
    sug = graph.propose_suggestion(
        SuggestionCreate(
            kind=SuggestionKind.CREATE_TASK,
            title=sug_title,
            reason=sug_reason,
            evidence=[f"chart:{metric}:{horizon}"],
            assumptions=[
                "Chart-derived tasks require human approval before creation.",
                "A short window of points does not prove long-term goal attainment.",
            ],
            confidence="medium",
            affected_goal_id=target.id,
            payload={
                "title": sug_title,
                "description": sug_reason,
                "metric": metric,
                "horizon": horizon,
                "source": "chart",
            },
        )
    )
    return {
        "suggestion": sug.model_dump(),
        "applied": False,
        "human_in_the_loop": True,
        "detail": "Task suggestion pending — approve in Suggestion review.",
    }
