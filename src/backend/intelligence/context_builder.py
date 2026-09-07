from typing import Dict, Any, List
from datetime import datetime, timedelta, timezone

from src.backend.storage.sqlite_store import _get_connection
from src.backend.models.health_metrics import MetricType, DataSource
from src.backend.safety.anomaly_detector import get_active_alerts
from src.backend.intelligence.goal_tracker import get_active_goals, get_pending_check_ins
from src.backend.sync.scheduler import get_sync_status
import json

def build_context(user_id: str) -> str:
    """Builds a summarized context of the user's current state."""
    conn = _get_connection()
    context = []
    context.append("--- SYSTEM CONTEXT ---")
    
    # 1. 24h Vitals
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    rows = conn.execute(
        "SELECT metric_type, value, unit, timestamp FROM health_metrics "
        "WHERE user_id=? AND timestamp >= ? ORDER BY timestamp DESC",
        (user_id, cutoff)
    ).fetchall()
    
    if not rows:
        context.append("VITALS (Last 24h): No vitals data synced in the last 24h.")
    else:
        metrics = {}
        for r in rows:
            mt = r["metric_type"]
            if mt not in metrics:
                metrics[mt] = []
            metrics[mt].append(r["value"])
            
        parts = []
        if MetricType.heart_rate.value in metrics:
            hrs = metrics[MetricType.heart_rate.value]
            parts.append(f"HR {min(hrs):.0f}-{max(hrs):.0f}bpm")
        if MetricType.resting_heart_rate.value in metrics:
            parts.append(f"Resting HR {metrics[MetricType.resting_heart_rate.value][0]:.0f}bpm")
        if MetricType.hrv.value in metrics:
            parts.append(f"HRV {metrics[MetricType.hrv.value][0]:.0f}ms")
        if MetricType.sleep_duration.value in metrics:
            sleep_hrs = metrics[MetricType.sleep_duration.value][0] / 60.0
            parts.append(f"Sleep {sleep_hrs:.1f}h")
            
        context.append(f"VITALS (Last 24h): {', '.join(parts)}.")
    
    # 2. Active Alerts
    alerts = get_active_alerts(user_id)
    if alerts:
        context.append("ACTIVE ALERTS:")
        for a in alerts:
            context.append(f"- [{a.severity.name.upper()}] {a.message}")
    else:
        context.append("ACTIVE ALERTS: None")
        
    # 3. Body Composition
    bc_row = conn.execute("SELECT * FROM body_compositions ORDER BY date DESC LIMIT 1").fetchone()
    if bc_row:
        context.append(f"BODY COMPOSITION: Last recorded {bc_row['weight']} lbs, {bc_row['body_fat_pct']}% body fat ({bc_row['date']}).")
    else:
        context.append("BODY COMPOSITION: No body composition data recorded.")
    
    # 4. Calendar Context
    cal_rows = conn.execute(
        "SELECT * FROM calendar_events WHERE date(start_time) = date('now') ORDER BY start_time"
    ).fetchall()
    
    if cal_rows:
        has_travel = False
        for r in cal_rows:
            if r["derived_signals"]:
                signals = json.loads(r["derived_signals"])
                if signals.get("travel", False):
                    has_travel = True
                    break
        travel_str = "Travel detected." if has_travel else "No travel detected."
        context.append(f"CALENDAR: {len(cal_rows)} meetings today. {travel_str}")
    else:
        context.append("CALENDAR: No calendar data synced.")
    
    # 5. Active Goals
    goals = get_active_goals(user_id)
    if goals:
        context.append("ACTIVE GOALS:")
        for g in goals:
            prog = f"{g.progress_pct:.1f}%" if g.progress_pct is not None else "Unknown"
            context.append(f"- {g.title}: {prog} progress")
            
    # 6. Pending Confirmations
    pending = get_pending_check_ins(user_id)
    if pending:
        context.append(f"PENDING GOAL CONFIRMATIONS: {len(pending)}")
        
    # 7. Staleness
    stale_sources = []
    for s in [DataSource.fitbit, DataSource.calendar, DataSource.fitindex]:
        status = get_sync_status(s.value)
        if status.enabled and status.last_sync_at:
            if datetime.now(timezone.utc) - status.last_sync_at > timedelta(hours=24):
                stale_sources.append(s.value)
    if stale_sources:
        context.append(f"STALE DATA WARNING: {', '.join(stale_sources)} haven't synced in >24h.")
        
    context.append("--- END CONTEXT ---")
    
    conn.close()
    return "\n".join(context)
