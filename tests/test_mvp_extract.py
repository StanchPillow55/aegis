from backend.local_llm import OllamaClient, extract_intake_with_meta


def test_mvp_extract_reports_heuristic():
    client = OllamaClient(base_url="http://127.0.0.1:9", timeout_s=0.2)
    intake, extractor = extract_intake_with_meta("Slept 8 hours well", client=client)
    assert extractor == "heuristic"
    assert intake.sleep.hours == 8
