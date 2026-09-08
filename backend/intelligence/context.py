"""Rich screen/system context for chat (ported from legacy context_builder)."""

from __future__ import annotations

import time
from typing import Any

from backend.alerts import AlertEngine
from backend.environment import fetch_environment
from backend.goals import GoalStore
from backend.health.store import HealthMetricsStore
from backend.sync import SourceRegistry


def build_system_context(
    *,
    metrics: HealthMetricsStore | None = None,
    alerts: AlertEngine | None = None,
    goals: GoalStore | None = None,
    sync: SourceRegistry | None = None,
    panel: str | None = None,
) -> dict[str, Any]:
    metrics = metrics or HealthMetricsStore()
    alerts = alerts or AlertEngine(metrics=metrics)
    goals = goals or GoalStore(metrics=metrics)
    sync = sync or SourceRegistry()

    vitals: dict[str, Any] = {}
    for metric in ("resting_hr", "hrv", "sleep_hours", "sleep_minutes", "steps", "spo2", "weight_kg", "body_fat_pct"):
        pt = metrics.latest(metric)
        if pt is not None:
            age_h = (time.time() - pt.observed_at) / 3600.0
            vitals[metric] = {
                "value": pt.value,
                "day": pt.day,
                "source": pt.provenance.source.value,
                "quality": pt.provenance.quality.value,
                "age_hours": round(age_h, 1),
                "fresh_24h": age_h <= 24,
            }

    alerts.evaluate()
    active = [a.model_dump() for a in alerts.active()]
    goal_rows = []
    for g in goals.list():
        goal_rows.append(goals.evaluate(g.goal_id))

    sources = []
    stale = []
    for s in sync.list_sources():
        row = {
            "source_id": s.source_id.value,
            "enabled": s.enabled,
            "stale": s.stale,
            "last_success_at": s.last_success_at,
        }
        sources.append(row)
        if s.enabled and s.stale:
            stale.append(s.source_id.value)

    env = fetch_environment(force_offline=True)
    calendar_events = []
    for pt in metrics.series("calendar_event", limit=20):
        calendar_events.append(pt.meta or {"value": pt.value})

    from backend.connectors.calendar_signals import summarize_calendar_signals

    cal = summarize_calendar_signals(calendar_events) if calendar_events else {
        "events": 0,
        "travel_days": 0,
        "early_events": 0,
        "late_events": 0,
    }

    return {
        "panel": panel or "overview",
        "vitals_24h": vitals,
        "alerts_active": active,
        "goals": goal_rows,
        "sources": sources,
        "stale": stale,
        "calendar": {
            "events": cal.get("events", 0),
            "travel_days": cal.get("travel_days", 0),
            "early_events": cal.get("early_events", 0),
            "late_events": cal.get("late_events", 0),
        },
        "environment_mode": env.get("mode"),
        "geo_enabled": False,
        "disclaimer": "Informational only — not medical advice.",
    }


def format_context_text(ctx: dict[str, Any]) -> str:
    lines = ["--- SYSTEM CONTEXT ---"]
    vitals = ctx.get("vitals_24h") or {}
    if not vitals:
        lines.append("VITALS: No recent metrics.")
    else:
        parts = [f"{k}={v['value']} (src={v['source']})" for k, v in vitals.items()]
        lines.append("VITALS: " + ", ".join(parts))
    alerts = ctx.get("alerts_active") or []
    lines.append(f"ACTIVE ALERTS: {len(alerts)}")
    goals = ctx.get("goals") or []
    lines.append(f"GOALS: {len(goals)}")
    stale = ctx.get("stale") or []
    if stale:
        lines.append("STALE: " + ", ".join(stale))
    cal = ctx.get("calendar") or {}
    lines.append(
        f"CALENDAR: {cal.get('events', 0)} events; travel_days={cal.get('travel_days', 0)}"
    )
    lines.append(f"ENV MODE: {ctx.get('environment_mode')}")
    lines.append("--- END CONTEXT ---")
    return "\n".join(lines)
