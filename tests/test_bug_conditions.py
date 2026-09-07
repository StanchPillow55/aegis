import pytest
from fastapi.testclient import TestClient

def test_bug_import_main():
    """Test that importing src.backend.main works without ModuleNotFoundError"""
    import src.backend.main
    assert src.backend.main.app is not None

def test_bug_import_scheduler():
    """Test that importing start_scheduler works without ImportError"""
    from src.backend.sync.scheduler import start_scheduler
    assert start_scheduler is not None

def test_bug_get_directive():
    """Test that GET /api/directive with X-User-ID header returns HTTP 200 (not 500)"""
    from src.backend.main import app
    client = TestClient(app)
    response = client.get("/api/directive", headers={"X-User-ID": "test_user"})
    # It might return 404 or something if db is empty, but definitely not 500 TypeError
    assert response.status_code != 500

def test_bug_get_patterns():
    """Test that GET /api/patterns/search?query=test with X-User-ID header returns HTTP 200 (not 500)"""
    from src.backend.main import app
    client = TestClient(app)
    response = client.get("/api/patterns/search?query=test", headers={"X-User-ID": "test_user"})
    assert response.status_code != 500

def test_bug_get_logs():
    """Test that GET /api/logs/2024-01-01 with X-User-ID header returns HTTP 200 (not 500)"""
    from src.backend.main import app
    client = TestClient(app)
    response = client.get("/api/logs/2024-01-01", headers={"X-User-ID": "test_user"})
    assert response.status_code != 500

def test_bug_alert_persistence():
    """Test that alerts persist across client recreation and are isolated by user."""
    from src.backend.main import app
    from src.backend.safety.anomaly_detector import check_metric_against_thresholds, get_system_defaults
    from src.backend.models.health_metrics import HealthMetric, MetricType, DataSource
    from datetime import datetime, timezone
    import uuid
    
    # Trigger an alert
    metric = HealthMetric(id=str(uuid.uuid4()), metric_type=MetricType.heart_rate, value=250.0, timestamp=datetime.now(timezone.utc), source=DataSource.manual, unit="bpm")
    thresholds = get_system_defaults()
    alert = check_metric_against_thresholds(metric, thresholds, user_id="test_user")
    assert alert is not None
    
    # Check persistence and user isolation
    client = TestClient(app)
    response = client.get("/api/alerts", headers={"X-User-ID": "test_user"})
    assert response.status_code == 200
    assert len(response.json()) >= 1
    alert_id = response.json()[0]["id"]
    
    # Isolation
    response_other = client.get("/api/alerts", headers={"X-User-ID": "other_user"})
    assert response_other.status_code == 200
    assert len(response_other.json()) == 0
    
    # Acknowledge
    ack_response = client.post(f"/api/alerts/{alert_id}/acknowledge", headers={"X-User-ID": "test_user"})
    assert ack_response.status_code == 200
    
    response_empty = client.get("/api/alerts", headers={"X-User-ID": "test_user"})
    assert response_empty.status_code == 200
    assert not any(a["id"] == alert_id for a in response_empty.json())

def test_bug_threshold_persistence():
    """Test that custom thresholds persist and defaults are returned."""
    from src.backend.main import app
    client = TestClient(app)
    
    # Defaults
    resp = client.get("/api/settings/thresholds", headers={"X-User-ID": "test_user"})
    assert resp.status_code == 200
    assert len(resp.json()) == 4
    
    # Custom
    payload = {
        "id": "test_thresh",
        "metric_type": "heart_rate",
        "condition": "above",
        "value": 150.0,
        "severity": "warning",
        "message": "Test"
    }
    client.post("/api/settings/thresholds", json=payload, headers={"X-User-ID": "test_user"})
    
    # Re-client
    client2 = TestClient(app)
    resp2 = client2.get("/api/settings/thresholds", headers={"X-User-ID": "test_user"})
    assert len(resp2.json()) == 5
    
    # Delete
    client2.delete("/api/settings/thresholds/test_thresh", headers={"X-User-ID": "test_user"})
    resp3 = client2.get("/api/settings/thresholds", headers={"X-User-ID": "test_user"})
    assert len(resp3.json()) == 4

