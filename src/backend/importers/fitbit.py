"""Fitbit Web API importer.

OAuth2 flow:
1. User visits /api/import/fitbit/auth -> redirect to Fitbit authorization
2. Fitbit redirects back with code -> /api/import/fitbit/callback
3. We exchange code for access token, store it
4. Pull historical data: sleep, heart rate, activities

Fitbit API docs: https://dev.fitbit.com/build/reference/web-api/

Requires FITBIT_CLIENT_ID and FITBIT_CLIENT_SECRET in .env.
Register app at https://dev.fitbit.com/apps/new (set type to "Personal")
"""

from datetime import date, timedelta
from typing import Optional

import httpx

from src.backend.config import get_settings

FITBIT_AUTH_URL = "https://www.fitbit.com/oauth2/authorize"
FITBIT_TOKEN_URL = "https://api.fitbit.com/oauth2/token"
FITBIT_API_BASE = "https://api.fitbit.com"

# Scopes we need
SCOPES = "sleep heartrate activity"


def get_auth_url(redirect_uri: str) -> Optional[str]:
    """Generate Fitbit OAuth authorization URL."""
    settings = get_settings()
    if not settings.fitbit_client_id:
        return None

    params = {
        "response_type": "code",
        "client_id": settings.fitbit_client_id,
        "redirect_uri": redirect_uri,
        "scope": SCOPES,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{FITBIT_AUTH_URL}?{query}"


async def exchange_code(code: str, redirect_uri: str) -> dict:
    """Exchange authorization code for access token."""
    settings = get_settings()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            FITBIT_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": settings.fitbit_client_id,
                "client_secret": settings.fitbit_client_secret,
            },
        )
        response.raise_for_status()
        return response.json()

async def refresh_token(refresh_token: str) -> dict:
    """Refresh the access token."""
    settings = get_settings()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            FITBIT_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": settings.fitbit_client_id,
                "client_secret": settings.fitbit_client_secret,
            },
        )
        response.raise_for_status()
        return response.json()


async def fetch_sleep_data(access_token: str, start: date, end: date) -> list[dict]:
    """Fetch sleep data from Fitbit API."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{FITBIT_API_BASE}/1.2/user/-/sleep/date/{start.isoformat()}/{end.isoformat()}.json",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        data = response.json()
        return data.get("sleep", [])


async def fetch_heart_rate(access_token: str, day: date) -> dict:
    """Fetch intraday heart rate for a specific day."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{FITBIT_API_BASE}/1/user/-/activities/heart/date/{day.isoformat()}/1d/1min.json",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return response.json()


async def fetch_activities(access_token: str, start: date, end: date) -> list[dict]:
    """Fetch activity/exercise logs."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{FITBIT_API_BASE}/1/user/-/activities/list.json",
            params={"afterDate": start.isoformat(), "sort": "asc", "limit": 100, "offset": 0},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        data = response.json()
        return data.get("activities", [])

import logging
import asyncio
import uuid
from datetime import datetime, timezone
from src.backend.models.health_metrics import HealthMetric, MetricType, DataSource
from src.backend.storage.sqlite_store import _get_connection

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self, max_requests: int = 150, time_window: int = 3600):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
        
    async def wait_if_needed(self):
        now = datetime.now(timezone.utc).timestamp()
        # Remove requests older than time_window
        self.requests = [req for req in self.requests if req > now - self.time_window]
        
        if len(self.requests) >= self.max_requests:
            sleep_time = (self.requests[0] + self.time_window) - now
            if sleep_time > 0:
                logger.info(f"Rate limit reached. Sleeping for {sleep_time} seconds.")
                await asyncio.sleep(sleep_time)
                
        self.requests.append(datetime.now(timezone.utc).timestamp())

rate_limiter = RateLimiter()

async def api_get(access_token: str, url: str) -> dict:
    await rate_limiter.wait_if_needed()
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if response.status_code == 404 or response.status_code == 400:
            # Missing data gracefully skipped
            return {}
        response.raise_for_status()
        return response.json()

async def fetch_hrv(access_token: str, start: date, end: date) -> list[dict]:
    data = await api_get(access_token, f"{FITBIT_API_BASE}/1/user/-/hrv/date/{start.isoformat()}/{end.isoformat()}.json")
    return data.get("hrv", [])

async def fetch_spo2(access_token: str, start: date, end: date) -> list[dict]:
    data = await api_get(access_token, f"{FITBIT_API_BASE}/1/user/-/spo2/date/{start.isoformat()}/{end.isoformat()}.json")
    return data if isinstance(data, list) else []

async def fetch_body_fat(access_token: str, start: date, end: date) -> list[dict]:
    data = await api_get(access_token, f"{FITBIT_API_BASE}/1/user/-/body/log/fat/date/{start.isoformat()}/{end.isoformat()}.json")
    return data.get("fat", [])

async def fetch_body_weight(access_token: str, start: date, end: date) -> list[dict]:
    data = await api_get(access_token, f"{FITBIT_API_BASE}/1/user/-/body/log/weight/date/{start.isoformat()}/{end.isoformat()}.json")
    return data.get("weight", [])

async def pull_all_data(access_token: str, user_id: str = "test_user_1"):
    logger.info("Starting Fitbit pull_all_data")
    end = date.today()
    start = end - timedelta(days=7) # Pull last 7 days for now
    
    try:
        # Sleep
        sleep_data = await fetch_sleep_data(access_token, start, end)
        # HRV
        hrv_data = await fetch_hrv(access_token, start, end)
        # Weight
        weight_data = await fetch_body_weight(access_token, start, end)
        
        # Save to DB
        conn = _get_connection()
        
        for s in sleep_data:
            dt_str = s.get("endTime") or s.get("dateOfSleep")
            if dt_str:
                if "T" in dt_str:
                    dt = datetime.strptime(dt_str[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
                else:
                    dt = datetime.strptime(dt_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    
                val = s.get("minutesAsleep")
                if val is None and s.get("duration"):
                    val = s.get("duration") / 60000.0
                    
                if val:
                    conn.execute("INSERT OR REPLACE INTO health_metrics (id, user_id, timestamp, metric_type, value, unit, source, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), user_id, dt.isoformat(), MetricType.sleep_duration.value, float(val), "minutes", DataSource.fitbit.value, "{}"))
        for hr in hrv_data:
            dt = datetime.strptime(hr["dateTime"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            val = hr["value"].get("dailyRmssd")
            if val:
                conn.execute("INSERT OR REPLACE INTO health_metrics (id, user_id, timestamp, metric_type, value, unit, source, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), user_id, dt.isoformat(), MetricType.hrv.value, float(val), "ms", DataSource.fitbit.value, "{}"))
                
        for w in weight_data:
            dt = datetime.strptime(w["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            conn.execute("INSERT OR REPLACE INTO health_metrics (id, user_id, timestamp, metric_type, value, unit, source, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), user_id, dt.isoformat(), MetricType.weight.value, float(w["weight"]), "lbs", DataSource.fitbit.value, "{}"))
            
        conn.commit()
        conn.close()
        logger.info("Fitbit data pull completed successfully.")
        
    except Exception as e:
        logger.exception(f"Failed pulling fitbit data: {e}")
