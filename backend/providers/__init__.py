"""Provider interfaces — local-first implementations."""

from __future__ import annotations

from backend.providers.browser import LocalBrowserProvider, fetch_page
from backend.providers.llm import LLMProvider, LocalLLMProvider
from backend.providers.memory import (
    LocalMemoryProvider,
    retrieve_memory,
    store_memory,
)
from backend.providers.speech import (
    LocalSpeechProvider,
    synthesize_speech,
    transcribe_audio,
)
from backend.providers.tracing import LocalTracer, init_tracing, start_span

__all__ = [
    "LLMProvider",
    "LocalLLMProvider",
    "LocalMemoryProvider",
    "LocalSpeechProvider",
    "LocalBrowserProvider",
    "LocalTracer",
    "store_memory",
    "retrieve_memory",
    "transcribe_audio",
    "synthesize_speech",
    "fetch_page",
    "init_tracing",
    "start_span",
]
