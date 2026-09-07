from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta

from src.backend.sync.scheduler import get_sync_status, update_sync_status, sync_job, scheduler
from src.backend.models.health_metrics import DataSource

router = APIRouter(prefix="/api/sync", tags=["sync"])

@router.get("/status")
def get_all_status() -> List[Dict[str, Any]]:
    results = []
    for s in [DataSource.fitbit, DataSource.calendar]:
        status = get_sync_status(s.value)
        is_stale = False
        if status.last_sync_at:
            if datetime.now(timezone.utc) - status.last_sync_at > timedelta(hours=24):
                is_stale = True
        elif status.enabled:
            is_stale = True
            
        res = status.model_dump()
        res["is_stale"] = is_stale
        results.append(res)
    return results

@router.post("/toggle/{source}")
def toggle_sync(source: str, enabled: bool):
    try:
        ds = DataSource(source)
    except ValueError:
        raise HTTPException(400, "Invalid source")
        
    status = get_sync_status(ds.value)
    status.enabled = enabled
    update_sync_status(status)
    return {"status": "success", "enabled": enabled}

@router.post("/now/{source}")
async def trigger_sync(source: str, background_tasks: BackgroundTasks):
    try:
        ds = DataSource(source)
    except ValueError:
        raise HTTPException(400, "Invalid source")
        
    background_tasks.add_task(sync_job, ds)
    return {"status": "sync_started"}
