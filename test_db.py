from src.backend.storage.sqlite_store import _get_connection
conn = _get_connection()
rows = conn.execute("SELECT count(*) FROM goals").fetchone()
print(f"Goal count: {rows[0]}")
