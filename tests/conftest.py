import os
import pytest
from src.backend.storage.sqlite_store import init_db

os.environ.setdefault("SQLITE_DB_PATH", ":memory:")

@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    """Ensure DB tables exist for each test."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("SQLITE_DB_PATH", db_path)
    # Clear the cached settings so it picks up the new path
    from src.backend.config import get_settings
    get_settings.cache_clear()
    init_db()
    yield
    get_settings.cache_clear()
