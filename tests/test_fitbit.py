import pytest
from datetime import date
from unittest.mock import patch, MagicMock

from src.backend.importers.fitbit import (
    rate_limiter, api_get, fetch_hrv, fetch_spo2, fetch_body_fat, fetch_body_weight
)

@pytest.mark.asyncio
async def test_rate_limiter():
    import time
    limiter = rate_limiter
    limiter.max_requests = 2
    limiter.time_window = 1
    limiter.requests = []

    start = time.time()
    await limiter.wait_if_needed() # 1st
    await limiter.wait_if_needed() # 2nd
    await limiter.wait_if_needed() # 3rd, should block for ~1 second
    end = time.time()
    
    assert end - start >= 0.9

@pytest.mark.asyncio
@patch('src.backend.importers.fitbit.httpx.AsyncClient')
async def test_api_get_graceful_missing_data(mock_client_cls):
    mock_client = mock_client_cls.return_value.__aenter__.return_value
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_client.get.return_value = mock_response

    result = await api_get("fake_token", "http://fake.url")
    assert result == {}

@pytest.mark.asyncio
@patch('src.backend.importers.fitbit.api_get')
async def test_fetchers(mock_api_get):
    mock_api_get.return_value = {"hrv": [{"value": {"dailyRmssd": 50}}]}
    
    res = await fetch_hrv("fake", date.today(), date.today())
    assert len(res) == 1
    assert res[0]["value"]["dailyRmssd"] == 50
    
    mock_api_get.return_value = {"weight": [{"weight": 180}]}
    res = await fetch_body_weight("fake", date.today(), date.today())
    assert len(res) == 1
    assert res[0]["weight"] == 180
