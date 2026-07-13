import pytest
from importer.wod_importer import fetch_wod
from backend.intake.schema import WOD


def test_fetch_wod(monkeypatch):
    # We can't guarantee playwright will pass without setup (installing browsers).
    # We'll just mock it to verify the pipeline.

    def mock_import_wod(url):
        return WOD(movements=["pull-ups", "squats"], raw="mock wod")

    monkeypatch.setattr("importer.wod_importer.import_wod", mock_import_wod)

    result = fetch_wod("http://mock-gym.com")
    assert "pull-ups" in result.movements
