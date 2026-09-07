import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from src.backend.config import get_settings
from src.backend.models.health_metrics import CalendarEvent

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

def get_auth_url(redirect_uri: str) -> Optional[str]:
    settings = get_settings()
    if not settings.google_client_id or not settings.google_client_secret:
        return None
    client_config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }
    }
    flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=redirect_uri)
    auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent")
    return auth_url

def exchange_code(code: str, redirect_uri: str) -> dict:
    settings = get_settings()
    client_config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }
    }
    flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=redirect_uri)
    flow.fetch_token(code=code)
    creds = flow.credentials
    return {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes
    }

def fetch_events(credentials_dict: dict, start_time: datetime, end_time: datetime) -> List[dict]:
    creds = Credentials(**credentials_dict)
    service = build('calendar', 'v3', credentials=creds)
    events_result = service.events().list(calendarId='primary', timeMin=start_time.isoformat(),
                                          timeMax=end_time.isoformat(), singleEvents=True,
                                          orderBy='startTime').execute()
    return events_result.get('items', [])

def derive_signals(events: List[CalendarEvent], home_location: str = "") -> List[CalendarEvent]:
    """Derive lifestyle signals."""
    from geopy.geocoders import Nominatim
    from geopy.distance import geodesic
    
    geolocator = Nominatim(user_agent="aegis_health")
    home_coords = None
    if home_location:
        try:
            home_loc = geolocator.geocode(home_location)
            if home_loc:
                home_coords = (home_loc.latitude, home_loc.longitude)
        except Exception:
            pass
            
    for event in events:
        signals = {}
        
        # Check early morning (<6am)
        if not event.all_day and event.start_time.hour < 6:
            signals["early_morning"] = True
            
        # Check late night (>11pm or ends past midnight)
        if not event.all_day:
            if event.start_time.hour >= 23 or event.end_time.hour >= 23 or event.end_time.hour < 5:
                signals["late_night"] = True
            
        # Real travel detection using geopy
        if event.location and home_coords:
            try:
                evt_loc = geolocator.geocode(event.location)
                if evt_loc:
                    evt_coords = (evt_loc.latitude, evt_loc.longitude)
                    dist = geodesic(home_coords, evt_coords).miles
                    if dist > 50:
                        signals["travel"] = True
            except Exception as e:
                logger.error(f"Geocoding failed for {event.location}: {e}")
            
        event.derived_signals = signals
        
    # Busy day density
    # Count events per day
    days: Dict[str, int] = {}
    for e in events:
        d = e.start_time.date().isoformat()
        days[d] = days.get(d, 0) + 1
        
    for e in events:
        d = e.start_time.date().isoformat()
        if days[d] >= 5:
            e.derived_signals["busy_day"] = True
            
    return events

def parse_events(raw_events: List[dict], home_location: str = "") -> List[CalendarEvent]:
    parsed = []
    for item in raw_events:
        start_str = item["start"].get("dateTime", item["start"].get("date"))
        end_str = item["end"].get("dateTime", item["end"].get("date"))
        
        all_day = "date" in item["start"]
        
        start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00")) if not all_day else datetime.fromisoformat(start_str).replace(tzinfo=timezone.utc)
        end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00")) if not all_day else datetime.fromisoformat(end_str).replace(tzinfo=timezone.utc)
        
        event = CalendarEvent(
            id=str(uuid.uuid4()),
            start_time=start_dt,
            end_time=end_dt,
            title=item.get("summary", "Untitled"),
            location=item.get("location"),
            description=item.get("description"),
            all_day=all_day
        )
        parsed.append(event)
        
    return derive_signals(parsed, home_location)