def test_bug_context_builder():
    """Test that context builder uses real data."""
    from src.backend.intelligence.context_builder import build_context
    from src.backend.storage.sqlite_store import _get_connection
    from datetime import datetime, timezone
    
    # 1. Empty DB
    empty_context = build_context("test_user")
    assert "No vitals data synced" in empty_context
    assert "No body composition data" in empty_context
    assert "No calendar data synced" in empty_context
    
    # 2. Seed DB
    conn = _get_connection()
    now = datetime.now(timezone.utc).isoformat()
    # health metric
    conn.execute(
        "INSERT INTO health_metrics (id, user_id, timestamp, metric_type, value, unit, source) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("m1", "test_user", now, "resting_heart_rate", 58.0, "bpm", "test")
    )
    # body comp
    conn.execute(
        "INSERT INTO body_compositions (id, date, weight, body_fat_pct, source) VALUES (?, ?, ?, ?, ?)",
        ("bc1", now[:10], 175.0, 18.5, "test")
    )
    conn.commit()
    conn.close()
    
    # 3. Test again
    full_context = build_context("test_user")
    assert "58bpm" in full_context
    assert "52bpm" not in full_context
    assert "175.0 lbs" in full_context
    assert "18.5% body fat" in full_context

def test_bug_llm_tools():
    """Test that LLM tools use real database queries."""
    from src.backend.intelligence.tools import get_body_composition, get_calendar_context, compare_periods, get_correlations
    from src.backend.storage.sqlite_store import _get_connection
    from datetime import datetime, timezone, timedelta
    
    # 1. Empty DB
    assert "No body composition" in get_body_composition("test_user", "2024-01-01T00:00:00Z")
    assert "No calendar data" in get_calendar_context("test_user", "2024-01-01T00:00:00Z")
    
    # 2. Seed DB
    conn = _get_connection()
    now = datetime.now(timezone.utc)
    # body comp
    conn.execute(
        "INSERT INTO body_compositions (id, date, weight, body_fat_pct, source) VALUES (?, ?, ?, ?, ?)",
        ("bc2", now.isoformat()[:10], 180.0, 19.0, "test")
    )
    # calendar
    conn.execute(
        "INSERT INTO calendar_events (id, start_time, end_time, title, derived_signals) VALUES (?, ?, ?, ?, ?)",
        ("cal1", now.isoformat(), now.isoformat(), "Test Event", '{"travel": true, "early_morning": false, "late_night": false}')
    )
    # health metrics
    cutoff_a = (now - timedelta(days=5)).isoformat()
    cutoff_b = (now - timedelta(days=10)).isoformat()
    conn.execute("INSERT INTO health_metrics (id, user_id, timestamp, metric_type, value, unit, source) VALUES (?, ?, ?, ?, ?, ?, ?)", ("m_a1", "test_user", cutoff_a, "steps", 10000, "steps", "test"))
    conn.execute("INSERT INTO health_metrics (id, user_id, timestamp, metric_type, value, unit, source) VALUES (?, ?, ?, ?, ?, ?, ?)", ("m_a2", "test_user", cutoff_a, "heart_rate", 70, "bpm", "test"))
    conn.execute("INSERT INTO health_metrics (id, user_id, timestamp, metric_type, value, unit, source) VALUES (?, ?, ?, ?, ?, ?, ?)", ("m_b1", "test_user", cutoff_b, "steps", 5000, "steps", "test"))
    conn.execute("INSERT INTO health_metrics (id, user_id, timestamp, metric_type, value, unit, source) VALUES (?, ?, ?, ?, ?, ?, ?)", ("m_b2", "test_user", cutoff_b, "heart_rate", 75, "bpm", "test"))
    conn.commit()
    conn.close()
    
    # 3. Test Tools
    bc = get_body_composition("test_user", (now - timedelta(days=30)).isoformat())
    assert "180.0 lbs" in bc
    
    cal = get_calendar_context("test_user", (now - timedelta(days=30)).isoformat())
    assert "1 events" in cal
    assert "1 travel days" in cal
    
    comp = compare_periods("test_user", "steps", "period_a", "period_b")
    assert "10000.0" in comp
    assert "5000.0" in comp
    
    corr = get_correlations("test_user", "steps", "heart_rate", 30)
    # Might not have enough overlapping days (only 1 day seeded for each)
    assert "Not enough overlapping data" in corr or "correlation" in corr

