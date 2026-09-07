"""Bundled offline health fixtures for local demo / sync tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "health_bundle.json"


def default_fixture_bundle() -> dict[str, Any]:
    return {
        "sample_days": 3,
        "record_count": 12,
        "metrics": {
            "resting_hr": [{"date": "2026-09-05", "value": 58}, {"date": "2026-09-06", "value": 60}],
            "sleep_hours": [{"date": "2026-09-05", "value": 7.2}, {"date": "2026-09-06", "value": 6.1}],
            "steps": [{"date": "2026-09-05", "value": 8200}, {"date": "2026-09-06", "value": 10400}],
            "weight_kg": [{"date": "2026-09-05", "value": 82.4}],
            "body_fat_pct": [{"date": "2026-09-05", "value": 18.2}],
            "hrv": [{"date": "2026-09-06", "value": 62}],
        },
        "activities": [
            {"date": "2026-09-06", "name": "Strength", "minutes": 55},
        ],
        "notes": "Offline fixture — used when Fitbit/Calendar/weather unavailable.",
    }


def load_fixture_bundle(path: Path | None = None) -> dict[str, Any]:
    target = path or FIXTURE_PATH
    if target.exists():
        return json.loads(target.read_text(encoding="utf-8"))
    return default_fixture_bundle()


def ensure_fixture_file(path: Path | None = None) -> Path:
    target = path or FIXTURE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_text(json.dumps(default_fixture_bundle(), indent=2) + "\n", encoding="utf-8")
    return target
