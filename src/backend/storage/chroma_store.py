"""ChromaDB vector storage for semantic search and pattern matching."""

from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from src.backend.config import get_settings
from src.backend.models.intake import DailyLog

_client: Optional[chromadb.ClientAPI] = None
_collection: Optional[chromadb.Collection] = None

COLLECTION_NAME = "daily_logs"


def _get_collection() -> chromadb.Collection:
    global _client, _collection
    if _collection is None:
        settings = get_settings()
        _client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def _build_summary(log: DailyLog) -> str:
    """Build a human-readable summary for embedding."""
    parts = []
    intake = log.intake

    if intake.sleep:
        s = f"Sleep: {intake.sleep.quality}"
        if intake.sleep.hours:
            s += f", {intake.sleep.hours}h"
        parts.append(s)

    if intake.soreness:
        areas = [f"{s.body_part} ({s.severity}/5)" for s in intake.soreness]
        parts.append(f"Soreness: {', '.join(areas)}")

    if intake.meals:
        parts.append(f"Meals: {', '.join(m.description for m in intake.meals)}")

    if intake.hydration:
        h_parts = []
        if intake.hydration.water_oz:
            h_parts.append(f"{intake.hydration.water_oz}oz water")
        if intake.hydration.alcohol_drinks:
            h_parts.append(f"{intake.hydration.alcohol_drinks} drinks")
        if h_parts:
            parts.append(f"Hydration: {', '.join(h_parts)}")

    if intake.todays_wod and intake.todays_wod.movements:
        wod = f"WOD: {', '.join(intake.todays_wod.movements)}"
        if intake.todays_wod.raw:
            wod += f" ({intake.todays_wod.raw})"
        parts.append(wod)

    if intake.performance:
        perf_parts = []
        if intake.performance.feel:
            perf_parts.append(f"felt {intake.performance.feel}")
        if intake.performance.hr_max:
            perf_parts.append(f"HR max {intake.performance.hr_max}")
        if intake.performance.total_time_seconds:
            mins = intake.performance.total_time_seconds / 60
            perf_parts.append(f"{mins:.1f} min")
        if perf_parts:
            parts.append(f"Performance: {', '.join(perf_parts)}")

    if intake.subjective_readiness:
        parts.append(f"Readiness: {intake.subjective_readiness}")

    return " | ".join(parts) if parts else "No data"


def store_embedding(user_id: str, log: DailyLog) -> None:
    """Store a daily log's embedding in ChromaDB."""
    collection = _get_collection()
    summary = log.summary_text or _build_summary(log)

    metadata = {
        "user_id": user_id,
        "date": log.date.isoformat(),
        "readiness": log.scores.readiness if log.scores else 0,
        "sleep_score": log.scores.sleep if log.scores else 0,
        "soreness_score": log.scores.soreness if log.scores else 0,
    }

    # Add soreness body parts and WOD movements for filtering
    if log.intake.soreness:
        metadata["sore_areas"] = ",".join(s.body_part for s in log.intake.soreness)
    if log.intake.todays_wod:
        metadata["movements"] = ",".join(log.intake.todays_wod.movements)
    if log.intake.performance and log.intake.performance.feel:
        metadata["feel"] = log.intake.performance.feel

    collection.upsert(
        ids=[log.id],
        documents=[summary],
        metadatas=[metadata],
    )


def search_similar(user_id: str, query: str, n: int = 5, where: Optional[dict] = None) -> list[dict]:
    """Semantic search across all logs."""
    collection = _get_collection()
    
    where_clause = {"user_id": user_id}
    if where:
        # Chroma supports simple $and
        where_clause = {"$and": [{"user_id": user_id}, where]}
        
    kwargs = {"query_texts": [query], "n_results": n, "where": where_clause}

    results = collection.query(**kwargs)

    logs = []
    if results and results["ids"]:
        for i, doc_id in enumerate(results["ids"][0]):
            logs.append({
                "id": doc_id,
                "document": results["documents"][0][i] if results["documents"] else "",
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else None,
            })
    return logs


def get_similar_days(user_id: str, log: DailyLog, n: int = 5) -> list[dict]:
    """Find days most similar to a given log."""
    summary = log.summary_text or _build_summary(log)
    return search_similar(user_id, summary, n=n)
