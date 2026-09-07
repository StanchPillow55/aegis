"""SQL-based trend analysis over score history."""

import sqlite3
from datetime import date, timedelta
from typing import Optional

from src.backend.storage.sqlite_store import _get_connection


def weekly_averages(end_date: Optional[date] = None, weeks: int = 4) -> list[dict]:
    """Get weekly average scores for the last N weeks."""
    if end_date is None:
        end_date = date.today()
    start_date = end_date - timedelta(weeks=weeks)

    conn = _get_connection()
    rows = conn.execute("""
        SELECT
            strftime('%Y-W%W', date) as week,
            AVG(sleep) as avg_sleep,
            AVG(soreness) as avg_soreness,
            AVG(diet) as avg_diet,
            AVG(hydration) as avg_hydration,
            AVG(readiness) as avg_readiness,
            AVG(performance) as avg_performance,
            COUNT(*) as log_count
        FROM score_history
        WHERE date >= ? AND date <= ?
        GROUP BY week
        ORDER BY week
    """, (start_date.isoformat(), end_date.isoformat())).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def trend_direction(dimension: str, days: int = 14) -> dict:
    """Determine if a score dimension is trending up, down, or flat."""
    end = date.today()
    start = end - timedelta(days=days)
    mid = start + timedelta(days=days // 2)

    conn = _get_connection()

    first_half = conn.execute(f"""
        SELECT AVG({dimension}) as avg_score FROM score_history
        WHERE date >= ? AND date < ?
    """, (start.isoformat(), mid.isoformat())).fetchone()

    second_half = conn.execute(f"""
        SELECT AVG({dimension}) as avg_score FROM score_history
        WHERE date >= ? AND date <= ?
    """, (mid.isoformat(), end.isoformat())).fetchone()

    conn.close()

    avg1 = first_half["avg_score"] if first_half and first_half["avg_score"] else None
    avg2 = second_half["avg_score"] if second_half and second_half["avg_score"] else None

    if avg1 is None or avg2 is None:
        return {"direction": "insufficient_data", "change": 0}

    change = avg2 - avg1
    if change > 5:
        direction = "up"
    elif change < -5:
        direction = "down"
    else:
        direction = "flat"

    return {"direction": direction, "change": round(change, 1), "first_half_avg": round(avg1, 1), "second_half_avg": round(avg2, 1)}


def best_days(n: int = 5) -> list[dict]:
    """Find the N best readiness days for pattern analysis."""
    conn = _get_connection()
    rows = conn.execute("""
        SELECT * FROM score_history
        ORDER BY readiness DESC
        LIMIT ?
    """, (n,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def worst_days(n: int = 5) -> list[dict]:
    """Find the N worst readiness days."""
    conn = _get_connection()
    rows = conn.execute("""
        SELECT * FROM score_history
        ORDER BY readiness ASC
        LIMIT ?
    """, (n,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
