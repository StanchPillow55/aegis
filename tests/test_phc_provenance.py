"""PHC-PROVENANCE-01: stored records include source, timestamp, quality."""

from pathlib import Path

from backend.health.schema import DataQuality, DataSource
from backend.intake.schema import IntakeResult
from backend.providers.memory import LocalMemoryProvider


def test_provenance_fields_persisted(tmp_path: Path):
    mem = LocalMemoryProvider(tmp_path / "prov.sqlite3")
    intake = IntakeResult.model_validate(
        {
            "soreness": [],
            "sleep": {"quality": "ok", "hours": 7},
            "meals": [],
            "todays_wod": {"movements": [], "raw": None},
            "subjective_readiness": "moderate",
        }
    )
    log_id = mem.store(
        intake,
        source=DataSource.HEURISTIC_EXTRACT,
        extractor="heuristic",
        quality=DataQuality.LOW,
    )
    hit = mem.get(log_id)
    assert hit is not None
    assert hit.provenance is not None
    assert hit.provenance["source"] == "heuristic_extract"
    assert hit.provenance["extractor"] == "heuristic"
    assert hit.provenance["quality"] == "low"
    assert "recorded_at" in hit.provenance
    assert hit.provenance["schema_version"] == 1
    assert hit.content_hash
