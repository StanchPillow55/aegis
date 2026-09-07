"""Local SQLite memory — vector-ish retrieval without Redis Cloud."""

from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.intake.schema import IntakeResult


_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall((text or "").lower())


def _embed(text: str, dims: int = 64) -> list[float]:
    """Hashing trick embedding — no torch/sentence-transformers required for CI."""
    vec = [0.0] * dims
    tokens = _tokenize(text)
    if not tokens:
        return vec
    for tok in tokens:
        digest = hashlib.sha256(tok.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "little") % dims
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vec[idx] += sign
    # L2 normalize
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _serialize_intake(intake: IntakeResult) -> str:
    parts = [
        f"Sleep: {intake.sleep.quality}"
        + (f", {intake.sleep.hours}h" if intake.sleep.hours is not None else ""),
    ]
    if intake.soreness:
        parts.append(
            "Soreness: "
            + ", ".join(f"{s.body_part} ({s.severity}/5)" for s in intake.soreness)
        )
    if intake.meals:
        parts.append("Meals: " + ", ".join(m.description for m in intake.meals))
    if intake.todays_wod.movements:
        parts.append("WOD: " + ", ".join(intake.todays_wod.movements))
    parts.append(f"Readiness: {intake.subjective_readiness}")
    return " | ".join(parts)


@dataclass
class MemoryHit:
    log_id: str
    timestamp: float
    content: str
    score: float
    intake: dict[str, Any]


class LocalMemoryProvider:
    """SQLite-backed log store with cosine retrieval over hashing embeddings."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is None:
            from backend.config import get_settings

            db_path = get_settings().resolved_memory_db()
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS logs (
                    log_id TEXT PRIMARY KEY,
                    ts REAL NOT NULL,
                    content TEXT NOT NULL,
                    intake_json TEXT NOT NULL,
                    embedding_json TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def store(self, data: dict[str, Any] | IntakeResult, ts: float | None = None) -> str:
        if isinstance(data, IntakeResult):
            intake = data
        else:
            intake = IntakeResult.model_validate(data)
        ts = time.time() if ts is None else ts
        content = _serialize_intake(intake)
        log_id = hashlib.sha256(f"{ts}:{content}".encode()).hexdigest()[:16]
        embedding = _embed(content)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO logs (log_id, ts, content, intake_json, embedding_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    log_id,
                    ts,
                    content,
                    intake.model_dump_json(),
                    json.dumps(embedding),
                ),
            )
            conn.commit()
        return log_id

    def search(self, query: str, k: int = 5) -> list[MemoryHit]:
        qvec = _embed(query)
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT log_id, ts, content, intake_json, embedding_json FROM logs"
            ).fetchall()
        scored: list[MemoryHit] = []
        for row in rows:
            emb = json.loads(row["embedding_json"])
            scored.append(
                MemoryHit(
                    log_id=row["log_id"],
                    timestamp=float(row["ts"]),
                    content=row["content"],
                    score=_cosine(qvec, emb),
                    intake=json.loads(row["intake_json"]),
                )
            )
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:k]

    def recent(self, n: int = 10) -> list[MemoryHit]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT log_id, ts, content, intake_json, embedding_json FROM logs ORDER BY ts DESC LIMIT ?",
                (n,),
            ).fetchall()
        return [
            MemoryHit(
                log_id=row["log_id"],
                timestamp=float(row["ts"]),
                content=row["content"],
                score=1.0,
                intake=json.loads(row["intake_json"]),
            )
            for row in rows
        ]


# Module-level helpers matching the original provider skeleton API.
_default_memory: LocalMemoryProvider | None = None


def _memory() -> LocalMemoryProvider:
    global _default_memory
    if _default_memory is None:
        _default_memory = LocalMemoryProvider()
    return _default_memory


def store_memory(data: dict) -> str:
    return _memory().store(data)


def retrieve_memory(query: str) -> list[dict]:
    return [
        {
            "log_id": hit.log_id,
            "timestamp": hit.timestamp,
            "content": hit.content,
            "score": hit.score,
            "intake": hit.intake,
        }
        for hit in _memory().search(query)
    ]
