"""Fitbit OAuth scaffold — honest status, no fake authenticated success.

Ported from legacy-aegis fitbit importer/API. Live token exchange only runs when
FITBIT_CLIENT_ID + FITBIT_CLIENT_SECRET are set. Without credentials, status is
needs_credentials and fixture sync remains available separately.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request

from backend.config import get_settings

FITBIT_AUTH_URL = "https://www.fitbit.com/oauth2/authorize"
FITBIT_TOKEN_URL = "https://api.fitbit.com/oauth2/token"
FITBIT_API_BASE = "https://api.fitbit.com"
SCOPES = "sleep heartrate activity weight oxygen_saturation"


def _client_id() -> str:
    return (
        os.environ.get("FITBIT_CLIENT_ID")
        or os.environ.get("AEGIS_FITBIT_CLIENT_ID")
        or ""
    ).strip()


def _client_secret() -> str:
    return (
        os.environ.get("FITBIT_CLIENT_SECRET")
        or os.environ.get("AEGIS_FITBIT_CLIENT_SECRET")
        or ""
    ).strip()


def _redirect_uri() -> str:
    return (
        os.environ.get("FITBIT_REDIRECT_URI")
        or os.environ.get("AEGIS_FITBIT_REDIRECT_URI")
        or "http://127.0.0.1:8000/api/fitbit/callback"
    ).strip()


def credentials_present() -> bool:
    return bool(_client_id() and _client_secret())


def auth_url(redirect_uri: str | None = None) -> str | None:
    if not credentials_present():
        return None
    params = {
        "response_type": "code",
        "client_id": _client_id(),
        "redirect_uri": redirect_uri or _redirect_uri(),
        "scope": SCOPES,
    }
    return f"{FITBIT_AUTH_URL}?{parse.urlencode(params)}"


def _token_db() -> Path:
    settings = get_settings()
    return Path(settings.data_dir) / "aegis_oauth.sqlite3"


def _fernet():
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        return None
    # Prefer explicit key; never hardcode a shared "demo" seed as production truth
    raw = os.environ.get("AEGIS_TOKEN_KEY") or ""
    if raw:
        key = raw.encode() if len(raw) == 44 else base64.urlsafe_b64encode(hashlib.sha256(raw.encode()).digest())
    else:
        # Local-only derived key from data dir path (machine-local, not a fake auth backdoor)
        seed = str(_token_db().resolve()).encode()
        key = base64.urlsafe_b64encode(hashlib.sha256(seed).digest())
    return Fernet(key)


def _connect() -> sqlite3.Connection:
    path = _token_db()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_tokens (
            source TEXT PRIMARY KEY,
            access_token TEXT NOT NULL,
            refresh_token TEXT NOT NULL,
            expires_at REAL NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def store_token(access_token: str, refresh_token: str, expires_in: int) -> dict[str, Any]:
    f = _fernet()
    if f is None:
        return {
            "stored": False,
            "detail": "cryptography package required to store Fitbit tokens securely",
        }
    enc_a = f.encrypt(access_token.encode()).decode()
    enc_r = f.encrypt(refresh_token.encode()).decode()
    expires_at = time.time() + float(expires_in)
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO auth_tokens(source, access_token, refresh_token, expires_at) VALUES (?,?,?,?)",
            ("fitbit", enc_a, enc_r, expires_at),
        )
        conn.commit()
    return {"stored": True, "expires_at": expires_at}


def get_stored_token() -> dict[str, Any] | None:
    f = _fernet()
    if f is None:
        return None
    with _connect() as conn:
        row = conn.execute("SELECT * FROM auth_tokens WHERE source='fitbit'").fetchone()
    if not row:
        return None
    try:
        return {
            "access_token": f.decrypt(row["access_token"].encode()).decode(),
            "refresh_token": f.decrypt(row["refresh_token"].encode()).decode(),
            "expires_at": float(row["expires_at"]),
        }
    except Exception:
        return None


def status() -> dict[str, Any]:
    """Honest Fitbit connection status — never reports authenticated without a token."""
    if not credentials_present():
        return {
            "authenticated": False,
            "integration_state": "needs_credentials",
            "live_oauth": False,
            "auth_url": None,
            "detail": "Set FITBIT_CLIENT_ID and FITBIT_CLIENT_SECRET to enable OAuth. Fixture sync remains available.",
            "fixture_available": True,
        }
    token = get_stored_token()
    if not token:
        return {
            "authenticated": False,
            "integration_state": "configured",
            "live_oauth": True,
            "auth_url": auth_url(),
            "detail": "Credentials present; authorize via auth_url. Not authenticated yet.",
            "fixture_available": True,
        }
    expired = token["expires_at"] < time.time()
    return {
        "authenticated": not expired,
        "integration_state": "connected" if not expired else "token_expired",
        "live_oauth": True,
        "expires_at": datetime.fromtimestamp(token["expires_at"], tz=timezone.utc).isoformat(),
        "detail": "Live Fitbit token on disk." if not expired else "Token expired — refresh or re-auth.",
        "fixture_available": True,
    }


def exchange_code(code: str, redirect_uri: str | None = None) -> dict[str, Any]:
    if not credentials_present():
        return {"ok": False, "detail": "Fitbit OAuth not configured (missing credentials)."}
    data = parse.urlencode(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri or _redirect_uri(),
            "client_id": _client_id(),
            "client_secret": _client_secret(),
        }
    ).encode()
    req = request.Request(
        FITBIT_TOKEN_URL,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "aegis-local"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode())
    except (error.URLError, error.HTTPError, TimeoutError, OSError, ValueError) as exc:
        return {"ok": False, "detail": f"Token exchange failed: {exc}"}
    stored = store_token(
        payload["access_token"],
        payload.get("refresh_token") or "",
        int(payload.get("expires_in") or 28800),
    )
    if not stored.get("stored"):
        return {"ok": False, "detail": stored.get("detail"), "token_received": True}
    return {"ok": True, "detail": "Fitbit authorized.", "expires_at": stored.get("expires_at")}
