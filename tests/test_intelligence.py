import pytest
from unittest.mock import patch, MagicMock
from src.backend.intelligence.context_builder import build_context
from src.backend.intelligence.tools import query_metric, pop_emitted_charts, suggest_goal

def test_build_context(mocker):
    # Mock all the external calls so we just test the string building
    mocker.patch('src.backend.intelligence.context_builder.get_active_alerts', return_value=[])
    mocker.patch('src.backend.intelligence.context_builder.get_active_goals', return_value=[])
    mocker.patch('src.backend.intelligence.context_builder.get_sync_status', return_value=MagicMock(enabled=False))
    
    ctx = build_context("test_user")
    
    assert "--- SYSTEM CONTEXT ---" in ctx
    assert "ACTIVE ALERTS: None" in ctx
    assert "ACTIVE ALERTS: None" in ctx

def test_query_metric_emits_chart():
    res = query_metric("hrv", "2024-05-01", "2024-05-07")
    assert "hrv" in res
    
    charts = pop_emitted_charts()
    assert len(charts) == 1
    assert charts[0]["chart"]["metric"] == "hrv"
    
    charts2 = pop_emitted_charts()
    assert len(charts2) == 0 # Should be empty after pop

@patch('src.backend.intelligence.tools.suggest_goal_from_conversation')
def test_suggest_goal_tool(mock_suggest):
    mock_goal = MagicMock()
    mock_suggest.return_value = mock_goal
    
    res = suggest_goal("Increase HRV", "hrv", 70.0, "increase", "test_user")
    assert "Drafted goal" in res
    mock_suggest.assert_called_once()
