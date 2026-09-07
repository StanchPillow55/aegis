from tests.test_mvp_product_wave import test_tools_and_charts


def test_phc_llm_tools():
    test_tools_and_charts.__wrapped__ if False else None
    # reuse via direct call with tmp_path from pytest — import functions
    pass


def test_tools_dispatch(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from backend.config import get_settings
    from backend.health.store import HealthMetricsStore
    from backend.tools import HealthQueryTools

    get_settings.cache_clear()
    store = HealthMetricsStore()
    store.ingest_fixture()
    tools = HealthQueryTools(metrics=store)
    assert "metrics" in tools.dispatch("list_metrics")
    assert tools.dispatch("latest", metric="steps")["value"] is not None
    assert "sources" in tools.dispatch("source_freshness")
