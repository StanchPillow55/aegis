import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from src.backend.config import get_settings
from src.backend.importers import fitbit
from src.backend.storage.sqlite_store import _get_connection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/import/fitbit", tags=["fitbit"])

# We should use Fernet in production to encrypt tokens.
# For simplicity in this implementation, we will just store them.
# The user specified: Persist tokens in SQLite (encrypted with Fernet using a local key derived from machine ID)

from cryptography.fernet import Fernet
import uuid
import base64
import hashlib

def _get_encryption_key() -> bytes:
    # In a real app we'd use a stable machine ID. We'll derive a 32-urlsafe-b64 key from an env variable or static string.
    # For now, just use a hardcoded seed for the demo.
    seed = b"aegis_local_machine_key_seed"
    key = hashlib.sha256(seed).digest()
    return base64.urlsafe_b64encode(key)

fernet = Fernet(_get_encryption_key())

def store_token(source: str, access_token: str, refresh_token: str, expires_in: int):
    conn = _get_connection()
    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat()
    
    enc_access = fernet.encrypt(access_token.encode()).decode()
    enc_refresh = fernet.encrypt(refresh_token.encode()).decode()
    
    conn.execute("""
        INSERT OR REPLACE INTO auth_tokens (source, access_token, refresh_token, expires_at)
        VALUES (?, ?, ?, ?)
    """, (source, enc_access, enc_refresh, expires_at))
    conn.commit()
    conn.close()

def get_token(source: str) -> Optional[dict]:
    conn = _get_connection()
    row = conn.execute("SELECT * FROM auth_tokens WHERE source = ?", (source,)).fetchone()
    conn.close()
    
    if not row:
        return None
        
    access_token = fernet.decrypt(row["access_token"].encode()).decode()
    refresh_token = fernet.decrypt(row["refresh_token"].encode()).decode()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": datetime.fromisoformat(row["expires_at"])
    }

from fastapi.responses import RedirectResponse

@router.get("/auth")
def auth(redirect_uri: Optional[str] = None):
    """Get auth URL for Fitbit."""
    url = fitbit.get_auth_url(redirect_uri)
    if not url:
        raise HTTPException(status_code=400, detail="Fitbit OAuth is not configured. Missing FITBIT_CLIENT_ID.")
    return RedirectResponse(url)

@router.get("/callback")
async def callback(code: str, redirect_uri: Optional[str] = None):
    """Handle Fitbit OAuth callback."""
    try:
        data = await fitbit.exchange_code(code, redirect_uri)
        store_token("fitbit", data["access_token"], data["refresh_token"], data["expires_in"])
        # Redirect back to the app on success
        return RedirectResponse(redirect_uri or "http://localhost:5173")
    except Exception as e:
        logger.exception("Failed to exchange Fitbit code")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/sync")
async def sync_fitbit(background_tasks: BackgroundTasks):
    """Trigger a manual sync of Fitbit data."""
    token_data = get_token("fitbit")
    if not token_data:
        raise HTTPException(status_code=401, detail="Fitbit not authenticated")
        
    # Check if expired, if so refresh
    if token_data["expires_at"] < datetime.now(timezone.utc):
        # We need a refresh_token function in fitbit.py
        try:
            new_data = await fitbit.refresh_token(token_data["refresh_token"])
            store_token("fitbit", new_data["access_token"], new_data["refresh_token"], new_data["expires_in"])
            token_data["access_token"] = new_data["access_token"]
        except Exception as e:
            logger.exception("Failed to refresh token")
            raise HTTPException(status_code=401, detail="Fitbit token refresh failed, re-authenticate")
            
    # Trigger background pull
    background_tasks.add_task(fitbit.pull_all_data, token_data["access_token"])
    return {"status": "sync_started"}

@router.get("/status")
def status():
    """Get Fitbit authentication status."""
    token = get_token("fitbit")
    if not token:
        return {"authenticated": False}
    return {"authenticated": True, "expires_at": token["expires_at"].isoformat()}
