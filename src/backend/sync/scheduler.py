import logging
import asyncio
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.backend.models.health_metrics import DataSource, SyncStatus
from src.backend.storage.sqlite_store import _get_connection
from src.backend.api.fitbit import get_token as get_fitbit_token
from src.backend.importers.fitbit import pull_all_data as pull_fitbit
from src.backend.api.calendar import pull_and_store_calendar

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

def get_sync_status(source: str) -> SyncStatus:
    conn = _get_connection()
    row = conn.execute("SELECT * FROM sync_status WHERE source = ?", (source,)).fetchone()
    conn.close()
    if row:
        return SyncStatus(
            source=DataSource(row["source"]),
            last_sync_at=datetime.fromisoformat(row["last_sync_at"]) if row["last_sync_at"] else None,
            next_sync_at=datetime.fromisoformat(row["next_sync_at"]) if row["next_sync_at"] else None,
            enabled=bool(row["enabled"]),
            error_count=row["error_count"],
            last_error=row["last_error"]
        )
    return SyncStatus(source=DataSource(source))

def update_sync_status(status: SyncStatus):
    conn = _get_connection()
    conn.execute("""
        INSERT OR REPLACE INTO sync_status (source, last_sync_at, next_sync_at, enabled, error_count, last_error)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        status.source.value,
        status.last_sync_at.isoformat() if status.last_sync_at else None,
        status.next_sync_at.isoformat() if status.next_sync_at else None,
        1 if status.enabled else 0,
        status.error_count,
        status.last_error
    ))
    conn.commit()
    conn.close()

async def sync_job(source: DataSource):
    status = get_sync_status(source.value)
    if not status.enabled:
        return

    logger.info(f"Starting sync for {source.value}")
    try:
        if source == DataSource.fitbit:
            token = get_fitbit_token("fitbit")
            if token:
                await pull_fitbit(token["access_token"])
        elif source == DataSource.calendar:
            pull_and_store_calendar()

        status.last_sync_at = datetime.now(timezone.utc)
        status.error_count = 0
        status.last_error = None
    except Exception as e:
        logger.exception(f"Sync failed for {source.value}")
        status.error_count += 1
        status.last_error = str(e)
        
        # Exponential backoff would be handled by rescheduling, 
        # but for simplicity we let APScheduler keep the fixed interval 
        # and just track error_count.
    
    update_sync_status(status)

def setup_scheduler():
    # Initialize DB statuses if missing
    for source in [DataSource.fitbit, DataSource.calendar]:
        if get_sync_status(source.value).source == source:
            update_sync_status(get_sync_status(source.value))

    scheduler.add_job(sync_job, IntervalTrigger(hours=4), args=[DataSource.fitbit], id="sync_fitbit", replace_existing=True)
    scheduler.add_job(sync_job, IntervalTrigger(hours=6), args=[DataSource.calendar], id="sync_calendar", replace_existing=True)
    
def start_scheduler():
    setup_scheduler()
    scheduler.start()

def stop_scheduler():
    scheduler.shutdown()
