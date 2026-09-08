"""Connector configuration honesty — never fake live OAuth success."""

from __future__ import annotations

import os
from typing import Any

from backend.connectors import google_oauth


def fitbit_config_state() -> dict[str, Any]:
    client_id = os.environ.get("FITBIT_CLIENT_ID") or os.environ.get("AEGIS_FITBIT_CLIENT_ID")
    client_secret = os.environ.get("FITBIT_CLIENT_SECRET") or os.environ.get(
        "AEGIS_FITBIT_CLIENT_SECRET"
    )
    if client_id and client_secret:
        return {
            "integration_state": "configured",
            "live_oauth": False,
            "detail": (
                "Fitbit credentials present but Fitbit is not the primary sync path "
                "(legacy fixture only). Prefer Google Health / Takeout."
            ),
            "mode": "legacy_fixture",
            "primary": False,
        }
    return {
        "integration_state": "needs_credentials",
        "live_oauth": False,
        "detail": "Fitbit OAuth not configured. Legacy fixture sync available when source enabled.",
        "mode": "fixture_available",
        "primary": False,
    }


def calendar_config_state() -> dict[str, Any]:
    st = google_oauth.status(google_oauth.SOURCE_CALENDAR)
    return {
        "integration_state": st["integration_state"],
        "live_oauth": bool(st.get("live_oauth")),
        "authenticated": bool(st.get("authenticated")),
        "auth_url": st.get("auth_url"),
        "detail": st.get("detail"),
        "mode": st["integration_state"],
        "primary": False,
    }


def google_health_config_state() -> dict[str, Any]:
    st = google_oauth.status(google_oauth.SOURCE_HEALTH)
    return {
        "integration_state": st["integration_state"],
        "live_oauth": bool(st.get("live_oauth")),
        "authenticated": bool(st.get("authenticated")),
        "auth_url": st.get("auth_url"),
        "detail": st.get("detail"),
        "mode": st["integration_state"],
        "primary_metric_path": True,
    }


def takeout_config_state() -> dict[str, Any]:
    return {
        "integration_state": "local_upload",
        "live_oauth": False,
        "detail": (
            "Primary offline metric path: upload a Takeout ZIP via preview→confirm. "
            "Live Google Health API uses separate OAuth scaffold."
        ),
        "mode": "upload_or_fixture",
        "primary_metric_path": True,
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
        "google_health": google_health_config_state,
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
    # Never claim live OAuth connected without authenticated=true
    if payload.get("live_oauth") is True and not payload.get("authenticated"):
        # configured-but-not-authed is allowed (auth_url present); connected requires token
        if payload.get("integration_state") == "connected":
            payload["integration_state"] = "configured"
            payload["detail"] = (payload.get("detail") or "") + " (no token on disk)"
    if hasattr(payload.get("source_id"), "value"):
        payload["source_id"] = payload["source_id"].value
    return payload
