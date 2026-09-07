from __future__ import annotations

import os
from pathlib import Path

import pytest

# Isolate memory DB before app imports settings cache in other modules.
@pytest.fixture()
def tmp_memory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db = tmp_path / "mem.sqlite3"
    monkeypatch.setenv("MEMORY_DB_PATH", str(db))
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from backend.config import get_settings

    get_settings.cache_clear()
    yield db
    get_settings.cache_clear()


def test_store_and_retrieve(tmp_memory: Path):
    from backend.intake.schema import IntakeResult
    from backend.providers.memory import LocalMemoryProvider

    mem = LocalMemoryProvider(tmp_memory)
    intake = IntakeResult.model_validate(
        {
            "soreness": [{"body_part": "quads", "severity": 3}],
            "sleep": {"quality": "poor", "hours": 5},
            "meals": [{"description": "chicken", "protein_g": 40}],
            "todays_wod": {"movements": ["squats"], "raw": "squat day"},
            "subjective_readiness": "low",
        }
    )
    log_id = mem.store(intake)
    assert log_id
    hits = mem.search("quads soreness squat readiness", k=3)
    assert hits
    assert hits[0].log_id == log_id
    recent = mem.recent(1)
    assert len(recent) == 1
