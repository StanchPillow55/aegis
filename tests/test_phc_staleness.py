"""PHC-STALE-01 dedicated verify target."""

from pathlib import Path

from tests.test_phc_sync import test_staleness_after_24h


def test_phc_staleness(tmp_path: Path):
    test_staleness_after_24h(tmp_path)
