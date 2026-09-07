"""MVP-PERSIST-01 / PHC-SQLITE-01: SQLite survives process restart."""

from __future__ import annotations

from pathlib import Path

from backend.health.schema import DataSource, SCHEMA_VERSION
from backend.intake.schema import IntakeResult
from backend.providers.memory import LocalMemoryProvider


def _sample_intake(**overrides) -> IntakeResult:
    base = {
        "soreness": [{"body_part": "quads", "severity": 2}],
        "sleep": {"quality": "good", "hours": 8.0},
        "meals": [{"description": "chicken", "protein_g": 30}],
        "todays_wod": {"movements": ["squats"], "raw": "squat day"},
        "subjective_readiness": "moderate",
    }
    base.update(overrides)
    return IntakeResult.model_validate(base)


def test_sqlite_survives_reopen(tmp_path: Path):
    db = tmp_path / "durable.sqlite3"
    mem1 = LocalMemoryProvider(db)
    assert mem1.schema_version() == SCHEMA_VERSION
    log_id = mem1.store(
        _sample_intake(),
        source=DataSource.FIXTURE,
        extractor="fixture",
    )
    assert mem1.count() == 1
    assert mem1.get(log_id) is not None

    # New process / new provider instance against same file
    mem2 = LocalMemoryProvider(db)
    assert mem2.count() == 1
    hit = mem2.get(log_id)
    assert hit is not None
    assert hit.log_id == log_id
    assert hit.provenance is not None
    assert hit.provenance["source"] == DataSource.FIXTURE.value
    recent = mem2.recent(5)
    assert any(r.log_id == log_id for r in recent)
