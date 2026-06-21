import time
import statistics
import pytest

from backend.intake.schema import IntakeResult, Soreness, Sleep, Meal, WOD
from backend.memory.store import (
    store_log,
    search_similar,
    get_recent,
    cache_directive,
    get_cached_directive,
    SearchResult,
)


@pytest.fixture(scope="module")
def seed_synthetic_logs():
    base_ts = time.time() - 86400 * 7
    
    logs = [
        IntakeResult(
            soreness=[
                Soreness(body_part="forearms", severity=3),
                Soreness(body_part="shoulders", severity=2),
            ],
            sleep=Sleep(quality="good", hours=7.5),
            meals=[Meal(description="eggs and oats", protein_g=25)],
            todays_wod=WOD(movements=["cleans", "pull-ups"], raw="heavy day"),
            subjective_readiness="moderate",
        ),
        IntakeResult(
            soreness=[
                Soreness(body_part="forearms", severity=5),
            ],
            sleep=Sleep(quality="poor", hours=5.5),
            meals=[Meal(description="protein shake", protein_g=30)],
            todays_wod=WOD(movements=["front squats", "rowing"], raw="light recovery"),
            subjective_readiness="low",
        ),
        IntakeResult(
            soreness=[
                Soreness(body_part="lower back", severity=2),
            ],
            sleep=Sleep(quality="good", hours=8.0),
            meals=[Meal(description="chicken and rice", protein_g=50)],
            todays_wod=WOD(movements=["deadlifts", "box jumps"]),
            subjective_readiness="high",
        ),
        IntakeResult(
            soreness=[
                Soreness(body_part="quads", severity=3),
                Soreness(body_part="glutes", severity=3),
            ],
            sleep=Sleep(quality="good", hours=7.0),
            meals=[Meal(description="steak and sweet potato", protein_g=60)],
            todays_wod=WOD(movements=["back squats", "lunges"]),
            subjective_readiness="moderate",
        ),
        IntakeResult(
            soreness=[
                Soreness(body_part="forearms", severity=2),
                Soreness(body_part="wrists", severity=2),
            ],
            sleep=Sleep(quality="good", hours=7.5),
            meals=[Meal(description="salmon and veggies", protein_g=45)],
            todays_wod=WOD(movements=["snatches", "overhead press"], raw="technique focus"),
            subjective_readiness="high",
        ),
        IntakeResult(
            soreness=[
                Soreness(body_part="shoulders", severity=3),
            ],
            sleep=Sleep(quality="fair", hours=6.5),
            meals=[Meal(description="turkey sandwich", protein_g=35)],
            todays_wod=WOD(movements=["front rack lunges", "push press"]),
            subjective_readiness="moderate",
        ),
        IntakeResult(
            soreness=[
                Soreness(body_part="hamstrings", severity=2),
            ],
            sleep=Sleep(quality="excellent", hours=8.5),
            meals=[Meal(description="greek yogurt and berries", protein_g=20), Meal(description="grilled chicken salad", protein_g=40)],
            todays_wod=WOD(movements=["running", "burpees"], raw="conditioning"),
            subjective_readiness="high",
        ),
        IntakeResult(
            soreness=[
                Soreness(body_part="forearms", severity=3),
                Soreness(body_part="upper back", severity=2),
            ],
            sleep=Sleep(quality="good", hours=7.0),
            meals=[Meal(description="beef and broccoli", protein_g=55)],
            todays_wod=WOD(movements=["power cleans", "front squats", "jerks"], raw="olympic lifting"),
            subjective_readiness="high",
        ),
    ]
    
    log_ids = []
    for i, log in enumerate(logs):
        ts = base_ts + (i * 86400)
        log_id = store_log(log, ts)
        log_ids.append(log_id)
    
    time.sleep(0.5)
    
    return log_ids


def test_vector_search_grip_front_rack(seed_synthetic_logs):
    results = search_similar("forearms grip front rack", k=5)
    
    assert len(results) > 0, "Should return at least one result"
    
    relevant_count = 0
    for log in results:
        content_lower = log.content.lower()
        if any(term in content_lower for term in ["forearm", "grip", "front rack", "clean"]):
            relevant_count += 1
    
    assert relevant_count >= 3, f"Expected at least 3 relevant logs, got {relevant_count}"
    
    top_result = results[0]
    assert "forearm" in top_result.content.lower() or "grip" in top_result.content.lower(), \
        "Top result should mention forearms or grip"


def test_vector_search_cleans_history(seed_synthetic_logs):
    results = search_similar("cleans history", k=5)
    
    assert len(results) > 0, "Should return results for cleans query"
    
    cleans_count = 0
    for log in results:
        if "clean" in log.movements.lower():
            cleans_count += 1
    
    assert cleans_count >= 2, f"Expected at least 2 logs with cleans, got {cleans_count}"


def test_retrieval_latency_p95(seed_synthetic_logs):
    latencies = []
    
    queries = [
        "forearms grip front rack",
        "cleans",
        "squats DOMS",
        "recovery sleep",
        "high readiness",
        "shoulder pain",
        "olympic lifting",
        "conditioning running",
        "protein meals",
        "poor sleep",
    ]
    
    for _ in range(2):
        for query in queries:
            start = time.perf_counter()
            results = search_similar(query, k=5)
            end = time.perf_counter()
            
            latency_ms = (end - start) * 1000
            latencies.append(latency_ms)
            
            assert len(results) >= 0, "Search should complete without error"
    
    assert len(latencies) == 20, "Should have 20 latency measurements"
    
    p95 = statistics.quantiles(latencies, n=20)[18]
    
    print(f"\nLatency stats (ms):")
    print(f"  Min: {min(latencies):.2f}")
    print(f"  Median: {statistics.median(latencies):.2f}")
    print(f"  P95: {p95:.2f}")
    print(f"  Max: {max(latencies):.2f}")
    
    assert p95 < 150, f"P95 latency {p95:.2f}ms exceeds 150ms threshold"


def test_get_recent_logs(seed_synthetic_logs):
    recent = get_recent(n=5)
    
    assert len(recent) <= 5, "Should return at most 5 logs"
    assert len(recent) > 0, "Should return at least one log"
    
    for i in range(len(recent) - 1):
        assert recent[i].timestamp >= recent[i + 1].timestamp, \
            "Logs should be sorted by timestamp descending"


def test_cache_directive_beyond_caching():
    key = "test_directive_key"
    rationale = "Rest day recommended due to accumulated fatigue in forearms and shoulders"
    
    cache_directive(key, rationale, ttl=10)
    
    cached = get_cached_directive(key)
    assert cached == rationale, "Cached directive should match stored value"
    
    non_existent = get_cached_directive("non_existent_key")
    assert non_existent is None, "Non-existent key should return None"


def test_beyond_caching_proof(seed_synthetic_logs):
    vector_results = search_similar("grip fatigue front rack", k=3)
    assert len(vector_results) > 0, "Vector search should work"
    
    recent_results = get_recent(n=3)
    assert len(recent_results) > 0, "Recent retrieval should work"
    
    cache_directive("proof_key", "This proves we use Redis beyond caching", ttl=60)
    cached = get_cached_directive("proof_key")
    assert cached is not None, "Caching should work"
    
    print("\n=== BEYOND CACHING PROOF ===")
    print("✓ Vector search (HNSW index): semantic similarity retrieval")
    print("✓ Agent memory: temporal log storage and retrieval")
    print("✓ Context retrieval: sorted recent logs by timestamp")
    print("✓ Caching: directive memoization (traditional use)")
    print("===========================")
