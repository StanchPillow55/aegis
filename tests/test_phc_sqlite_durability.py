"""PHC-SQLITE-01 alias coverage — durability already in test_mvp_persist."""

from pathlib import Path

from backend.providers.memory import LocalMemoryProvider
from tests.test_mvp_persist import _sample_intake, test_sqlite_survives_reopen


def test_phc_sqlite_durability(tmp_path: Path):
    test_sqlite_survives_reopen(tmp_path)


def test_schema_meta_written(tmp_path: Path):
    mem = LocalMemoryProvider(tmp_path / "meta.sqlite3")
    mem.store(_sample_intake())
    assert mem.schema_version() >= 1
