"""Open-Meteo weather + AQI client with honest live|offline|disabled modes.

No API key required. Network failures never pretend to be live success.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any
from urllib import error, request

# San Francisco default when geo is disabled (privacy default-off)
_DEFAULT_LAT = 37.7749
_DEFAULT_LON = -122.4194
_TIMEOUT_S = 4.0

_OFFLINE_FIXTURE = {
    "temp_c": 18.0,
    "conditions": "partly_cloudy",
    "wind_kmh": 12.0,
    "us_aqi": 42,
    "aqi_category": "Good",
}


def _aqi_category(us_aqi: int | None) -> str:
    if us_aqi is None:
        return "unknown"
    if us_aqi <= 50:
        return "Good"
    if us_aqi <= 100:
        return "Moderate"
    if us_aqi <= 150:
        return "Unhealthy for Sensitive Groups"
    if us_aqi <= 200:
        return "Unhealthy"
    if us_aqi <= 300:
        return "Very Unhealthy"
    return "Hazardous"


def _http_json(url: str) -> dict[str, Any]:
    req = request.Request(url, headers={"User-Agent": "aegis-local/0.5"})
    with request.urlopen(req, timeout=_TIMEOUT_S) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_environment(
    *,
    lat: float | None = None,
    lon: float | None = None,
    force_offline: bool | None = None,
) -> dict[str, Any]:
    """Return weather/AQI payload with explicit mode labeling.

    Modes:
    - live: network fetch succeeded
    - offline: live attempted or forced off; fixture returned and labeled
    - disabled: env var AEGIS_WEATHER=disabled
    """
    flag = (os.environ.get("AEGIS_WEATHER") or "auto").strip().lower()
    if flag in {"0", "off", "disabled", "false"}:
        return {
            "ok": False,
            "mode": "disabled",
            "weather": None,
            "aqi": None,
            "detail": "Weather/AQI disabled via AEGIS_WEATHER.",
            "fetched_at": time.time(),
            "source": "none",
        }

    if force_offline is None:
        force_offline = flag in {"offline", "fixture"}

    latitude = lat if lat is not None else _DEFAULT_LAT
    longitude = lon if lon is not None else _DEFAULT_LON

    if force_offline:
        return {
            "ok": True,
            "mode": "offline",
            "weather": {
                "temp_c": _OFFLINE_FIXTURE["temp_c"],
                "conditions": _OFFLINE_FIXTURE["conditions"],
                "wind_kmh": _OFFLINE_FIXTURE["wind_kmh"],
            },
            "aqi": {
                "us_aqi": _OFFLINE_FIXTURE["us_aqi"],
                "category": _OFFLINE_FIXTURE["aqi_category"],
            },
            "detail": "Offline fixture — live Open-Meteo not requested.",
            "fetched_at": time.time(),
            "source": "fixture",
            "location": {"lat": latitude, "lon": longitude, "precision": "city_default"},
        }

    weather_url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitude}&longitude={longitude}"
        "&current=temperature_2m,weather_code,wind_speed_10m"
    )
    aqi_url = (
        "https://air-quality-api.open-meteo.com/v1/air-quality"
        f"?latitude={latitude}&longitude={longitude}&current=us_aqi"
    )

    try:
        weather_raw = _http_json(weather_url)
        aqi_raw = _http_json(aqi_url)
        current = weather_raw.get("current") or {}
        aqi_current = aqi_raw.get("current") or {}
        us_aqi = aqi_current.get("us_aqi")
        us_aqi_i = int(us_aqi) if us_aqi is not None else None
        return {
            "ok": True,
            "mode": "live",
            "weather": {
                "temp_c": current.get("temperature_2m"),
                "conditions": f"wmo_{current.get('weather_code')}",
                "wind_kmh": current.get("wind_speed_10m"),
            },
            "aqi": {
                "us_aqi": us_aqi_i,
                "category": _aqi_category(us_aqi_i),
            },
            "detail": "Live Open-Meteo weather + AQI.",
            "fetched_at": time.time(),
            "source": "open-meteo",
            "location": {"lat": latitude, "lon": longitude, "precision": "city_default"},
        }
    except (error.URLError, error.HTTPError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            "ok": True,
            "mode": "offline",
            "weather": {
                "temp_c": _OFFLINE_FIXTURE["temp_c"],
                "conditions": _OFFLINE_FIXTURE["conditions"],
                "wind_kmh": _OFFLINE_FIXTURE["wind_kmh"],
            },
            "aqi": {
                "us_aqi": _OFFLINE_FIXTURE["us_aqi"],
                "category": _OFFLINE_FIXTURE["aqi_category"],
            },
            "detail": f"Offline fixture — live Open-Meteo unavailable ({type(exc).__name__}: {exc}).",
            "fetched_at": time.time(),
            "source": "fixture",
            "location": {"lat": latitude, "lon": longitude, "precision": "city_default"},
            "error": str(exc),
        }
