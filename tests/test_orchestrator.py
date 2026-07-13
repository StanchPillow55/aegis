import pytest
from backend.agents.orchestrator import orchestrator
from backend.intake.schema import IntakeResult, Sleep, WOD, Soreness


def test_orchestrator_process(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "mock")

    intake = IntakeResult(
        soreness=[Soreness(body_part="legs", severity=4)],
        sleep=Sleep(quality="poor", hours=4.0),
        meals=[],
        todays_wod=WOD(movements=["squats"]),
        subjective_readiness="low",
    )

    # Process the intake (stores log, retrieves context, scores, generates directive)
    directive = orchestrator.process_intake(intake)

    # The deterministic fallback directive contains the readiness score
    # Based on the scores: poor sleep + low readiness + high soreness = low score
    assert "readiness score is" in directive
    assert "Proceed with" in directive
