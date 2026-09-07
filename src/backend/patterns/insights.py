"""LLM-powered pattern narratives (optional, uses Ollama)."""

from typing import Optional

import httpx

from src.backend.config import get_settings
from src.backend.patterns.trends import weekly_averages, trend_direction, best_days


async def generate_weekly_insight(base_url: Optional[str] = None) -> str:
    """Generate a natural language summary of the week's patterns."""
    settings = get_settings()
    url = base_url or settings.ollama_base_url

    # Gather data
    averages = weekly_averages(weeks=2)
    trends = {
        dim: trend_direction(dim, days=14)
        for dim in ["sleep", "soreness", "diet", "hydration", "readiness"]
    }
    best = best_days(3)

    prompt = f"""You are a concise fitness analyst. Based on this athlete's recent data, give a 2-3 sentence insight about their patterns and one actionable suggestion.

Weekly averages (last 2 weeks): {averages}
Trends (14-day direction): {trends}
Best readiness days: {best}

Be specific and data-driven. No fluff."""

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{url}/api/generate",
            json={
                "model": settings.ollama_model,
                "prompt": prompt,
                "stream": False,
            },
        )
        response.raise_for_status()
        result = response.json()

    return result.get("response", "Unable to generate insight.")
