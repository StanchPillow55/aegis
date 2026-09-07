from backend.local_llm import OllamaClient, extract_fallback, extract_heuristic, extract_intake
from backend.intake.schema import IntakeResult


def test_extract_fallback():
    """Test fallback extraction logic returns schema-compliant data."""
    result = extract_fallback("test transcript")
    validated = IntakeResult(**result)
    assert validated.soreness[0].body_part == "quads"
    assert validated.sleep.quality == "good"
    assert validated.subjective_readiness == "moderate"


def test_extract_heuristic_parses_signals():
    text = (
        "Slept 6 hours poorly, quads sore 4/5, ate chicken and eggs, "
        "squats and pull-ups today, feeling tired."
    )
    data = extract_heuristic(text)
    intake = IntakeResult.model_validate(data)
    assert intake.sleep.hours == 6
    assert intake.sleep.quality == "poor"
    assert any(s.body_part == "quads" for s in intake.soreness)
    assert any(m.description == "chicken" for m in intake.meals)
    assert "squats" in intake.todays_wod.movements
    assert intake.subjective_readiness == "low"


def test_ollama_client_availability_and_offline_generate():
    client = OllamaClient(base_url="http://127.0.0.1:9", timeout_s=0.2)
    assert client.available() is False
    try:
        client.generate("test")
        raised = False
    except RuntimeError:
        raised = True
    assert raised is True


def test_extract_intake_without_ollama():
    client = OllamaClient(base_url="http://127.0.0.1:9", timeout_s=0.2)
    intake = extract_intake("good sleep 8 hours, feeling fresh, deadlift day", client=client)
    assert isinstance(intake, IntakeResult)
    assert intake.sleep.hours == 8
