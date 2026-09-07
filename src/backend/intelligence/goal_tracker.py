from typing import List, Optional
from datetime import datetime, timezone
import uuid

from src.backend.models.health_metrics import HealthMetric, MetricType
from src.backend.models.goals import (
    Goal, GoalStatus, GoalType, GoalDirection, 
    GoalCheckIn, CheckInSource, CompletionConfirmedBy
)
from src.backend.storage.sqlite_store import _get_connection

def _row_to_goal(row) -> Goal:
    return Goal(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        goal_type=GoalType(row["goal_type"]),
        metric_type=MetricType(row["metric_type"]) if row["metric_type"] else None,
        target_value=row["target_value"],
        current_value=row["current_value"],
        direction=GoalDirection(row["direction"]) if row["direction"] else None,
        unit=row["unit"],
        timeframe_start=datetime.fromisoformat(row["timeframe_start"]) if row["timeframe_start"] else None,
        timeframe_end=datetime.fromisoformat(row["timeframe_end"]) if row["timeframe_end"] else None,
        status=GoalStatus(row["status"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
        completion_confirmed_by=CompletionConfirmedBy(row["completion_confirmed_by"]) if row["completion_confirmed_by"] else None,
        progress_pct=row["progress_pct"],
        success_criteria=row["success_criteria"],
        notes=row["notes"]
    )

def _row_to_check_in(row) -> GoalCheckIn:
    return GoalCheckIn(
        id=row["id"],
        goal_id=row["goal_id"],
        timestamp=datetime.fromisoformat(row["timestamp"]),
        source=CheckInSource(row["source"]),
        message=row["message"],
        requires_confirmation=bool(row["requires_confirmation"])
    )

def get_active_goals(user_id: str) -> List[Goal]:
    conn = _get_connection()
    rows = conn.execute("SELECT * FROM goals WHERE status = ?", (GoalStatus.active.value,)).fetchall()
    conn.close()
    return [_row_to_goal(r) for r in rows]

def get_all_goals(user_id: str, status: Optional[GoalStatus] = None) -> List[Goal]:
    conn = _get_connection()
    if status:
        rows = conn.execute("SELECT * FROM goals WHERE status = ?", (status.value,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM goals").fetchall()
    conn.close()
    return [_row_to_goal(r) for r in rows]

def get_goal(goal_id: str, user_id: str) -> Optional[Goal]:
    conn = _get_connection()
    row = conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
    conn.close()
    if not row:
        return None
    return _row_to_goal(row)

def save_goal(goal: Goal, user_id: str) -> None:
    conn = _get_connection()
    conn.execute("""
        INSERT INTO goals (
            id, title, description, goal_type, metric_type, target_value, current_value, 
            direction, unit, timeframe_start, timeframe_end, status, created_at, 
            completed_at, completion_confirmed_by, progress_pct, success_criteria, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            title = excluded.title,
            description = excluded.description,
            goal_type = excluded.goal_type,
            metric_type = excluded.metric_type,
            target_value = excluded.target_value,
            current_value = excluded.current_value,
            direction = excluded.direction,
            unit = excluded.unit,
            timeframe_start = excluded.timeframe_start,
            timeframe_end = excluded.timeframe_end,
            status = excluded.status,
            completed_at = excluded.completed_at,
            completion_confirmed_by = excluded.completion_confirmed_by,
            progress_pct = excluded.progress_pct,
            success_criteria = excluded.success_criteria,
            notes = excluded.notes
    """, (
        goal.id, goal.title, goal.description, goal.goal_type.value, 
        goal.metric_type.value if goal.metric_type else None, goal.target_value, goal.current_value,
        goal.direction.value if goal.direction else None, goal.unit,
        goal.timeframe_start.isoformat() if goal.timeframe_start else None,
        goal.timeframe_end.isoformat() if goal.timeframe_end else None,
        goal.status.value, goal.created_at.isoformat(),
        goal.completed_at.isoformat() if goal.completed_at else None,
        goal.completion_confirmed_by.value if goal.completion_confirmed_by else None,
        goal.progress_pct, goal.success_criteria, goal.notes
    ))
    conn.commit()
    conn.close()

def update_goal_progress(goal_id: str, progress_pct: float, current_value: float) -> None:
    conn = _get_connection()
    conn.execute(
        "UPDATE goals SET progress_pct = ?, current_value = ? WHERE id = ?",
        (progress_pct, current_value, goal_id)
    )
    conn.commit()
    conn.close()

def create_pending_check_in(check_in: GoalCheckIn, user_id: str) -> None:
    conn = _get_connection()
    conn.execute("""
        INSERT INTO goal_check_ins (id, goal_id, timestamp, source, message, requires_confirmation)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        check_in.id, check_in.goal_id, check_in.timestamp.isoformat(),
        check_in.source.value, check_in.message, int(check_in.requires_confirmation)
    ))
    conn.commit()
    conn.close()

def get_pending_check_ins(user_id: str) -> List[GoalCheckIn]:
    conn = _get_connection()
    rows = conn.execute("SELECT * FROM goal_check_ins").fetchall()
    conn.close()
    return [_row_to_check_in(r) for r in rows]

def delete_pending_check_in(goal_id: str) -> None:
    conn = _get_connection()
    conn.execute("DELETE FROM goal_check_ins WHERE goal_id = ?", (goal_id,))
    conn.commit()
    conn.close()

def check_goals_against_metrics(metrics: List[HealthMetric], user_id: str):
    """Check all active goals against latest metrics to detect potential completions."""
    active_goals = get_active_goals(user_id)
    for g in active_goals:
        if g.goal_type != GoalType.metric_target or not g.metric_type or not g.target_value:
            continue
            
        relevant_metrics = [m for m in metrics if m.metric_type == g.metric_type]
        if not relevant_metrics:
            continue
            
        latest_metric = sorted(relevant_metrics, key=lambda x: x.timestamp)[-1]
        
        # Check if crossed target
        crossed = False
        if g.direction == GoalDirection.decrease and latest_metric.value <= g.target_value:
            crossed = True
        elif g.direction == GoalDirection.increase and latest_metric.value >= g.target_value:
            crossed = True
            
        # Update progress percentage
        if g.current_value is not None:
            total_delta = abs(g.current_value - g.target_value)
            current_delta = abs(latest_metric.value - g.target_value)
            if total_delta > 0:
                # Basic linear progress calculation
                progress = max(0.0, min(100.0, 100.0 * (1 - (current_delta / total_delta))))
                update_goal_progress(g.id, progress, latest_metric.value)
                
        # If crossed target and no existing pending check-in, create one
        if crossed:
            existing = [c for c in get_pending_check_ins(user_id) if c.goal_id == g.id]
            if not existing:
                check_in = GoalCheckIn(
                    id=str(uuid.uuid4()),
                    goal_id=g.id,
                    timestamp=datetime.now(timezone.utc),
                    source=CheckInSource.auto_detected,
                    message=f"It looks like you've hit your target of {g.target_value} {g.unit or ''} for {g.title}. Confirm?",
                    requires_confirmation=True
                )
                create_pending_check_in(check_in, user_id)

def suggest_goal_from_conversation(title: str, metric: MetricType, target: float, direction: GoalDirection, user_id: str) -> Goal:
    """Creates a draft goal based on natural language extraction."""
    goal = Goal(
        id=str(uuid.uuid4()),
        title=title,
        goal_type=GoalType.metric_target,
        metric_type=metric,
        target_value=target,
        direction=direction,
        status=GoalStatus.paused, # Wait for user to confirm before setting to active
        created_at=datetime.now(timezone.utc)
    )
    save_goal(goal, user_id)
    return goal
