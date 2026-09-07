import json
import math
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta

from src.backend.models.health_metrics import MetricType
from src.backend.models.goals import GoalDirection
from src.backend.intelligence.goal_tracker import suggest_goal_from_conversation, get_active_goals
from src.backend.storage.sqlite_store import _get_connection

# Emitted chart specs that the frontend will intercept
_EMITTED_CHARTS = []

def query_metric(metric_type: str, start_date: str, end_date: str) -> str:
    """Fetch time-series data for a specific metric."""
    # Emits chart spec
    _EMITTED_CHARTS.append({
        "chart": {
            "metric": metric_type,
            "start": start_date,
            "end": end_date,
            "type": "line"
        }
    })
    return f"Retrieved {metric_type} from {start_date} to {end_date}."

def get_body_composition(user_id: str, date_range: str) -> str:
    import dateparser
    parsed = dateparser.parse(date_range)
    if parsed:
        start_date = parsed.astimezone(timezone.utc)
    else:
        try:
            start_date = datetime.fromisoformat(date_range)
        except:
            start_date = datetime.now(timezone.utc) - timedelta(days=30)
    
    conn = _get_connection()
    # In reality body comp schema doesn't have user_id currently, but let's assume it should or we just query by date
    # Let's check sqlite_store.py schema for body_compositions: id, date, weight, body_fat_pct, etc.
    # Ah, body_compositions doesn't have user_id in the baseline schema! Let me omit user_id from the WHERE clause for body_comp for now, or just query it.
    rows = conn.execute("SELECT * FROM body_compositions WHERE date >= ? ORDER BY date ASC", (start_date.isoformat()[:10],)).fetchall()
    conn.close()
    
    if not rows:
        return "No body composition data for this period."
        
    latest = rows[-1]
    if len(rows) > 1:
        first = rows[0]
        delta_w = latest["weight"] - first["weight"]
        return f"{len(rows)} measurements. Latest: {latest['weight']} lbs, {latest['body_fat_pct']}% body fat ({latest['date']}). 30-day change: {delta_w:+.1f} lbs."
    else:
        return f"{len(rows)} measurements. Latest: {latest['weight']} lbs, {latest['body_fat_pct']}% body fat ({latest['date']}). 30-day change: +0.0 lbs."

def get_calendar_context(user_id: str, date_range: str) -> str:
    import dateparser
    parsed = dateparser.parse(date_range)
    if parsed:
        start_date = parsed.astimezone(timezone.utc)
    else:
        try:
            start_date = datetime.fromisoformat(date_range)
        except:
            start_date = datetime.now(timezone.utc) - timedelta(days=7)
    
    conn = _get_connection()
    rows = conn.execute("SELECT * FROM calendar_events WHERE start_time >= ?", (start_date.isoformat(),)).fetchall()
    conn.close()
    
    if not rows:
        return "No calendar data for this period."
        
    travel_days = 0
    early = 0
    late = 0
    for r in rows:
        if r["derived_signals"]:
            sig = json.loads(r["derived_signals"])
            if sig.get("travel"): travel_days += 1
            if sig.get("early_morning"): early += 1
            if sig.get("late_night"): late += 1
            
    return f"{len(rows)} events. {travel_days} travel days, {early} early events, {late} late events."

def compare_periods(user_id: str, metric: str, period_a: str, period_b: str) -> str:
    conn = _get_connection()
    import dateparser
    parsed_a = dateparser.parse(period_a)
    parsed_b = dateparser.parse(period_b)
    
    if parsed_a:
        cutoff_a = parsed_a.astimezone(timezone.utc).isoformat()
    else:
        cutoff_a = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        
    if parsed_b:
        cutoff_b = parsed_b.astimezone(timezone.utc).isoformat()
    else:
        cutoff_b = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
    
    rows_a = conn.execute("SELECT AVG(value) as avg_val FROM health_metrics WHERE user_id=? AND metric_type=? AND timestamp >= ?", (user_id, metric, cutoff_a)).fetchone()
    rows_b = conn.execute("SELECT AVG(value) as avg_val FROM health_metrics WHERE user_id=? AND metric_type=? AND timestamp >= ? AND timestamp < ?", (user_id, metric, cutoff_b, cutoff_a)).fetchone()
    conn.close()
    
    val_a = rows_a["avg_val"] if rows_a and rows_a["avg_val"] else 0.0
    val_b = rows_b["avg_val"] if rows_b and rows_b["avg_val"] else 0.0
    
    if val_b == 0:
        pct = 0.0
    else:
        pct = ((val_a - val_b) / val_b) * 100
        
    return f"{metric} avg {val_a:.1f} in period_a vs {val_b:.1f} in period_b ({pct:+.1f}%)."

def get_correlations(user_id: str, metric_a: str, metric_b: str, days: int) -> str:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    conn = _get_connection()
    rows_a = conn.execute("SELECT date(timestamp) as d, AVG(value) as v FROM health_metrics WHERE user_id=? AND metric_type=? AND timestamp >= ? GROUP BY d", (user_id, metric_a, cutoff)).fetchall()
    rows_b = conn.execute("SELECT date(timestamp) as d, AVG(value) as v FROM health_metrics WHERE user_id=? AND metric_type=? AND timestamp >= ? GROUP BY d", (user_id, metric_b, cutoff)).fetchall()
    conn.close()
    
    dict_a = {r["d"]: r["v"] for r in rows_a}
    dict_b = {r["d"]: r["v"] for r in rows_b}
    
    common_days = set(dict_a.keys()).intersection(set(dict_b.keys()))
    if len(common_days) < 2:
        return f"Not enough overlapping data between {metric_a} and {metric_b}."
        
    x = [dict_a[d] for d in common_days]
    y = [dict_b[d] for d in common_days]
    
    # Pearson r
    n = len(x)
    sum_x = sum(x)
    sum_y = sum(y)
    sum_xy = sum(xi*yi for xi, yi in zip(x, y))
    sum_x2 = sum(xi*xi for xi in x)
    sum_y2 = sum(yi*yi for yi in y)
    
    denom = math.sqrt((n * sum_x2 - sum_x**2) * (n * sum_y2 - sum_y**2))
    if denom == 0:
        r = 0.0
    else:
        r = (n * sum_xy - sum_x * sum_y) / denom
        
    direction = "positive" if r > 0 else "negative"
    strength = "strong" if abs(r) > 0.5 else "weak"
    return f"{metric_a} and {metric_b} show {strength} {direction} correlation (r={r:.2f}) over {n} days."

def check_goal_progress(goal_id: str, user_id: str) -> str:
    goals = get_active_goals(user_id)
    for g in goals:
        if g.id == goal_id:
            return f"Goal {g.title} is at {g.progress_pct}%."
    return "Goal not found."

def suggest_goal(title: str, metric: str, target: float, direction: str, user_id: str) -> str:
    goal = suggest_goal_from_conversation(
        title=title,
        metric=MetricType(metric),
        target=target,
        direction=GoalDirection(direction),
        user_id=user_id
    )
    return f"Drafted goal '{title}'. Awaiting user confirmation."

def pop_emitted_charts() -> List[Dict[str, Any]]:
    global _EMITTED_CHARTS
    charts = _EMITTED_CHARTS.copy()
    _EMITTED_CHARTS = []
    return charts
