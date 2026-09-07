"""Local SQLite health memory — durable store with provenance + deduped retrieval."""

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

from backend.health.schema import (
    SCHEMA_VERSION,
    DataQuality,
    DataSource,
    HistoryHit,
    Provenance,
)
from backend.intake.schema import IntakeResult


_TOKEN_RE = re.compile(r"[a-z0-9]+")
_DEDUP_COSINE = 0.995


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall((text or "").lower())


def _embed(text: str, dims: int = 64) -> list[float]:
    """Hashing trick embedding — no torch required for CI."""
    vec = [0.0] * dims
    tokens = _tokenize(text)
    if not tokens:
        return vec
    for tok in tokens:
        digest = hashlib.sha256(tok.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "little") % dims
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def serialize_intake(intake: IntakeResult) -> str:
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


def content_hash_for(content: str) -> str:
    normalized = " ".join((content or "").lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]


@dataclass
class MemoryHit:
    log_id: str
    timestamp: float
    content: str
    score: float
    intake: dict[str, Any]
    provenance: dict[str, Any] | None = None
    content_hash: str | None = None

    def to_history_hit(self) -> HistoryHit:
        prov = None
        if self.provenance:
            try:
                prov = Provenance.model_validate(self.provenance)
            except Exception:
                prov = None
        return HistoryHit(
            record_id=self.log_id,
            timestamp=self.timestamp,
            content=self.content,
            score=self.score,
            intake=self.intake,
            provenance=prov,
            content_hash=self.content_hash,
        )


class LocalMemoryProvider:
    """SQLite-backed log store with cosine retrieval, provenance, and dedup."""

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
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS logs (
                    log_id TEXT PRIMARY KEY,
                    ts REAL NOT NULL,
                    content TEXT NOT NULL,
                    intake_json TEXT NOT NULL,
                    embedding_json TEXT NOT NULL,
                    content_hash TEXT,
                    provenance_json TEXT,
                    schema_version INTEGER DEFAULT 1
                )
                """
            )
            # Migrate older DBs that lack new columns.
            cols = {r[1] for r in conn.execute("PRAGMA table_info(logs)").fetchall()}
            if "content_hash" not in cols:
                conn.execute("ALTER TABLE logs ADD COLUMN content_hash TEXT")
            if "provenance_json" not in cols:
                conn.execute("ALTER TABLE logs ADD COLUMN provenance_json TEXT")
            if "schema_version" not in cols:
                conn.execute("ALTER TABLE logs ADD COLUMN schema_version INTEGER DEFAULT 1")
            conn.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES ('schema_version', ?)",
                (str(SCHEMA_VERSION),),
            )
            # Backfill hashes for legacy rows
            rows = conn.execute(
                "SELECT log_id, content, content_hash FROM logs WHERE content_hash IS NULL OR content_hash = ''"
            ).fetchall()
            for row in rows:
                ch = content_hash_for(row["content"])
                conn.execute(
                    "UPDATE logs SET content_hash = ?, schema_version = ? WHERE log_id = ?",
                    (ch, SCHEMA_VERSION, row["log_id"]),
                )
            conn.commit()

    def schema_version(self) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM meta WHERE key = 'schema_version'"
            ).fetchone()
        return int(row["value"]) if row else SCHEMA_VERSION

    def store(
        self,
        data: dict[str, Any] | IntakeResult,
        ts: float | None = None,
        *,
        provenance: Provenance | None = None,
        source: DataSource | str = DataSource.MANUAL_TEXT,
        extractor: str | None = None,
        quality: DataQuality = DataQuality.MEDIUM,
    ) -> str:
        if isinstance(data, IntakeResult):
            intake = data
        else:
            intake = IntakeResult.model_validate(data)
        ts = time.time() if ts is None else ts
        content = serialize_intake(intake)
        ch = content_hash_for(content)
        log_id = hashlib.sha256(f"{ts}:{ch}".encode()).hexdigest()[:16]
        embedding = _embed(content)

        if provenance is None:
            src = source if isinstance(source, DataSource) else DataSource(source)
            provenance = Provenance(
                source=src,
                recorded_at=ts,
                observed_at=ts,
                quality=quality,
                extractor=extractor,
                schema_version=SCHEMA_VERSION,
            )

        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO logs (
                    log_id, ts, content, intake_json, embedding_json,
                    content_hash, provenance_json, schema_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    log_id,
                    ts,
                    content,
                    intake.model_dump_json(),
                    json.dumps(embedding),
                    ch,
                    provenance.model_dump_json(),
                    SCHEMA_VERSION,
                ),
            )
            conn.commit()
        return log_id

    def _row_to_hit(self, row: sqlite3.Row, score: float) -> MemoryHit:
        prov_raw = row["provenance_json"] if "provenance_json" in row.keys() else None
        prov = json.loads(prov_raw) if prov_raw else None
        ch = row["content_hash"] if "content_hash" in row.keys() else None
        return MemoryHit(
            log_id=row["log_id"],
            timestamp=float(row["ts"]),
            content=row["content"],
            score=score,
            intake=json.loads(row["intake_json"]),
            provenance=prov,
            content_hash=ch or content_hash_for(row["content"]),
        )

    def search(
        self,
        query: str,
        k: int = 5,
        *,
        exclude_ids: set[str] | None = None,
        dedupe: bool = True,
    ) -> list[MemoryHit]:
        exclude_ids = exclude_ids or set()
        qvec = _embed(query)
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT log_id, ts, content, intake_json, embedding_json, content_hash, provenance_json FROM logs"
            ).fetchall()
        scored: list[MemoryHit] = []
        for row in rows:
            if row["log_id"] in exclude_ids:
                continue
            emb = json.loads(row["embedding_json"])
            scored.append(self._row_to_hit(row, _cosine(qvec, emb)))
        scored.sort(key=lambda h: h.score, reverse=True)

        if not dedupe:
            return scored[:k]

        # Deduplicate by content_hash, then near-duplicate cosine between kept hits.
        out: list[MemoryHit] = []
        seen_hash: set[str] = set()
        for hit in scored:
            ch = hit.content_hash or content_hash_for(hit.content)
            if ch in seen_hash:
                continue
            if any(
                _cosine(_embed(hit.content), _embed(kept.content)) >= _DEDUP_COSINE
                for kept in out
            ):
                continue
            seen_hash.add(ch)
            out.append(hit)
            if len(out) >= k:
                break
        return out

    def recent(self, n: int = 10) -> list[MemoryHit]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT log_id, ts, content, intake_json, embedding_json, content_hash, provenance_json
                FROM logs ORDER BY ts DESC LIMIT ?
                """,
                (n,),
            ).fetchall()
        return [self._row_to_hit(row, 1.0) for row in rows]

    def get(self, log_id: str) -> MemoryHit | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT log_id, ts, content, intake_json, embedding_json, content_hash, provenance_json
                FROM logs WHERE log_id = ?
                """,
                (log_id,),
            ).fetchone()
        return self._row_to_hit(row, 1.0) if row else None

    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM logs").fetchone()
        return int(row["n"])


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
            "provenance": hit.provenance,
            "content_hash": hit.content_hash,
        }
        for hit in _memory().search(query)
    ]
