"""Metric trend helpers using the health metrics store (not legacy score_history)."""

from __future__ import annotations

from typing import Any

from backend.health.store import HealthMetricsStore


def trend_direction(metric: str, *, days: int = 14, metrics: HealthMetricsStore | None = None) -> dict[str, Any]:
    store = metrics or HealthMetricsStore()
    pts = store.series(metric, limit=max(days * 2, 10))
    if len(pts) < 4:
        return {"metric": metric, "direction": "insufficient_data", "change": 0, "sample": len(pts)}
    mid = len(pts) // 2
    first = pts[:mid]
    second = pts[mid:]
    avg1 = sum(p.value for p in first) / len(first)
    avg2 = sum(p.value for p in second) / len(second)
    change = avg2 - avg1
    if change > 5:
        direction = "up"
    elif change < -5:
        direction = "down"
    else:
        direction = "flat"
    return {
        "metric": metric,
        "direction": direction,
        "change": round(change, 2),
        "first_half_avg": round(avg1, 2),
        "second_half_avg": round(avg2, 2),
        "sample": len(pts),
    }


def weekly_metric_averages(metric: str, *, limit: int = 60, metrics: HealthMetricsStore | None = None) -> dict[str, Any]:
    store = metrics or HealthMetricsStore()
    pts = store.series(metric, limit=limit)
    buckets: dict[str, list[float]] = {}
    for p in pts:
        day = p.day or "unknown"
        # crude week key from ISO day
        key = day[:8] + "W?" if len(day) >= 8 else day
        if p.day and len(p.day) >= 10:
            import datetime as dt

            try:
                d = dt.date.fromisoformat(p.day)
                key = f"{d.isocalendar().year}-W{d.isocalendar().week:02d}"
            except ValueError:
                key = p.day
        buckets.setdefault(key, []).append(p.value)
    weeks = [
        {"week": w, "avg": round(sum(vs) / len(vs), 2), "count": len(vs)}
        for w, vs in sorted(buckets.items())
    ]
    return {"metric": metric, "weeks": weeks}
