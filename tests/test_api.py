"""Test FastAPI endpoints."""

import os

import pytest
from fastapi.testclient import TestClient

# Use in-memory SQLite for tests
os.environ.setdefault("SQLITE_DB_PATH", ":memory:")

from src.backend.main import app
from src.backend.storage.sqlite_store import init_db

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_logs_empty():
    response = client.get("/api/logs?days=7", headers={"X-User-ID": "test_user"})
    assert response.status_code == 200
    data = response.json()
    assert "logs" in data
    assert data["count"] == 0


def test_directive_no_data():
    response = client.get("/api/directive")
    assert response.status_code == 200
    data = response.json()
    assert data["has_data"] is False
