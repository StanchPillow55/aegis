import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from src.backend.importers import google_calendar
from src.backend.api.fitbit import store_token, get_token  # Reusing token logic
from src.backend.storage.sqlite_store import _get_connection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/import/calendar", tags=["calendar"])

@router.post("/auth")
def auth(redirect_uri: str):
    """Get auth URL for Google Calendar."""
    url = google_calendar.get_auth_url(redirect_uri)
    if not url:
        raise HTTPException(status_code=500, detail="Google Client ID not configured")
    return {"url": url}

class CallbackRequest(BaseModel):
    code: str
    redirect_uri: str

@router.post("/callback")
def callback(req: CallbackRequest):
    try:
        data = google_calendar.exchange_code(req.code, req.redirect_uri)
        store_token("calendar", data["access_token"], data["refresh_token"], data["expires_in"])
        return {"status": "success"}
    except Exception as e:
        logger.exception("Failed to exchange Google code")
        raise HTTPException(status_code=400, detail=str(e))

def pull_and_store_calendar():
    token_data = get_token("calendar")
    if not token_data:
        return
        
    start = datetime.now(timezone.utc) - timedelta(days=7)
    end = datetime.now(timezone.utc) + timedelta(days=3)
    
    # Needs refresh token logic in real app
    raw_events = google_calendar.fetch_events(token_data, start, end)
    events = google_calendar.parse_events(raw_events, home_location="home")
    
    conn = _get_connection()
    for e in events:
        import json
        conn.execute("""
            INSERT OR REPLACE INTO calendar_events (id, start_time, end_time, title, location, description, all_day, derived_signals)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            e.id, e.start_time.isoformat(), e.end_time.isoformat(), e.title,
            e.location, e.description, e.all_day, json.dumps(e.derived_signals)
        ))
    conn.commit()
    conn.close()

@router.post("/sync")
def sync_calendar(background_tasks: BackgroundTasks):
    token_data = get_token("calendar")
    if not token_data:
        raise HTTPException(status_code=401, detail="Calendar not authenticated")
        
    background_tasks.add_task(pull_and_store_calendar)
    return {"status": "sync_started"}
