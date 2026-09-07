"""PHC-SAFETY-01"""

from backend.health.schema import SAFETY_DISCLAIMER
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_phc_safety_copy():
    assert "does not diagnose" in SAFETY_DISCLAIMER.lower()
    html = client.get("/").text
    assert "disclaimer-text" in html
    # API includes disclaimer
    # (full directive tested elsewhere)
