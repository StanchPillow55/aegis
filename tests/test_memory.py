import pytest
import time
from backend.intake.schema import IntakeResult, Sleep, WOD
from backend.providers.memory import store_log, search_similar, get_cached_directive, cache_directive

def test_memory_cache():
    # Test sqlite cache
    cache_directive("test_key", "Test rationale", ttl=10)
    res = get_cached_directive("test_key")
    assert res == "Test rationale"
    
def test_store_and_search_memory():
    # Only test if Chroma is healthy or mock it
    # We will just verify it doesn't crash on standard execution.
    intake = IntakeResult(
        soreness=[],
        sleep=Sleep(quality="good"),
        meals=[],
        todays_wod=WOD(movements=[]),
        subjective_readiness="high"
    )
    ts = time.time()
    
    try:
        log_id = store_log(intake, ts)
        assert log_id is not None
        
        results = search_similar("high readiness", k=1)
        # It may return empty if Chroma fails gracefully, but it shouldn't crash
        assert isinstance(results, list)
    except Exception as e:
        pytest.fail(f"Memory operations raised an exception: {e}")
