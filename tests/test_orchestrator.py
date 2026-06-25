"""Integration test for orchestrator uAgent (SC-FETCH-01)."""

from unittest.mock import MagicMock, patch

import pytest
from uagents import Model

from backend.agents.orchestrator import AgentDirective, ProcessIntake, handle_intake
from backend.intake.schema import IntakeResult, Sleep, WOD


class MockContext:
    def __init__(self):
        self.logger = MagicMock()
        self.sent_messages = []

    async def send(self, destination: str, message: Model):
        self.sent_messages.append((destination, message))


@pytest.fixture
def sample_intake():
    return IntakeResult(
        soreness=[],
        sleep=Sleep(quality="good", hours=8),
        meals=[],
        todays_wod=WOD(movements=["pull-ups"]),
        subjective_readiness="high"
    )


@pytest.mark.asyncio
@patch("backend.agents.orchestrator.score_all")
@patch("backend.agents.orchestrator.search_similar")
@patch("backend.agents.orchestrator.store_log")
async def test_orchestrator_pipeline(mock_store_log, mock_search_similar, mock_score_all, sample_intake):
    # Setup mocks
    mock_store_log.return_value = "fake_log_id"
    mock_search_similar.return_value = []
    mock_score_all.return_value = {"readiness": {"score": 85}}

    ctx = MockContext()
    msg = ProcessIntake(intake_dict=sample_intake.model_dump())

    # Execute the handler
    await handle_intake(ctx, "test_sender", msg)

    # Verify interactions
    mock_store_log.assert_called_once()
    mock_search_similar.assert_called_once()
    mock_score_all.assert_called_once_with(sample_intake)

    # Verify response
    assert len(ctx.sent_messages) == 1
    dest, response_msg = ctx.sent_messages[0]
    assert dest == "test_sender"
    assert isinstance(response_msg, AgentDirective)
    assert "readiness score is 85/100" in response_msg.directive
    assert "full training session" in response_msg.directive
