"""Local LLM provider (Ollama + heuristic fallback)."""

from __future__ import annotations

from backend.intake.schema import IntakeResult
from backend.local_llm import OllamaClient, extract_fallback, extract_intake


class LLMProvider:
    """Base interface for LLM operations."""

    def generate_text(self, prompt: str) -> str:
        return ""

    def extract_intake(self, transcript: str) -> IntakeResult:
        return IntakeResult.model_validate(extract_fallback(transcript))


class LocalLLMProvider(LLMProvider):
    """Ollama-backed provider with deterministic offline fallback."""

    def __init__(self, client: OllamaClient | None = None) -> None:
        self.client = client

    def generate_text(self, prompt: str) -> str:
        from backend.config import get_settings

        settings = get_settings()
        client = self.client or OllamaClient(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout_s=settings.ollama_timeout_s,
        )
        if not client.available():
            return (
                "[local-llm] Ollama is not running. "
                f"Start it and pull `{settings.ollama_model}` "
                f"(endpoint {settings.ollama_base_url}). Using fallback path for intake."
            )
        return client.generate(prompt)

    def extract_intake(self, transcript: str) -> IntakeResult:
        return extract_intake(transcript, client=self.client)
