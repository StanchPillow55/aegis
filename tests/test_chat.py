import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.backend.main import app
from src.backend.storage.sqlite_store import _get_connection

client = TestClient(app)

@patch('src.backend.api.chat.httpx.AsyncClient.post')
@pytest.mark.asyncio
def test_chat_endpoint(mock_post):
    class MockResponse:
        def raise_for_status(self):
            pass
        def json(self):
            return {"response": "Hello, how can I help you?", "message": {"content": "Hello, how can I help you?"}}
            
    mock_post.return_value = MockResponse()
    
    # 1. Post to chat
    response = client.post("/api/chat", data={"message": "Hi"}, headers={"X-User-ID": "test_user"})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["response"] == "Hello, how can I help you?"
    session_id = data["session_id"]
    
    # 2. Check history
    history_resp = client.get(f"/api/chat/sessions/{session_id}/history", headers={"X-User-ID": "test_user"})
    assert history_resp.status_code == 200, history_resp.text
    history = history_resp.json()
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Hi"
    assert history[1]["role"] == "assistant"
    assert history[1]["content"] == "Hello, how can I help you?"
