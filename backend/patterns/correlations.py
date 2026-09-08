"""Simple metric correlations (Pearson) over aligned day series."""

from __future__ import annotations

import math
from typing import Any

from backend.health.store import HealthMetricsStore


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 3:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    denx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    deny = math.sqrt(sum((y - my) ** 2 for y in ys))
    if denx == 0 or deny == 0:
        return None
    return num / (denx * deny)


def correlate_metrics(
    metric_a: str,
    metric_b: str,
    *,
    limit: int = 60,
    metrics: HealthMetricsStore | None = None,
) -> dict[str, Any]:
    store = metrics or HealthMetricsStore()
    a = {p.day or str(p.observed_at): p.value for p in store.series(metric_a, limit=limit)}
    b = {p.day or str(p.observed_at): p.value for p in store.series(metric_b, limit=limit)}
    keys = sorted(set(a) & set(b))
    xs = [a[k] for k in keys]
    ys = [b[k] for k in keys]
    r = _pearson(xs, ys)
    return {
        "metric_a": metric_a,
        "metric_b": metric_b,
        "n": len(keys),
        "pearson_r": round(r, 3) if r is not None else None,
        "limitation": None if r is not None else "Need ≥3 overlapping days",
    }


def day_before_metric_performance(
    performance_metric: str = "workout_preparation",
    predictors: list[str] | None = None,
    *,
    metrics: HealthMetricsStore | None = None,
) -> dict[str, Any]:
    """Lightweight stand-in: correlate predictors with performance metric (same-day).

    Legacy used score_history day-before joins; canonical store uses metric points.
    """
    predictors = predictors or ["sleep_hours", "resting_hr", "steps"]
    out = []
    for pred in predictors:
        out.append(correlate_metrics(pred, performance_metric, metrics=metrics))
    return {"performance_metric": performance_metric, "predictors": out}
