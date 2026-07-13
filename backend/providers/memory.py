import json
import logging
import os
import sqlite3
import time
from typing import Optional, List

from pydantic import BaseModel
import chromadb
from sentence_transformers import SentenceTransformer

from backend.intake.schema import IntakeResult, StoredLog

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("SQLITE_DB_PATH", "aegis_local.db")
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "chroma_data")


class SearchResult(BaseModel):
    """Lightweight search result from vector query."""

    log_id: str
    timestamp: float
    content: str
    soreness_areas: str
    movements: str
    readiness: str
    score: Optional[float] = None


_encoder: Optional[SentenceTransformer] = None
_chroma_client: Optional[chromadb.ClientAPI] = None


def _get_encoder() -> SentenceTransformer:
    global _encoder
    if _encoder is None:
        logger.info("Loading sentence-transformers all-MiniLM-L6-v2")
        _encoder = SentenceTransformer("all-MiniLM-L6-v2")
    return _encoder


def _get_chroma_collection():
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    return _chroma_client.get_or_create_collection(name="aegis_logs")


def _init_sqlite():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS logs (
            log_id TEXT PRIMARY KEY,
            timestamp REAL,
            intake_json TEXT,
            content TEXT
        )
    """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS directives_cache (
            key TEXT PRIMARY KEY,
            rationale TEXT,
            expires_at REAL
        )
    """
    )
    conn.commit()
    conn.close()


# Initialize DB on module load
_init_sqlite()


def _serialize_intake(intake: IntakeResult) -> str:
    parts = []

    if intake.sleep:
        sleep_desc = f"Sleep: {intake.sleep.quality}"
        if intake.sleep.hours:
            sleep_desc += f", {intake.sleep.hours}h"
        parts.append(sleep_desc)

    if intake.soreness:
        soreness_list = [
            f"{s.body_part} (severity {s.severity}/5)" for s in intake.soreness
        ]
        parts.append(f"Soreness: {', '.join(soreness_list)}")

    if intake.meals:
        meal_list = [m.description for m in intake.meals]
        parts.append(f"Meals: {', '.join(meal_list)}")

    if intake.todays_wod and intake.todays_wod.movements:
        wod_desc = f"WOD: {', '.join(intake.todays_wod.movements)}"
        if intake.todays_wod.raw:
            wod_desc += f" ({intake.todays_wod.raw})"
        parts.append(wod_desc)

    parts.append(f"Readiness: {intake.subjective_readiness}")

    return " | ".join(parts)


def store_log(intake: IntakeResult, ts: float) -> str:
    try:
        content = _serialize_intake(intake)
        import hashlib

        log_id = hashlib.sha256(f"{ts}:{content}".encode()).hexdigest()[:16]

        # Save to SQLite
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO logs (log_id, timestamp, intake_json, content) VALUES (?, ?, ?, ?)",
            (log_id, ts, intake.model_dump_json(), content),
        )
        conn.commit()
        conn.close()

        # Save to Chroma
        try:
            encoder = _get_encoder()
            embedding = encoder.encode(content).tolist()
            collection = _get_chroma_collection()

            collection.add(
                ids=[log_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[
                    {
                        "timestamp": ts,
                        "soreness_areas": ", ".join(
                            [s.body_part for s in intake.soreness]
                        ),
                        "movements": ", ".join(intake.todays_wod.movements),
                        "readiness": intake.subjective_readiness,
                    }
                ],
            )
        except Exception as e:
            logger.error(f"Failed to add to Chroma vector store: {e}")

        return log_id
    except Exception as e:
        logger.error(f"Error storing log: {e}")
        raise


def search_similar(query_text: str, k: int = 5) -> List[SearchResult]:
    try:
        encoder = _get_encoder()
        query_embedding = encoder.encode(query_text).tolist()

        collection = _get_chroma_collection()
        results = collection.query(query_embeddings=[query_embedding], n_results=k)

        search_results = []
        if not results["ids"] or not results["ids"][0]:
            return search_results

        for i in range(len(results["ids"][0])):
            metadata = results["metadatas"][0][i] or {}
            search_results.append(
                SearchResult(
                    log_id=results["ids"][0][i],
                    timestamp=metadata.get("timestamp", 0),
                    content=results["documents"][0][i] if results["documents"] else "",
                    soreness_areas=metadata.get("soreness_areas", ""),
                    movements=metadata.get("movements", ""),
                    readiness=metadata.get("readiness", ""),
                    score=(
                        results["distances"][0][i]
                        if "distances" in results and results["distances"]
                        else None
                    ),
                )
            )

        return search_results
    except Exception as e:
        logger.error(f"Error searching Chroma vector store: {e}")
        # Graceful degradation: return empty if vector service fails
        return []


def cache_directive(key: str, rationale: str, ttl: int = 3600) -> None:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        expires_at = time.time() + ttl
        cursor.execute(
            "INSERT OR REPLACE INTO directives_cache (key, rationale, expires_at) VALUES (?, ?, ?)",
            (key, rationale, expires_at),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error caching directive: {e}")


def get_cached_directive(key: str) -> Optional[str]:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT rationale, expires_at FROM directives_cache WHERE key = ?", (key,)
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            rationale, expires_at = row
            if time.time() < expires_at:
                return rationale
            else:
                return None
        return None
    except Exception as e:
        logger.error(f"Error getting cached directive: {e}")
        return None
