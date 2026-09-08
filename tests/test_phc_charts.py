from backend.charts import build_metric_trend, validate_chart_spec
from backend.health.store import HealthMetricsStore


def test_phc_charts(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from backend.config import get_settings

    get_settings.cache_clear()
    store = HealthMetricsStore()
    store.ingest_fixture()
    spec = build_metric_trend("sleep_hours", metrics=store)
    dumped = spec.model_dump()
    assert "html" not in dumped
    validate_chart_spec(dumped)
    try:
        validate_chart_spec({"type": "metric_trend", "title": "bad", "script": "alert(1)"})
        assert False
    except Exception:
        pass
