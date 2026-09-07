import os
os.makedirs("backend/providers", exist_ok=True)
os.makedirs("tests", exist_ok=True)
open("backend/providers/llm.py", "w").write('def generate_text(prompt: str) -> str:\n    """Generate text from local LLM."""\n    return ""\n')
open("backend/providers/speech.py", "w").write('def transcribe_audio(file_path: str) -> str:\n    """Transcribe audio using local model."""\n    return ""\n')
open("backend/providers/memory.py", "w").write('def store_memory(data: dict) -> None:\n    """Store memory in local DB."""\n    pass\n\ndef retrieve_memory(query: str) -> list:\n    """Retrieve memory from local DB."""\n    return []\n')
open("backend/providers/browser.py", "w").write('def fetch_page(url: str) -> str:\n    """Fetch page using Playwright."""\n    return ""\n')
open("backend/providers/tracing.py", "w").write('def init_tracing() -> None:\n    """Initialize local OpenTelemetry tracing."""\n    pass\n')
open("tests/test_provider_interfaces.py", "w").write('from backend.providers.llm import generate_text\nfrom backend.providers.speech import transcribe_audio\nfrom backend.providers.memory import store_memory, retrieve_memory\nfrom backend.providers.browser import fetch_page\nfrom backend.providers.tracing import init_tracing\n\ndef test_imports() -> None:\n    """Test that all providers can be imported."""\n    assert callable(generate_text)\n    assert callable(transcribe_audio)\n    assert callable(store_memory)\n    assert callable(retrieve_memory)\n    assert callable(fetch_page)\n    assert callable(init_tracing)\n')
