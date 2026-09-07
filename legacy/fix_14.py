import os
open("backend/providers/llm.py", "w").write('''\
class LLMProvider:
    """Base interface for LLM operations."""
    def generate_text(self, prompt: str) -> str:
        return ""
''')
open("tests/test_provider_interfaces.py", "w").write('''\
from backend.providers.llm import LLMProvider
from backend.providers.speech import transcribe_audio
from backend.providers.memory import store_memory, retrieve_memory
from backend.providers.browser import fetch_page
from backend.providers.tracing import init_tracing

def test_imports() -> None:
    """Test that all providers can be imported."""
    assert callable(LLMProvider)
    assert callable(transcribe_audio)
    assert callable(store_memory)
    assert callable(retrieve_memory)
    assert callable(fetch_page)
    assert callable(init_tracing)
''')
