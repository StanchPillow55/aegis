from backend.local_llm import extract_fallback, OllamaClient

def test_extract_fallback():
    result = extract_fallback("test transcript")
    assert result["mock"] is True
    assert result["status"] == "ok"

def test_ollama_client():
    client = OllamaClient()
    assert client.generate("test prompt") == "mock response"
