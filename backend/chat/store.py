"""SQLite-backed chat session + message store (S2)."""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class StoredMessage(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    at: float = Field(default_factory=time.time)
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)

    def to_chat_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "at": self.at,
            "attachments": self.attachments,
            "tool_results": self.tool_results,
            "id": self.id,
            "session_id": self.session_id,
        }


class ChatStore:
    """Durable chat history with LIKE search (fixture-friendly)."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is None:
            from backend.config import get_settings

            db_path = Path(get_settings().data_dir) / "aegis_chat.sqlite3"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    session_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL DEFAULT 'Chat',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    at REAL NOT NULL,
                    payload_json TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES chat_sessions(session_id)
                );
                CREATE INDEX IF NOT EXISTS idx_chat_messages_session
                    ON chat_messages(session_id, at);
                CREATE INDEX IF NOT EXISTS idx_chat_messages_at
                    ON chat_messages(at);
                """
            )
            conn.commit()

    def ensure_session(self, session_id: str | None = None, *, title: str = "Chat") -> str:
        sid = session_id or uuid.uuid4().hex
        now = time.time()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT session_id FROM chat_sessions WHERE session_id = ?", (sid,)
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE chat_sessions SET updated_at = ? WHERE session_id = ?",
                    (now, sid),
                )
            else:
                conn.execute(
                    "INSERT INTO chat_sessions(session_id, title, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?)",
                    (sid, title[:80] or "Chat", now, now),
                )
            conn.commit()
        return sid

    def append_message(
        self,
        *,
        session_id: str,
        role: str,
        content: str,
        attachments: list[dict[str, Any]] | None = None,
        tool_results: list[dict[str, Any]] | None = None,
        at: float | None = None,
    ) -> StoredMessage:
        self.ensure_session(session_id)
        msg = StoredMessage(
            id=uuid.uuid4().hex[:16],
            session_id=session_id,
            role=role,
            content=content,
            at=at if at is not None else time.time(),
            attachments=list(attachments or []),
            tool_results=list(tool_results or []),
        )
        payload = {
            "attachments": msg.attachments,
            "tool_results": msg.tool_results,
        }
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO chat_messages(id, session_id, role, content, at, payload_json) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    msg.id,
                    msg.session_id,
                    msg.role,
                    msg.content,
                    msg.at,
                    json.dumps(payload),
                ),
            )
            # Title from first user message
            if role == "user" and content.strip():
                row = conn.execute(
                    "SELECT title FROM chat_sessions WHERE session_id = ?",
                    (session_id,),
                ).fetchone()
                if row and (row["title"] == "Chat" or not row["title"]):
                    conn.execute(
                        "UPDATE chat_sessions SET title = ?, updated_at = ? WHERE session_id = ?",
                        (content.strip()[:48], msg.at, session_id),
                    )
                else:
                    conn.execute(
                        "UPDATE chat_sessions SET updated_at = ? WHERE session_id = ?",
                        (msg.at, session_id),
                    )
            else:
                conn.execute(
                    "UPDATE chat_sessions SET updated_at = ? WHERE session_id = ?",
                    (msg.at, session_id),
                )
            conn.commit()
        return msg

    def history(
        self, limit: int = 40, session_id: str | None = None
    ) -> list[StoredMessage]:
        with self._connect() as conn:
            if session_id:
                rows = conn.execute(
                    "SELECT * FROM chat_messages WHERE session_id = ? "
                    "ORDER BY at DESC LIMIT ?",
                    (session_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM chat_messages ORDER BY at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        msgs = [self._row_to_msg(r) for r in rows]
        msgs.reverse()
        return msgs

    def list_sessions(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT s.session_id, s.title, s.updated_at, "
                "(SELECT COUNT(*) FROM chat_messages m WHERE m.session_id = s.session_id) "
                "AS message_count "
                "FROM chat_sessions s ORDER BY s.updated_at DESC"
            ).fetchall()
        return [
            {
                "session_id": r["session_id"],
                "title": r["title"],
                "message_count": r["message_count"],
                "updated_at": r["updated_at"],
            }
            for r in rows
        ]

    def search(self, query: str, *, limit: int = 20) -> list[dict[str, Any]]:
        q = (query or "").strip()
        if not q:
            return []
        like = f"%{q}%"
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT m.*, s.title AS session_title FROM chat_messages m "
                "JOIN chat_sessions s ON s.session_id = m.session_id "
                "WHERE m.content LIKE ? COLLATE NOCASE "
                "ORDER BY m.at DESC LIMIT ?",
                (like, limit),
            ).fetchall()
        out = []
        for r in rows:
            msg = self._row_to_msg(r)
            out.append(
                {
                    "message_id": msg.id,
                    "session_id": msg.session_id,
                    "session_title": r["session_title"],
                    "role": msg.role,
                    "content": msg.content,
                    "snippet": msg.content[:160],
                    "at": msg.at,
                }
            )
        return out

    def _row_to_msg(self, row: sqlite3.Row) -> StoredMessage:
        payload = json.loads(row["payload_json"] or "{}")
        return StoredMessage(
            id=row["id"],
            session_id=row["session_id"],
            role=row["role"],
            content=row["content"],
            at=row["at"],
            attachments=list(payload.get("attachments") or []),
            tool_results=list(payload.get("tool_results") or []),
        )
