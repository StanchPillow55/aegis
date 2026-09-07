import uuid
import logging
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel

from fastapi import APIRouter

from src.backend.storage.sqlite_store import _get_connection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/import/geolocation", tags=["geolocation"])

class GeoLocation(BaseModel):
    latitude: float
    longitude: float
    
class EnvironmentalContext(BaseModel):
    temperature_c: float
    aqi: int
    condition: str

import httpx

def fetch_environmental_context(lat: float, lon: float) -> EnvironmentalContext:
    try:
        w_res = httpx.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true")
        w_res.raise_for_status()
        w_data = w_res.json()
        temp = w_data.get("current_weather", {}).get("temperature", 22.5)
        
        code = w_data.get("current_weather", {}).get("weathercode", 0)
        condition = "Clear" if code == 0 else "Cloudy" if code in (1,2,3) else "Rain/Snow"
        
        a_res = httpx.get(f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&current=us_aqi")
        a_res.raise_for_status()
        a_data = a_res.json()
        aqi = a_data.get("current", {}).get("us_aqi", 42)
        
        return EnvironmentalContext(
            temperature_c=temp,
            aqi=int(aqi),
            condition=condition
        )
    except Exception as e:
        logger.error(f"Failed to fetch environmental context: {e}")
        return EnvironmentalContext(
            temperature_c=22.5,
            aqi=42,
            condition="Unknown"
        )

@router.post("")
def update_location(loc: GeoLocation):
    # Fetch context
    env = fetch_environmental_context(loc.latitude, loc.longitude)
    
    # In a real app we might store this in a location_history table or attach to today's metrics
    conn = _get_connection()
    conn.execute(
        "CREATE TABLE IF NOT EXISTS environmental_history (id TEXT PRIMARY KEY, timestamp TEXT, lat REAL, lon REAL, temp REAL, aqi INTEGER, condition TEXT)"
    )
    conn.execute(
        "INSERT INTO environmental_history (id, timestamp, lat, lon, temp, aqi, condition) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), datetime.now(timezone.utc).isoformat(), loc.latitude, loc.longitude, env.temperature_c, env.aqi, env.condition)
    )
    conn.commit()
    conn.close()
    
    return {"status": "success", "environment": env.model_dump()}
