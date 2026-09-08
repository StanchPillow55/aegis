from tests.test_mvp_product_wave import test_alerts_defaults_and_dedup as test_phc_alerts
from backend.health.schema import SAFETY_DISCLAIMER


def test_phc_safety_copy():
    assert "does not diagnose" in SAFETY_DISCLAIMER.lower()
    assert "prescribe treatment" in SAFETY_DISCLAIMER.lower()
