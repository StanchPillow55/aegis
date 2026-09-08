"""Environmental context (weather / AQI)."""

from backend.environment.open_meteo import fetch_environment

__all__ = ["fetch_environment"]
