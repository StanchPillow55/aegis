from backend.providers.llm import LLMProvider, LocalLLMProvider
from backend.providers.speech import transcribe_audio
from backend.providers.memory import store_memory, retrieve_memory, LocalMemoryProvider
from backend.providers.browser import fetch_page
from backend.providers.tracing import init_tracing


def test_imports() -> None:
    """Test that all providers can be imported."""
    assert callable(LLMProvider)
    assert callable(LocalLLMProvider)
    assert callable(LocalMemoryProvider)
    assert callable(transcribe_audio)
    assert callable(store_memory)
    assert callable(retrieve_memory)
    assert callable(fetch_page)
    assert callable(init_tracing)


def test_local_llm_provider_offline_generate():
    provider = LocalLLMProvider()
    # Force offline client
    from backend.local_llm import OllamaClient

    provider.client = OllamaClient(base_url="http://127.0.0.1:9", timeout_s=0.2)
    text = provider.generate_text("hello")
    assert "Ollama is not running" in text
