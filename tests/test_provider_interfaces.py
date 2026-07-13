def test_import_llm_provider():
    from backend.providers.llm import LLMProvider
    assert LLMProvider is not None

def test_import_speech_provider():
    from backend.providers.speech import SpeechProvider
    assert SpeechProvider is not None

def test_import_memory_provider():
    from backend.providers.memory import MemoryProvider
    assert MemoryProvider is not None

def test_import_browser_provider():
    from backend.providers.browser import BrowserProvider
    assert BrowserProvider is not None

def test_import_tracing_provider():
    from backend.providers.tracing import TracingProvider
    assert TracingProvider is not None
