"""Shared encrypted OAuth token store (local SQLite + Fernet).

Used by Google Calendar / Google Health scaffolds and Fitbit legacy.
Never claims authentication without a decryptable stored token.
"""

from __future__ import annotations

import base64
import hashlib
import os
import sqlite3
import time
from pathlib import Path
from typing import Any


def token_db_path() -> Path:
    from backend.config import get_settings

    return Path(get_settings().data_dir) / "aegis_oauth.sqlite3"


def fernet():
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        return None
    raw = os.environ.get("AEGIS_TOKEN_KEY") or ""
    if raw:
        key = (
            raw.encode()
            if len(raw) == 44
            else base64.urlsafe_b64encode(hashlib.sha256(raw.encode()).digest())
        )
    else:
        seed = str(token_db_path().resolve()).encode()
        key = base64.urlsafe_b64encode(hashlib.sha256(seed).digest())
    return Fernet(key)


def _connect() -> sqlite3.Connection:
    path = token_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_tokens (
            source TEXT PRIMARY KEY,
            access_token TEXT NOT NULL,
            refresh_token TEXT NOT NULL,
            expires_at REAL NOT NULL,
            scopes TEXT,
            meta_json TEXT
        )
        """
    )
    # Older Fitbit rows may lack scopes/meta — ignore if columns already exist
    cols = {r[1] for r in conn.execute("PRAGMA table_info(auth_tokens)").fetchall()}
    if "scopes" not in cols:
        conn.execute("ALTER TABLE auth_tokens ADD COLUMN scopes TEXT")
    if "meta_json" not in cols:
        conn.execute("ALTER TABLE auth_tokens ADD COLUMN meta_json TEXT")
    conn.commit()
    return conn


def store_token(
    source: str,
    access_token: str,
    refresh_token: str,
    expires_in: int,
    *,
    scopes: str | None = None,
) -> dict[str, Any]:
    f = fernet()
    if f is None:
        return {
            "stored": False,
            "detail": "cryptography package required to store OAuth tokens securely",
        }
    enc_a = f.encrypt(access_token.encode()).decode()
    enc_r = f.encrypt((refresh_token or "").encode()).decode()
    expires_at = time.time() + float(expires_in)
    with _connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO auth_tokens(
                source, access_token, refresh_token, expires_at, scopes, meta_json
            ) VALUES (?,?,?,?,?,?)
            """,
            (source, enc_a, enc_r, expires_at, scopes, None),
        )
        conn.commit()
    return {"stored": True, "expires_at": expires_at, "source": source}


def get_token(source: str) -> dict[str, Any] | None:
    f = fernet()
    if f is None:
        return None
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM auth_tokens WHERE source=?", (source,)
        ).fetchone()
    if not row:
        return None
    try:
        return {
            "access_token": f.decrypt(row["access_token"].encode()).decode(),
            "refresh_token": f.decrypt(row["refresh_token"].encode()).decode(),
            "expires_at": float(row["expires_at"]),
            "scopes": row["scopes"],
            "expired": float(row["expires_at"]) < time.time(),
        }
    except Exception:
        return None


def clear_token(source: str) -> dict[str, Any]:
    with _connect() as conn:
        conn.execute("DELETE FROM auth_tokens WHERE source=?", (source,))
        conn.commit()
    return {"cleared": True, "source": source}


def has_usable_token(source: str) -> bool:
    tok = get_token(source)
    return bool(tok and not tok.get("expired"))
