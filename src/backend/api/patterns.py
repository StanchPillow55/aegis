"""GET /api/patterns — semantic search and pattern detection."""

from typing import Optional

from fastapi import APIRouter, Query, Header

from src.backend.storage.chroma_store import search_similar
from src.backend.patterns.correlations import day_before_performance
from src.backend.patterns.insights import generate_weekly_insight

router = APIRouter(prefix="/api", tags=["patterns"])


@router.get("/patterns/search")
async def semantic_search(
    query: str = Query(..., description="Natural language search query"),
    n: int = Query(5, description="Number of results"),
    x_user_id: str = Header(default="default_user"),
):
    """Semantic search across all logged days."""
    results = search_similar(x_user_id, query, n=n)
    return {"query": query, "results": results}


@router.get("/patterns/performance-predictors")
async def performance_predictors():
    """What patterns precede best vs worst performance days?"""
    result = day_before_performance()
    if result is None:
        return {"message": "Not enough data yet (need 7+ days with performance logged)"}
    return result


@router.get("/patterns/insight")
async def weekly_insight():
    """LLM-generated weekly insight (requires Ollama running)."""
    try:
        insight = await generate_weekly_insight()
        return {"insight": insight}
    except Exception as e:
        return {"error": f"Could not generate insight: {str(e)}"}
