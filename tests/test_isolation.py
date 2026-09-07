import pytest
import os
import sqlite3
from fastapi.testclient import TestClient
from src.backend.main import app
from src.backend.storage.sqlite_store import _get_db_path

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_teardown():
    # Setup test DB
    os.environ["SQLITE_DB_PATH"] = "data/test_aegis.db"
    from src.backend.storage.sqlite_store import init_db
    init_db()
    yield
    # Teardown
    if os.path.exists("data/test_aegis.db"):
        os.remove("data/test_aegis.db")
    if os.path.exists("data/test_aegis.db-wal"):
        os.remove("data/test_aegis.db-wal")
    if os.path.exists("data/test_aegis.db-shm"):
        os.remove("data/test_aegis.db-shm")

from unittest.mock import patch
from src.backend.models.intake import IntakeResult, Sleep

@patch("src.backend.api.intake.extract_with_ollama")
@patch("src.backend.api.intake.store_embedding")
def test_tenant_data_isolation(mock_store, mock_extract):
    mock_extract.return_value = IntakeResult(sleep=Sleep(quality="good", hours=8))
    user1_headers = {"X-User-ID": "test_user_1"}
    user2_headers = {"X-User-ID": "test_user_2"}
    
    # User 1 adds a log
    res1 = client.post("/api/intake", data={"text": "I slept great, 8 hours."}, headers=user1_headers)
    assert res1.status_code == 200
    
    # User 2 adds a log
    res2 = client.post("/api/intake", data={"text": "Horrible night, only 4 hours."}, headers=user2_headers)
    assert res2.status_code == 200
    
    # User 1 fetches logs
    fetch1 = client.get("/api/logs", headers=user1_headers)
    assert fetch1.status_code == 200
    data1 = fetch1.json()
    assert len(data1["logs"]) == 1
    assert "slept great" in data1["logs"][0]["raw_input"]
    
    # User 2 fetches logs
    fetch2 = client.get("/api/logs", headers=user2_headers)
    assert fetch2.status_code == 200
    data2 = fetch2.json()
    assert len(data2["logs"]) == 1
    assert "Horrible night" in data2["logs"][0]["raw_input"]

@patch("src.backend.api.chat.generate_response")
@patch("src.backend.api.chat.generate_headline")
def test_chat_session_isolation(mock_headline, mock_generate):
    mock_headline.return_value = "Test Chat"
    mock_generate.return_value = "Hello"
    
    user1_headers = {"X-User-ID": "test_user_1"}
    user2_headers = {"X-User-ID": "test_user_2"}
    
    # User 1 chats
    res1 = client.post("/api/chat", data={"message": "I am user 1"}, headers=user1_headers)
    assert res1.status_code == 200
    u1_session = res1.json()["session_id"]
    
    # User 2 chats
    res2 = client.post("/api/chat", data={"message": "I am user 2"}, headers=user2_headers)
    assert res2.status_code == 200
    u2_session = res2.json()["session_id"]
    
    # User 1 gets sessions
    sessions1 = client.get("/api/chat/sessions", headers=user1_headers).json()
    assert len(sessions1) == 1
    assert sessions1[0]["id"] == u1_session
    
    # User 2 cannot get User 1's history
    # For now it will just return empty list since get_history filters by user_id
    history = client.get(f"/api/chat/sessions/{u1_session}/history", headers=user2_headers).json()
    assert len(history) == 0
