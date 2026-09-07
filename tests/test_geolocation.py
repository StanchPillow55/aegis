import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from src.backend.main import app

client = TestClient(app)

@patch('src.backend.api.geolocation.httpx.get')
def test_geolocation_endpoint(mock_get):
    class MockResponse:
        def raise_for_status(self): pass
        def json(self):
            return {
                "current_weather": {"temperature": 22.5, "weathercode": 0},
                "current": {"us_aqi": 42}
            }
    mock_get.return_value = MockResponse()
    
    response = client.post("/api/import/geolocation", json={"latitude": 37.7749, "longitude": -122.4194})
    assert response.status_code == 200
    data = response.json()
    assert "environment" in data
    assert data["environment"]["condition"] == "Clear"
    assert data["environment"]["temperature_c"] == 22.5
    assert data["environment"]["aqi"] == 42
