"""Score correlation detection across history."""

import sqlite3
from datetime import date, timedelta
from typing import Optional

from src.backend.storage.sqlite_store import _get_connection


def day_before_performance(min_days: int = 7) -> Optional[dict]:
    """Analyze what the day-before scores look like for best vs worst performance days.
    
    Answers: 'What patterns precede my best training days?'
    """
    conn = _get_connection()
    
    # Get all days with performance scores
    rows = conn.execute("""
        SELECT s1.date as perf_date, s1.performance,
               s2.sleep as prev_sleep, s2.soreness as prev_soreness,
               s2.diet as prev_diet, s2.hydration as prev_hydration,
               s2.readiness as prev_readiness
        FROM score_history s1
        JOIN score_history s2 ON date(s1.date, '-1 day') = s2.date
        WHERE s1.performance IS NOT NULL
        ORDER BY s1.performance DESC
    """).fetchall()
    conn.close()
    
    if len(rows) < min_days:
        return None
    
    rows_list = [dict(r) for r in rows]
    top_quarter = rows_list[:len(rows_list) // 4] or rows_list[:1]
    bottom_quarter = rows_list[-(len(rows_list) // 4):] or rows_list[-1:]
    
    def avg_dict(subset, keys):
        return {k: round(sum(r[k] for r in subset if r[k] is not None) / max(1, len(subset)), 1) for k in keys}
    
    keys = ["prev_sleep", "prev_soreness", "prev_diet", "prev_hydration", "prev_readiness"]
    
    return {
        "best_performance_preceded_by": avg_dict(top_quarter, keys),
        "worst_performance_preceded_by": avg_dict(bottom_quarter, keys),
        "sample_size": len(rows_list),
    }


def soreness_after_movements(body_part: str) -> list[dict]:
    """Find which movements tend to precede soreness in a specific body part."""
    conn = _get_connection()
    
    # This requires joining with the daily_logs table to get movement data
    rows = conn.execute("""
        SELECT dl.date, dl.intake_json
        FROM daily_logs dl
        JOIN score_history sh ON dl.id = sh.log_id
        WHERE dl.intake_json LIKE ?
        ORDER BY dl.date DESC
        LIMIT 30
    """, (f'%{body_part}%',)).fetchall()
    conn.close()
    
    return [{"date": r["date"], "intake": r["intake_json"]} for r in rows]
