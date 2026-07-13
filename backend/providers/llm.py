import json
import logging
import os
from typing import Optional

import httpx

from backend.intake.schema import IntakeResult, Soreness, Sleep, Meal, WOD

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")


def _deterministic_extractor(text: str) -> IntakeResult:
    """Fallback extractor for tests or when local model is unavailable."""
    text_lower = text.lower()

    # Dummy mock logic
    sleep_quality = "good" if "good" in text_lower else "poor"
    readiness = "high" if "ready" in text_lower else "moderate"

    soreness = []
    if "sore" in text_lower and "back" in text_lower:
        soreness.append(Soreness(body_part="lower back", severity=3))

    meals = []
    if "chicken" in text_lower:
        meals.append(Meal(description="chicken and rice", protein_g=40))

    wod_movements = []
    if "pull-up" in text_lower or "pullup" in text_lower:
        wod_movements.append("pull-ups")

    return IntakeResult(
        soreness=soreness,
        sleep=Sleep(quality=sleep_quality, hours=8.0),
        meals=meals,
        todays_wod=WOD(movements=wod_movements, raw=text[:100]),
        subjective_readiness=readiness,
    )


def extract_intake(transcript: str, use_fallback: bool = False) -> IntakeResult:
    """Extract structured intake from a voice transcript using a local LLM."""
    if use_fallback or OLLAMA_MODEL == "mock":
        logger.info("Using deterministic fallback extractor")
        return _deterministic_extractor(transcript)

    schema_json = IntakeResult.model_json_schema()

    prompt = f"""
You are an expert sports science extractor. Parse the following athlete's daily update into the exact JSON schema provided.
Ensure you return ONLY valid JSON matching the schema, with no markdown formatting or extra text.

Athlete Update: "{transcript}"

JSON Schema:
{json.dumps(schema_json, indent=2)}
"""

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "format": "json",
                    "stream": False,
                },
            )
            response.raise_for_status()
            data = response.json()
            response_text = data.get("response", "{}")

            # The model should return valid JSON
            parsed_json = json.loads(response_text)
            return IntakeResult.model_validate(parsed_json)

    except Exception as e:
        logger.error(f"Failed to extract with Ollama ({OLLAMA_MODEL}): {e}")
        logger.info("Falling back to deterministic extractor")
        return _deterministic_extractor(transcript)


def generate_directive(intake: IntakeResult, context_logs: list, scores: dict) -> str:
    """Synthesize a daily training directive."""
    if OLLAMA_MODEL == "mock":
        return f"Based on your intake, your readiness score is {scores.get('readiness', {}).get('score', 50)}/100. Recommendation: Proceed with training."

    prompt = f"""
You are a functional longevity coach. Write a ONE-SENTENCE daily training directive for the athlete based on the data below.

Scores:
{json.dumps(scores, indent=2)}

Past Similar Logs Context:
{len(context_logs)} similar past logs retrieved.

Write ONLY the one-sentence directive.
"""
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "").strip()
    except Exception as e:
        logger.error(f"Failed to generate directive with Ollama: {e}")
        return f"Based on your intake, your readiness score is {scores.get('readiness', {}).get('score', 50)}/100. Proceed with caution."
