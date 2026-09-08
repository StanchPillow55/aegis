"""Google OAuth scaffolding for Calendar + Health (Fit) — up to secrets boundary.

Without GOOGLE_CLIENT_ID + GOOGLE_CLIENT_SECRET:
  integration_state=needs_credentials, never authenticated.

With credentials but no token:
  auth_url available; exchange_code stores encrypted tokens locally.

Never fakes OAuth success. Live Calendar/Health pulls only run with a real token.
Fitbit remains legacy/not-primary (see docs/CONNECTORS.md).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any
from urllib import error, parse, request

from backend.connectors import token_store

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

SOURCE_CALENDAR = "google_calendar"
SOURCE_HEALTH = "google_health"

CALENDAR_SCOPES = "https://www.googleapis.com/auth/calendar.readonly"
HEALTH_SCOPES = " ".join(
    [
        "https://www.googleapis.com/auth/fitness.activity.read",
        "https://www.googleapis.com/auth/fitness.heart_rate.read",
        "https://www.googleapis.com/auth/fitness.sleep.read",
        "https://www.googleapis.com/auth/fitness.body.read",
    ]
)


def _client_id() -> str:
    return (
        os.environ.get("GOOGLE_CLIENT_ID")
        or os.environ.get("AEGIS_GOOGLE_CLIENT_ID")
        or ""
    ).strip()


def _client_secret() -> str:
    return (
        os.environ.get("GOOGLE_CLIENT_SECRET")
        or os.environ.get("AEGIS_GOOGLE_CLIENT_SECRET")
        or ""
    ).strip()


def credentials_present() -> bool:
    return bool(_client_id() and _client_secret())


def redirect_uri_for(source: str) -> str:
    if source == SOURCE_CALENDAR:
        return (
            os.environ.get("GOOGLE_CALENDAR_REDIRECT_URI")
            or os.environ.get("AEGIS_GOOGLE_CALENDAR_REDIRECT_URI")
            or "http://127.0.0.1:8000/api/google/calendar/callback"
        ).strip()
    return (
        os.environ.get("GOOGLE_HEALTH_REDIRECT_URI")
        or os.environ.get("AEGIS_GOOGLE_HEALTH_REDIRECT_URI")
        or "http://127.0.0.1:8000/api/google/health/callback"
    ).strip()


def scopes_for(source: str) -> str:
    return CALENDAR_SCOPES if source == SOURCE_CALENDAR else HEALTH_SCOPES


def auth_url(source: str, redirect_uri: str | None = None) -> str | None:
    if not credentials_present():
        return None
    if source not in {SOURCE_CALENDAR, SOURCE_HEALTH}:
        return None
    params = {
        "response_type": "code",
        "client_id": _client_id(),
        "redirect_uri": redirect_uri or redirect_uri_for(source),
        "scope": scopes_for(source),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
    }
    return f"{GOOGLE_AUTH_URL}?{parse.urlencode(params)}"


def status(source: str) -> dict[str, Any]:
    """Honest Google connector status for calendar or health."""
    label = "Google Calendar" if source == SOURCE_CALENDAR else "Google Health / Fit API"
    primary = source == SOURCE_HEALTH
    if not credentials_present():
        return {
            "source": source,
            "label": label,
            "authenticated": False,
            "integration_state": "needs_credentials",
            "live_oauth": False,
            "primary_metric_path": primary,
            "auth_url": None,
            "scopes": scopes_for(source),
            "detail": (
                f"Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to enable {label} OAuth. "
                + (
                    "Takeout ZIP remains the primary offline metric path."
                    if primary
                    else "Fixture calendar events remain available."
                )
            ),
            "fixture_available": True,
        }
    token = token_store.get_token(source)
    url = auth_url(source)
    if not token:
        return {
            "source": source,
            "label": label,
            "authenticated": False,
            "integration_state": "configured",
            "live_oauth": True,
            "primary_metric_path": primary,
            "auth_url": url,
            "scopes": scopes_for(source),
            "detail": f"Credentials present; authorize via auth_url. Not authenticated yet.",
            "fixture_available": True,
        }
    expired = bool(token.get("expired"))
    return {
        "source": source,
        "label": label,
        "authenticated": not expired,
        "integration_state": "connected" if not expired else "token_expired",
        "live_oauth": True,
        "primary_metric_path": primary,
        "auth_url": url if expired else None,
        "scopes": token.get("scopes") or scopes_for(source),
        "expires_at": datetime.fromtimestamp(
            token["expires_at"], tz=timezone.utc
        ).isoformat(),
        "detail": (
            f"Live {label} token on disk."
            if not expired
            else "Token expired — re-authorize."
        ),
        "fixture_available": True,
    }


def exchange_code(
    source: str, code: str, redirect_uri: str | None = None
) -> dict[str, Any]:
    if source not in {SOURCE_CALENDAR, SOURCE_HEALTH}:
        return {"ok": False, "detail": f"Unknown Google source: {source}"}
    if not credentials_present():
        return {"ok": False, "detail": "Google OAuth not configured (missing credentials)."}
    if not code.strip():
        return {"ok": False, "detail": "Authorization code required."}
    data = parse.urlencode(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri or redirect_uri_for(source),
            "client_id": _client_id(),
            "client_secret": _client_secret(),
        }
    ).encode()
    req = request.Request(
        GOOGLE_TOKEN_URL,
        data=data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "aegis-local",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode())
    except (error.URLError, error.HTTPError, TimeoutError, OSError, ValueError) as exc:
        return {"ok": False, "detail": f"Token exchange failed: {exc}"}
    stored = token_store.store_token(
        source,
        payload["access_token"],
        payload.get("refresh_token") or "",
        int(payload.get("expires_in") or 3600),
        scopes=payload.get("scope") or scopes_for(source),
    )
    if not stored.get("stored"):
        return {"ok": False, "detail": stored.get("detail"), "token_received": True}
    return {
        "ok": True,
        "source": source,
        "detail": f"{source} authorized.",
        "expires_at": stored.get("expires_at"),
    }


def revoke(source: str) -> dict[str, Any]:
    return token_store.clear_token(source)


def calendar_events_live(*, max_results: int = 10) -> dict[str, Any]:
    """Fetch upcoming events when a live Calendar token exists (read-only)."""
    tok = token_store.get_token(SOURCE_CALENDAR)
    if not tok or tok.get("expired"):
        return {
            "ok": False,
            "mode": "needs_token",
            "events": [],
            "detail": "No usable Google Calendar token — authorize or use fixture sync.",
        }
    params = parse.urlencode(
        {
            "maxResults": max(1, min(max_results, 50)),
            "singleEvents": "true",
            "orderBy": "startTime",
            "timeMin": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
    )
    url = f"https://www.googleapis.com/calendar/v3/calendars/primary/events?{params}"
    req = request.Request(
        url,
        headers={
            "Authorization": f"Bearer {tok['access_token']}",
            "User-Agent": "aegis-local",
        },
        method="GET",
    )
    try:
        with request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode())
    except (error.URLError, error.HTTPError, TimeoutError, OSError, ValueError) as exc:
        return {"ok": False, "mode": "error", "events": [], "detail": str(exc)}
    events = []
    for item in payload.get("items") or []:
        start = (item.get("start") or {}).get("dateTime") or (item.get("start") or {}).get(
            "date"
        )
        end = (item.get("end") or {}).get("dateTime") or (item.get("end") or {}).get("date")
        events.append(
            {
                "name": item.get("summary") or "(untitled)",
                "location": item.get("location"),
                "description": item.get("description"),
                "start": start,
                "end": end,
            }
        )
    return {
        "ok": True,
        "mode": "live",
        "events": events,
        "count": len(events),
        "write_access": False,
        "detail": "Live Google Calendar read-only pull.",
    }


def health_pull_scaffold() -> dict[str, Any]:
    """Honest Health API gate — no silent fake metrics without a token."""
    st = status(SOURCE_HEALTH)
    if st["integration_state"] == "needs_credentials":
        return {
            "ok": False,
            "mode": "needs_credentials",
            "metrics": [],
            "detail": st["detail"],
            "fallback": "use_takeout_zip",
        }
    if not st.get("authenticated"):
        return {
            "ok": False,
            "mode": "needs_token",
            "metrics": [],
            "auth_url": st.get("auth_url"),
            "detail": st["detail"],
            "fallback": "use_takeout_zip",
        }
    # Token present: scaffold acknowledges readiness but defers dataset mapping
    # to a follow-up slice once operator verifies live Fitness API access.
    return {
        "ok": True,
        "mode": "token_ready",
        "metrics": [],
        "detail": (
            "Google Health token present. Live Fitness dataset mapping is scaffolded; "
            "use Takeout ZIP for bulk import until dataset sync is enabled."
        ),
        "fallback": "takeout_still_primary_for_bulk",
    }
