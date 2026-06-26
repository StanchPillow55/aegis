import hashlib
import time
from typing import Optional

import redis
from pydantic import BaseModel
from redisvl.index import SearchIndex
from sentence_transformers import SentenceTransformer

from backend.config import get_settings
from backend.intake.schema import IntakeResult, StoredLog
from backend.memory.index import get_index_schema
from backend.obs.tracing import capture_exception_with_context, traced_span


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
_search_index: Optional[SearchIndex] = None
_redis_client: Optional[redis.Redis] = None


def _get_encoder() -> SentenceTransformer:
    global _encoder
    if _encoder is None:
        _encoder = SentenceTransformer("all-MiniLM-L6-v2")
    return _encoder


def _get_search_index() -> SearchIndex:
    global _search_index
    if _search_index is None:
        settings = get_settings()
        schema = get_index_schema()
        _search_index = SearchIndex(schema=schema, redis_url=settings.redis_url)
        try:
            _search_index.create(overwrite=False)
        except Exception:
            pass
    return _search_index


def _get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


def _serialize_intake(intake: IntakeResult) -> str:
    parts = []
    
    if intake.sleep:
        sleep_desc = f"Sleep: {intake.sleep.quality}"
        if intake.sleep.hours:
            sleep_desc += f", {intake.sleep.hours}h"
        parts.append(sleep_desc)
    
    if intake.soreness:
        soreness_list = [
            f"{s.body_part} (severity {s.severity}/5)"
            for s in intake.soreness
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


@traced_span("redis.store_log", operation="write")
def store_log(intake: IntakeResult, ts: float) -> str:
    try:
        content = _serialize_intake(intake)
        log_id = hashlib.sha256(f"{ts}:{content}".encode()).hexdigest()[:16]
        
        encoder = _get_encoder()
        embedding = encoder.encode(content).tolist()
        
        stored_log = StoredLog.from_intake(
            intake,
            id=log_id,
            ts=ts,
            embedding=embedding,
        )
        
        index = _get_search_index()
        
        data = {
            "log_id": stored_log.id,
            "timestamp": stored_log.ts,
            "content": content,
            "embedding": stored_log.embedding,
            "soreness_areas": ", ".join(stored_log.body_parts),
            "movements": ", ".join(stored_log.movements),
            "readiness": intake.subjective_readiness,
        }
        
        index.load([data], keys=[f"log:{log_id}"])
        
        return log_id
    except Exception as e:
        capture_exception_with_context(e, function="store_log", log_id=log_id if 'log_id' in locals() else None)
        raise


@traced_span("redis.search_similar", operation="vector_search")
def search_similar(query_text: str, k: int = 5) -> list[SearchResult]:
    try:
        encoder = _get_encoder()
        query_embedding = encoder.encode(query_text).tolist()
        
        index = _get_search_index()
        
        from redisvl.query import VectorQuery
        
        query = VectorQuery(
            vector=query_embedding,
            vector_field_name="embedding",
            return_fields=["log_id", "timestamp", "content", "soreness_areas", "movements", "readiness"],
            num_results=k,
        )
        
        results = index.query(query)
        
        logs = []
        for result in results:
            logs.append(
                SearchResult(
                    log_id=result.get("log_id", ""),
                    timestamp=float(result.get("timestamp", 0)),
                    content=result.get("content", ""),
                    soreness_areas=result.get("soreness_areas", ""),
                    movements=result.get("movements", ""),
                    readiness=result.get("readiness", ""),
                    score=float(result.get("vector_distance", 1.0)) if "vector_distance" in result else None,
                )
            )
        
        return logs
    except Exception as e:
        capture_exception_with_context(e, function="search_similar", query_text=query_text, k=k)
        raise


@traced_span("redis.get_recent", operation="read")
def get_recent(n: int = 10) -> list[SearchResult]:
    try:
        index = _get_search_index()
        client = _get_redis_client()
        
        keys = client.keys("log:*")
        
        if not keys:
            return []
        
        logs_with_ts = []
        for key in keys:
            data = client.hgetall(key)
            if data and "timestamp" in data:
                logs_with_ts.append((float(data["timestamp"]), key, data))
        
        logs_with_ts.sort(reverse=True, key=lambda x: x[0])
        
        recent_logs = []
        for ts, key, data in logs_with_ts[:n]:
            recent_logs.append(
                SearchResult(
                    log_id=data.get("log_id", ""),
                    timestamp=ts,
                    content=data.get("content", ""),
                    soreness_areas=data.get("soreness_areas", ""),
                    movements=data.get("movements", ""),
                    readiness=data.get("readiness", ""),
                )
            )
        
        return recent_logs
    except Exception as e:
        capture_exception_with_context(e, function="get_recent", n=n)
        raise


@traced_span("redis.cache_directive", operation="cache_write")
def cache_directive(key: str, rationale: str, ttl: int = 3600) -> None:
    try:
        client = _get_redis_client()
        cache_key = f"directive:{key}"
        client.setex(cache_key, ttl, rationale)
    except Exception as e:
        capture_exception_with_context(e, function="cache_directive", key=key)
        raise


@traced_span("redis.get_cached_directive", operation="cache_read")
def get_cached_directive(key: str) -> Optional[str]:
    try:
        client = _get_redis_client()
        cache_key = f"directive:{key}"
        value = client.get(cache_key)
        return value if value else None
    except Exception as e:
        capture_exception_with_context(e, function="get_cached_directive", key=key)
        raise
