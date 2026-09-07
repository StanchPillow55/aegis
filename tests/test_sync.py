import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from src.backend.main import app

client = TestClient(app)

@patch('src.backend.api.sync.get_sync_status')
def test_sync_status(mock_get_status):
    mock_status = MagicMock()
    mock_status.last_sync_at = None
    mock_status.enabled = True
    mock_status.model_dump.return_value = {"enabled": True}
    mock_get_status.return_value = mock_status
    
    response = client.get("/api/sync/status")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["is_stale"] is True # True because enabled but no sync

@patch('src.backend.api.sync.update_sync_status')
@patch('src.backend.api.sync.get_sync_status')
def test_toggle_sync(mock_get_status, mock_update_status):
    mock_status = MagicMock()
    mock_status.enabled = True
    mock_get_status.return_value = mock_status
    
    response = client.post("/api/sync/toggle/fitbit?enabled=false")
    assert response.status_code == 200
    assert response.json()["enabled"] is False
