def extract_fallback(transcript: str) -> dict:
    """
    Deterministic fallback for LLM extraction.
    """
    return {"status": "ok", "mock": True}

class OllamaClient:
    """
    Skeleton for Ollama Client.
    Default model: llama3.2 (M2/16GB)
    Alternatives: qwen2.5:14b, mistral:7b
    """
    def __init__(self):
        pass

    def generate(self, prompt: str) -> str:
        """Generate response."""
        return "mock response"
