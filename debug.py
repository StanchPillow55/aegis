from src.backend.importers.google_calendar import parse_events
event = {
    "start": {"dateTime": "2024-01-01T05:00:00Z"},
    "end": {"dateTime": "2024-01-01T06:00:00Z"},
    "summary": "Morning workout"
}
e = parse_events([event])[0]
print(e.start_time, e.start_time.hour, e.all_day, e.derived_signals)
