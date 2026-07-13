def extract_fallback(transcript: str) -> dict:
    """
    Deterministic fallback for LLM extraction.
    Matches IntakeResult schema keys exactly.
    """
    return {
        "soreness": [{"body_part": "quads", "severity": 2}],
        "sleep": {"quality": "good", "hours": 8.0},
        "meals": [{"description": "chicken", "protein_g": 30}],
        "todays_wod": {"movements": ["squats"], "raw": "squat day"},
        "subjective_readiness": "moderate"
    }

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