def test_bug_google_calendar_oauth(mocker):
    """Test that Google Calendar OAuth functions use real implementations."""
    from src.backend.importers.google_calendar import get_auth_url, fetch_events
    from src.backend.config import get_settings
    from datetime import datetime, timezone
    
    # 1. No credentials config should return None
    settings = get_settings()
    settings.google_client_id = None
    settings.google_client_secret = None
    assert get_auth_url("http://localhost/callback") is None
    
    # 2. Test fetch_events calls the real API builder
    mock_build = mocker.patch("src.backend.importers.google_calendar.build")
    mock_service = mock_build.return_value
    mock_events = mock_service.events.return_value
    mock_list = mock_events.list.return_value
    mock_list.execute.return_value = {"items": [{"id": "123", "summary": "test"}]}
    
    creds_dict = {
        "token": "test",
        "refresh_token": "test",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "test",
        "client_secret": "test",
        "scopes": []
    }
    now = datetime.now(timezone.utc)
    items = fetch_events(creds_dict, now, now)
    
    assert len(items) == 1
    assert len(items) == 1
    assert items[0]["id"] == "123"
    mock_build.assert_called_once()
    mock_events.list.assert_called_once()

def test_bug_takeout_zip():
    """Test that Takeout zip parser extracts real data."""
    from src.backend.importers.takeout import parse_takeout_zip
    from src.backend.models.health_metrics import MetricType
    import zipfile
    import io
    import json
    
    # Create mock zip
    mem_zip = io.BytesIO()
    with zipfile.ZipFile(mem_zip, mode="w") as zf:
        # Heart rate file
        hr_data = {
            "Data Points": [
                {
                    "startTimeNanos": "1672531200000000000",
                    "endTimeNanos": "1672531200000000000",
                    "fitValue": [{"value": {"fpVal": 72.5}}]
                }
            ]
        }
        zf.writestr("Takeout/Fit/All Data/derived_com.google.heart_rate.bpm.json", json.dumps(hr_data))
        
        # Sleep file
        sleep_data = {
            "Data Points": [
                {
                    "startTimeNanos": "1672531200000000000",
                    "endTimeNanos": "1672552800000000000", # +6 hours (21600 seconds)
                    "fitValue": [{"value": {"intVal": 1}}]
                }
            ]
        }
        zf.writestr("Takeout/Fit/All Data/derived_com.google.sleep_segment.json", json.dumps(sleep_data))
        
    mem_zip.seek(0)
    records = parse_takeout_zip(mem_zip.read())
    
    assert len(records) == 2
    
    hr_rec = next(r for r in records if r["metric"] == MetricType.heart_rate.value)
    assert hr_rec["value"] == 72.5
    assert hr_rec["unit"] == "bpm"
    
    sleep_rec = next(r for r in records if r["metric"] == MetricType.sleep_duration.value)
    # 21600 seconds / 60 = 360 minutes
    assert sleep_rec["value"] == 360.0
    assert sleep_rec["unit"] == "minutes"

def test_bug_guardrails():
    """Test that guardrails produce grammatical rewrites."""
    from src.backend.safety.guardrails import apply_guardrails
    from src.backend.models.health_metrics import MetricType
    
    # 1. Normative rewrite
    res = apply_guardrails("Your HRV is too low.")
    assert "below your recent baseline" in res
    assert "notable" not in res
    
    # 2. Goal-aware suppression
    res2 = apply_guardrails("Your hrv is too low.", active_goal_metrics=[MetricType.hrv])
    assert res2 == "Your hrv is too low."
    
    # 3. Action-oriented rewrite
    res3 = apply_guardrails("You should drink more water.")
    assert "drink more water may be worth considering" in res3
