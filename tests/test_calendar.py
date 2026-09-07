import pytest
from datetime import datetime, timezone
import uuid

from src.backend.importers.google_calendar import parse_events, derive_signals
from src.backend.models.health_metrics import CalendarEvent

def test_parse_events():
    raw_events = [
        {
            "start": {"dateTime": "2024-05-12T05:00:00Z"},
            "end": {"dateTime": "2024-05-12T06:00:00Z"},
            "summary": "Early Workout",
            "location": "home"
        },
        {
            "start": {"dateTime": "2024-05-12T23:30:00Z"},
            "end": {"dateTime": "2024-05-13T00:30:00Z"},
            "summary": "Late Call",
            "location": "office"
        },
        {
            "start": {"date": "2024-05-12"},
            "end": {"date": "2024-05-13"},
            "summary": "All Day Event"
        }
    ]
    
    events = parse_events(raw_events, home_location="home")
    assert len(events) == 3
    
    # Early morning check
    early = events[0]
    assert early.derived_signals.get("early_morning") is True
    assert early.derived_signals.get("travel") is None
    
    # Late night & travel check
    late = events[1]
    assert late.derived_signals.get("late_night") is True
    assert late.derived_signals.get("travel") is True
    
    # All day check
    all_day = events[2]
    assert all_day.all_day is True
    assert all_day.derived_signals.get("early_morning") is None
    
def test_busy_day_density():
    # 5 events on the same day
    base_dt = datetime(2024, 5, 12, 10, 0, tzinfo=timezone.utc)
    raw = []
    for i in range(5):
        raw.append({
            "start": {"dateTime": (base_dt).isoformat()},
            "end": {"dateTime": (base_dt).isoformat()},
            "summary": f"Meeting {i}"
        })
        
    events = parse_events(raw)
    for e in events:
        assert e.derived_signals.get("busy_day") is True
