"""MVP-EVIDENCE-01: today vs history, dedup, exclude self, conflicts today_wins."""

from __future__ import annotations

from pathlib import Path

from backend.health.evidence import build_evidence_bundle, detect_conflicts
from backend.health.schema import HistoryHit
from backend.intake.schema import IntakeResult
from backend.providers.memory import LocalMemoryProvider


def _intake(**kw) -> IntakeResult:
    data = {
        "soreness": [],
        "sleep": {"quality": "poor", "hours": 6.0},
        "meals": [{"description": "eggs", "protein_g": 24}],
        "todays_wod": {"movements": ["squats"], "raw": "squats"},
        "subjective_readiness": "low",
    }
    data.update(kw)
    if "sleep" in kw:
        data["sleep"] = kw["sleep"]
    return IntakeResult.model_validate(data)


def test_search_excludes_current_and_dedupes(tmp_path: Path):
    mem = LocalMemoryProvider(tmp_path / "ev.sqlite3")
    # Two identical historical contents (different timestamps → different ids)
    a = mem.store(_intake(), ts=1000.0, extractor="fixture")
    b = mem.store(_intake(), ts=1001.0, extractor="fixture")
    assert a != b
    # Current (different sleep) — should be excluded from history
    today = _intake(sleep={"quality": "good", "hours": 8.0}, subjective_readiness="high")
    current_id = mem.store(today, ts=2000.0, extractor="heuristic")

    hits = mem.search("sleep readiness squat", k=5, exclude_ids={current_id}, dedupe=True)
    ids = [h.log_id for h in hits]
    assert current_id not in ids
    # Identical content should collapse to one history hit
    assert len(hits) == 1
    assert hits[0].content_hash is not None


def test_conflicts_today_wins():
    today = _intake(sleep={"quality": "good", "hours": 8.0}, subjective_readiness="high")
    hist = HistoryHit(
        record_id="h1",
        timestamp=1.0,
        content="old",
        score=0.9,
        intake=_intake().model_dump(),
    )
    conflicts = detect_conflicts(today, [hist])
    fields = {c.field for c in conflicts}
    assert "sleep.hours" in fields
    assert "sleep.quality" in fields
    assert all(c.resolution == "today_wins" for c in conflicts)

    bundle = build_evidence_bundle(intake=today, log_id="now", history=[hist], extractor="heuristic")
    assert bundle.today["authoritative"] is True
    assert bundle.today["log_id"] == "now"
    assert bundle.resolution_policy == "today_wins"
    assert len(bundle.history) == 1
    assert len(bundle.conflicts) >= 1
