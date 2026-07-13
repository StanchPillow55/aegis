class LLMProvider:
    """Base interface for LLM operations."""
    def generate_text(self, prompt: str) -> str:
        return ""
