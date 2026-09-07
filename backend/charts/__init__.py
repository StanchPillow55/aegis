"""Validated chart specifications (no arbitrary HTML/JS from LLM)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from backend.goals import GoalStore
from backend.health.store import HealthMetricsStore


ALLOWED_TYPES = {
    "metric_trend",
    "sleep_trend",
    "body_comp_trend",
    "activity_load",
    "goal_progress",
    "comparison",
}


class ChartSeries(BaseModel):
    label: str
    points: list[dict[str, Any]] = Field(default_factory=list)


class ChartSpec(BaseModel):
    type: Literal[
        "metric_trend",
        "sleep_trend",
        "body_comp_trend",
        "activity_load",
        "goal_progress",
        "comparison",
    ]
    title: str
    metric: str | None = None
    series: list[ChartSeries] = Field(default_factory=list)
    range: dict[str, Any] = Field(default_factory=dict)
    goal_bands: list[dict[str, Any]] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    source_note: str | None = None
    # Explicitly forbid HTML/script injection fields
    # (extra=forbid)
    model_config = {"extra": "forbid"}


def validate_chart_spec(data: dict[str, Any]) -> ChartSpec:
    if "html" in data or "script" in data:
        raise ValueError("Arbitrary HTML/script is not allowed in chart specs")
    return ChartSpec.model_validate(data)


def build_metric_trend(metric: str, metrics: HealthMetricsStore | None = None, goals: GoalStore | None = None) -> ChartSpec:
    store = metrics or HealthMetricsStore()
    gstore = goals or GoalStore(metrics=store)
    pts = store.series(metric, limit=60)
    series_points = [
        {
            "x": p.day or p.observed_at,
            "y": p.value,
            "source": p.provenance.source.value,
            "timestamp": p.observed_at,
        }
        for p in pts
    ]
    missing = [] if pts else [metric]
    chart_type = "metric_trend"
    if metric.startswith("sleep"):
        chart_type = "sleep_trend"
    elif metric in {"weight_kg", "body_fat_pct"}:
        chart_type = "body_comp_trend"
    elif metric in {"steps", "active_minutes", "calories", "activity_minutes"}:
        chart_type = "activity_load"
    bands = [b for b in gstore.chart_bands() if b["metric"] == metric]
    return ChartSpec(
        type=chart_type,  # type: ignore[arg-type]
        title=f"{metric} trend",
        metric=metric,
        series=[ChartSeries(label=metric, points=series_points)],
        range={"count": len(series_points)},
        goal_bands=bands,
        missing=missing,
        source_note="Local SQLite metrics; tooltips should show source+timestamp",
    )
