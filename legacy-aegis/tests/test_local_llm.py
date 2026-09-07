from backend.local_llm import extract_fallback, OllamaClient
from backend.intake.schema import IntakeResult

def test_extract_fallback():
    """Test fallback extraction logic returns schema-compliant data."""
    result = extract_fallback("test transcript")
    
    # Validate against actual schema to ensure compliance
    validated = IntakeResult(**result)
    assert validated.soreness[0].body_part == "quads"
    assert validated.sleep.quality == "good"
    assert validated.subjective_readiness == "moderate"

def test_ollama_client():
    client = OllamaClient()
    assert client.generate("test") == "mock response"
