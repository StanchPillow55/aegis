"""SQLite storage for daily logs, scores, and time-series queries."""

import json
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from src.backend.config import get_settings
from src.backend.models.intake import DailyLog, IntakeResult, ScoreSet


def _get_db_path() -> Path:
    settings = get_settings()
    path = Path(settings.sqlite_db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _get_connection() -> sqlite3.Connection:
    db_path = _get_db_path()
    conn = sqlite3.connect(str(db_path), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    """Create tables if they don't exist."""
    conn = _get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS daily_logs (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            date TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT,
            raw_input TEXT,
            intake_json TEXT NOT NULL,
            scores_json TEXT,
            summary_text TEXT,
            UNIQUE(user_id, date)
        );

        CREATE INDEX IF NOT EXISTS idx_logs_user_date ON daily_logs(user_id, date);

        CREATE TABLE IF NOT EXISTS score_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_id TEXT NOT NULL REFERENCES daily_logs(id),
            date TEXT NOT NULL,
            sleep INTEGER,
            soreness INTEGER,
            diet INTEGER,
            hydration INTEGER,
            performance INTEGER,
            readiness INTEGER
        );

        CREATE INDEX IF NOT EXISTS idx_scores_date ON score_history(date);

        -- Health Metrics (Task 1)
        CREATE TABLE IF NOT EXISTS health_metrics (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            metric_type TEXT NOT NULL,
            value REAL NOT NULL,
            unit TEXT NOT NULL,
            source TEXT NOT NULL,
            metadata TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_hm_user_ts_type ON health_metrics(user_id, timestamp, metric_type);

        CREATE TABLE IF NOT EXISTS body_compositions (
            id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            weight REAL NOT NULL,
            body_fat_pct REAL,
            muscle_mass_pct REAL,
            bone_mass REAL,
            bmi REAL,
            visceral_fat REAL,
            body_water_pct REAL,
            metabolic_age INTEGER,
            source TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS calendar_events (
            id TEXT PRIMARY KEY,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            title TEXT NOT NULL,
            location TEXT,
            description TEXT,
            all_day BOOLEAN,
            derived_signals TEXT
        );

        CREATE TABLE IF NOT EXISTS sync_status (
            source TEXT PRIMARY KEY,
            last_sync_at TEXT,
            next_sync_at TEXT,
            enabled BOOLEAN DEFAULT 1,
            error_count INTEGER DEFAULT 0,
            last_error TEXT
        );

        CREATE TABLE IF NOT EXISTS auth_tokens (
            source TEXT PRIMARY KEY,
            access_token TEXT NOT NULL,
            refresh_token TEXT NOT NULL,
            expires_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS chat_sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT,
            summarized_through_message_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS conversation_history (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            session_id TEXT
        );

        -- Safety Thresholds (Task 6)
        CREATE TABLE IF NOT EXISTS safety_thresholds (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            metric_type TEXT NOT NULL,
            condition TEXT NOT NULL,
            value REAL NOT NULL,
            window_hours INTEGER,
            severity TEXT NOT NULL,
            message TEXT NOT NULL,
            is_system_default BOOLEAN DEFAULT 0,
            user_modified BOOLEAN DEFAULT 0
        );

        -- Safety Alerts
        CREATE TABLE IF NOT EXISTS safety_alerts (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            severity TEXT NOT NULL,
            message TEXT NOT NULL,
            metric_type TEXT NOT NULL,
            metric_value REAL NOT NULL,
            threshold_value REAL NOT NULL,
            timestamp TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            resolved_at TEXT,
            action_taken TEXT
        );

        -- Goals (Task 7)
        CREATE TABLE IF NOT EXISTS goals (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            goal_type TEXT NOT NULL,
            metric_type TEXT,
            target_value REAL,
            current_value REAL,
            direction TEXT,
            unit TEXT,
            timeframe_start TEXT,
            timeframe_end TEXT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            completion_confirmed_by TEXT,
            progress_pct REAL,
            success_criteria TEXT,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS goal_progress (
            id TEXT PRIMARY KEY,
            goal_id TEXT NOT NULL REFERENCES goals(id),
            date TEXT NOT NULL,
            value REAL NOT NULL,
            note TEXT
        );

        CREATE TABLE IF NOT EXISTS goal_check_ins (
            id TEXT PRIMARY KEY,
            goal_id TEXT NOT NULL REFERENCES goals(id),
            timestamp TEXT NOT NULL,
            source TEXT NOT NULL,
            message TEXT NOT NULL,
            requires_confirmation BOOLEAN DEFAULT 0
        );
    """)
    conn.commit()
    conn.close()


def save_log(user_id: str, log: DailyLog) -> str:
    """Insert or update a daily log."""
    conn = _get_connection()
    scores_json = log.scores.model_dump_json() if log.scores else None

    conn.execute("""
        INSERT INTO daily_logs (id, user_id, date, created_at, updated_at, raw_input, intake_json, scores_json, summary_text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, date) DO UPDATE SET
            updated_at = excluded.updated_at,
            raw_input = excluded.raw_input,
            intake_json = excluded.intake_json,
            scores_json = excluded.scores_json,
            summary_text = excluded.summary_text
    """, (
        log.id, user_id, log.date.isoformat(), log.created_at.isoformat(),
        log.updated_at.isoformat() if log.updated_at else None,
        log.raw_input, log.intake.model_dump_json(), scores_json, log.summary_text,
    ))

    if log.scores:
        conn.execute("""
            INSERT OR REPLACE INTO score_history (log_id, date, sleep, soreness, diet, hydration, performance, readiness)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            log.id, log.date.isoformat(),
            log.scores.sleep, log.scores.soreness, log.scores.diet,
            log.scores.hydration, log.scores.performance, log.scores.readiness,
        ))

    conn.commit()
    conn.close()
    return log.id


def get_log_by_date(user_id: str, d: date) -> Optional[DailyLog]:
    """Retrieve a single day's log."""
    conn = _get_connection()
    row = conn.execute("SELECT * FROM daily_logs WHERE user_id = ? AND date = ?", (user_id, d.isoformat())).fetchone()
    conn.close()
    if not row:
        return None
    return _row_to_log(row)


def get_logs_range(user_id: str, start: date, end: date) -> list[DailyLog]:
    """Get all logs in a date range (inclusive)."""
    conn = _get_connection()
    rows = conn.execute(
        "SELECT * FROM daily_logs WHERE user_id = ? AND date >= ? AND date <= ? ORDER BY date",
        (user_id, start.isoformat(), end.isoformat()),
    ).fetchall()
    conn.close()
    return [_row_to_log(r) for r in rows]


def get_scores_range(user_id: str, start: date, end: date) -> list[dict]:
    """Get score time-series for trend charts."""
    conn = _get_connection()
    rows = conn.execute(
        "SELECT s.* FROM score_history s JOIN daily_logs l ON s.log_id = l.id WHERE l.user_id = ? AND s.date >= ? AND s.date <= ? ORDER BY s.date",
        (user_id, start.isoformat(), end.isoformat()),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _row_to_log(row) -> DailyLog:
    intake = IntakeResult.model_validate_json(row["intake_json"])
    scores = ScoreSet.model_validate_json(row["scores_json"]) if row["scores_json"] else None
    return DailyLog(
        id=row["id"],
        date=date.fromisoformat(row["date"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
        raw_input=row["raw_input"],
        intake=intake,
        scores=scores,
        summary_text=row["summary_text"],
    )

def create_chat_session(session_id: str, user_id: str, title: str):
    conn = _get_connection()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("INSERT INTO chat_sessions (id, user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                 (session_id, user_id, title, now, now))
    conn.commit()
    conn.close()

def get_chat_sessions(user_id: str) -> list[dict]:
    conn = _get_connection()
    rows = conn.execute("SELECT id, title, summary, created_at, updated_at FROM chat_sessions WHERE user_id = ? ORDER BY updated_at DESC", (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_chat_session(session_id: str, user_id: str):
    conn = _get_connection()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("UPDATE chat_sessions SET updated_at = ? WHERE id = ? AND user_id = ?", (now, session_id, user_id))
    conn.commit()
    conn.close()

def update_chat_session_summary(session_id: str, user_id: str, summary: str, summarized_through_message_id: str):
    conn = _get_connection()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE chat_sessions SET summary = ?, summarized_through_message_id = ?, updated_at = ? WHERE id = ? AND user_id = ?",
        (summary, summarized_through_message_id, now, session_id, user_id)
    )
    conn.commit()
    conn.close()

