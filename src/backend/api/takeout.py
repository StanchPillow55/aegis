from fastapi import APIRouter, UploadFile, File, HTTPException
import logging
from fastapi import Header

from src.backend.importers.takeout import process_takeout

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/import/takeout", tags=["takeout"])

@router.post("")
async def upload_takeout(file: UploadFile = File(...), x_user_id: str = Header(...)):
    """Upload and process a Google Health Takeout zip file."""
    if not file.filename.endswith(".zip"):
        raise HTTPException(400, "Must be a ZIP file")
        
    try:
        content = await file.read()
        result = process_takeout(x_user_id, content)
        return {"status": "success", "imported": result["records_imported"]}
    except Exception as e:
        logger.exception("Failed to parse takeout")
        raise HTTPException(400, f"Failed to parse Takeout zip: {e}")
