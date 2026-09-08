"""Connector configuration honesty — never fake live OAuth success."""

from __future__ import annotations

import os
from typing import Any


def fitbit_config_state() -> dict[str, Any]:
    client_id = os.environ.get("FITBIT_CLIENT_ID") or os.environ.get("AEGIS_FITBIT_CLIENT_ID")
    client_secret = os.environ.get("FITBIT_CLIENT_SECRET") or os.environ.get(
        "AEGIS_FITBIT_CLIENT_SECRET"
    )
    if client_id and client_secret:
        return {
            "integration_state": "configured",
            "live_oauth": False,
            "detail": "Credentials present but live OAuth adapter not enabled in this build; use fixture sync.",
            "mode": "needs_adapter",
        }
    return {
        "integration_state": "needs_credentials",
        "live_oauth": False,
        "detail": "Fitbit OAuth not configured. Fixture sync available when source enabled.",
        "mode": "fixture_available",
    }


def calendar_config_state() -> dict[str, Any]:
    token = os.environ.get("GOOGLE_CALENDAR_TOKEN") or os.environ.get("AEGIS_CALENDAR_TOKEN")
    if token:
        return {
            "integration_state": "configured",
            "live_oauth": False,
            "detail": "Token present but live Calendar adapter not enabled; use fixture sync.",
            "mode": "needs_adapter",
        }
    return {
        "integration_state": "needs_credentials",
        "live_oauth": False,
        "detail": "Google Calendar not configured. Fixture sync available when source enabled.",
        "mode": "fixture_available",
    }


def takeout_config_state() -> dict[str, Any]:
    return {
        "integration_state": "local_upload",
        "live_oauth": False,
        "detail": "Upload a Takeout ZIP via /api/takeout/zip; fixture sync also available.",
        "mode": "upload_or_fixture",
    }


def weather_config_state() -> dict[str, Any]:
    flag = (os.environ.get("AEGIS_WEATHER") or "auto").strip().lower()
    if flag in {"0", "off", "disabled", "false"}:
        return {
            "integration_state": "disabled",
            "live_oauth": False,
            "detail": "Weather disabled via AEGIS_WEATHER.",
            "mode": "disabled",
        }
    return {
        "integration_state": "optional_network",
        "live_oauth": False,
        "detail": "Open-Meteo attempted on demand; offline fixture if network fails.",
        "mode": "live_or_offline",
    }


def enrich_source_status(payload: dict[str, Any]) -> dict[str, Any]:
    """Attach honest integration_state to a source status dump."""
    sid = payload.get("source_id")
    if isinstance(sid, dict):
        sid = sid.get("value")
    elif hasattr(sid, "value"):
        sid = sid.value
    sid = str(sid or "")
    mapping = {
        "fitbit": fitbit_config_state,
        "calendar": calendar_config_state,
        "takeout": takeout_config_state,
        "weather": weather_config_state,
    }
    if sid in mapping:
        payload = {**payload, **mapping[sid]()}
    elif sid in {"manual", "fixture", "fitindex"}:
        payload = {
            **payload,
            "integration_state": "local",
            "live_oauth": False,
            "mode": "local",
            "detail": "Local source — no OAuth.",
        }
    else:
        payload.setdefault("integration_state", "unknown")
    # Never claim live OAuth connected
    if payload.get("live_oauth") is True and sid in {"fitbit", "calendar"}:
        payload["live_oauth"] = False
        payload["detail"] = (payload.get("detail") or "") + " (forced: no fake OAuth)"
    # Normalize enum source_id for JSON clients
    if hasattr(payload.get("source_id"), "value"):
        payload["source_id"] = payload["source_id"].value
    return payload
