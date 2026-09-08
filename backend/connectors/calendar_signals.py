"""Calendar lifestyle signal derivation (no live Google API required).

Ported from legacy-aegis google_calendar.derive_signals — works on fixture or
live-parsed event dicts. Travel distance requires optional geopy + home location;
without them, travel stays False with an honest note.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


def _parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def derive_calendar_signals(
    events: list[dict[str, Any]],
    *,
    home_location: str = "",
) -> list[dict[str, Any]]:
    """Annotate events with early_morning / late_night / busy_day / travel."""
    enriched: list[dict[str, Any]] = []
    day_counts: dict[str, int] = {}

    home_coords = None
    geocode_note = None
    if home_location:
        try:
            from geopy.geocoders import Nominatim  # type: ignore

            geolocator = Nominatim(user_agent="aegis_local")
            home_loc = geolocator.geocode(home_location, timeout=3)
            if home_loc:
                home_coords = (home_loc.latitude, home_loc.longitude)
            else:
                geocode_note = "home_location_not_found"
        except Exception as exc:  # noqa: BLE001
            geocode_note = f"geopy_unavailable:{type(exc).__name__}"

    for raw in events:
        ev = dict(raw)
        signals: dict[str, Any] = {}
        start = _parse_dt(ev.get("start") or ev.get("start_time"))
        end = _parse_dt(ev.get("end") or ev.get("end_time"))
        all_day = bool(ev.get("all_day"))
        if start and not all_day:
            if start.hour < 6:
                signals["early_morning"] = True
            if start.hour >= 23 or (end and (end.hour >= 23 or end.hour < 5)):
                signals["late_night"] = True
            day_counts[start.date().isoformat()] = day_counts.get(start.date().isoformat(), 0) + 1

        loc = ev.get("location") or ""
        if loc and home_coords:
            try:
                from geopy.distance import geodesic  # type: ignore
                from geopy.geocoders import Nominatim  # type: ignore

                geolocator = Nominatim(user_agent="aegis_local")
                evt_loc = geolocator.geocode(loc, timeout=3)
                if evt_loc:
                    dist = geodesic(home_coords, (evt_loc.latitude, evt_loc.longitude)).miles
                    if dist > 50:
                        signals["travel"] = True
                        signals["distance_mi"] = round(dist, 1)
            except Exception:
                signals["travel"] = False
                signals["travel_note"] = "geocode_failed"
        elif loc and home_location and not home_coords:
            signals["travel"] = False
            signals["travel_note"] = geocode_note or "home_coords_unavailable"
        else:
            signals["travel"] = False

        ev["derived_signals"] = signals
        enriched.append(ev)

    for ev in enriched:
        start = _parse_dt(ev.get("start") or ev.get("start_time"))
        if start and day_counts.get(start.date().isoformat(), 0) >= 5:
            ev.setdefault("derived_signals", {})["busy_day"] = True

    return enriched


def summarize_calendar_signals(events: list[dict[str, Any]]) -> dict[str, Any]:
    events = derive_calendar_signals(events)
    travel = sum(1 for e in events if (e.get("derived_signals") or {}).get("travel"))
    early = sum(1 for e in events if (e.get("derived_signals") or {}).get("early_morning"))
    late = sum(1 for e in events if (e.get("derived_signals") or {}).get("late_night"))
    busy = sum(1 for e in events if (e.get("derived_signals") or {}).get("busy_day"))
    return {
        "events": len(events),
        "travel_days": travel,
        "early_events": early,
        "late_events": late,
        "busy_day_events": busy,
        "events_annotated": events,
    }
