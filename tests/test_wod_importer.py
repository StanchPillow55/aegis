import os
import pytest
from pathlib import Path

from importer.wod_importer import import_wod, _extract_wod_from_page
from backend.intake.schema import WOD


@pytest.fixture
def sample_wod_path():
    return Path(__file__).parent / "fixtures" / "sample_wod.html"


def test_import_wod_deterministic(sample_wod_path, httpserver):
    with open(sample_wod_path, "r") as f:
        html_content = f.read()
    
    httpserver.expect_request("/wod").respond_with_data(html_content, content_type="text/html")
    
    url = httpserver.url_for("/wod")
    
    wod = import_wod(url)
    
    assert isinstance(wod, WOD)
    assert len(wod.movements) > 0, "Should extract at least one movement"
    
    movements_lower = [m.lower() for m in wod.movements]
    
    expected_movements = ["clean", "pull up", "bike"]
    found_movements = []
    for expected in expected_movements:
        if any(expected in m for m in movements_lower):
            found_movements.append(expected)
    
    assert len(found_movements) >= 2, f"Should find at least 2 expected movements (cleans, pull-ups, bike), found: {found_movements}"
    
    assert wod.raw is not None, "Should capture raw WOD text"
    assert len(wod.raw) > 0, "Raw text should not be empty"


def test_import_wod_graceful_failure():
    wod = import_wod("http://invalid-url-that-does-not-exist.local")
    
    assert isinstance(wod, WOD)
    assert wod.movements == []
    assert wod.raw == ""


@pytest.mark.skipif(
    not os.getenv("RUN_LIVE_WOD_TEST"),
    reason="Live WOD test skipped (set RUN_LIVE_WOD_TEST=1 to enable)"
)
def test_import_wod_live_smoke():
    live_url = os.getenv("LIVE_WOD_URL", "https://www.crossfit.com/workout")
    
    wod = import_wod(live_url)
    
    assert isinstance(wod, WOD)
    print(f"\nLive WOD import results:")
    print(f"  Movements: {wod.movements}")
    print(f"  Raw (first 200 chars): {wod.raw[:200]}")


def test_wod_model_frozen_schema():
    wod = WOD(movements=["cleans", "pull-ups"], raw="21-15-9 for time")
    
    assert hasattr(wod, "movements")
    assert hasattr(wod, "raw")
    assert isinstance(wod.movements, list)
    assert isinstance(wod.raw, str)
    
    assert not hasattr(wod, "note"), "WOD should use 'raw' field, not 'note' (frozen schema)"
