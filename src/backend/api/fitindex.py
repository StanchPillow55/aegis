from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import List

from src.backend.models.health_metrics import BodyComposition
from src.backend.importers import fitindex
from src.backend.storage.sqlite_store import _get_connection

router = APIRouter(prefix="/api/import/fitindex", tags=["fitindex"])

def save_body_composition(user_id: str, bc: BodyComposition):
    import uuid
    from src.backend.models.health_metrics import MetricType
    conn = _get_connection()
    conn.execute("""
        INSERT OR REPLACE INTO body_compositions 
        (id, date, weight, body_fat_pct, muscle_mass_pct, bone_mass, bmi, visceral_fat, body_water_pct, metabolic_age, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        bc.id, bc.date.isoformat(), bc.weight, bc.body_fat_pct, bc.muscle_mass_pct,
        bc.bone_mass, bc.bmi, bc.visceral_fat, bc.body_water_pct, bc.metabolic_age, bc.source.value
    ))
    
    # Also save to health_metrics so charts populate
    if bc.weight:
        conn.execute("INSERT OR REPLACE INTO health_metrics (id, user_id, timestamp, metric_type, value, unit, source, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), user_id, bc.date.isoformat(), MetricType.weight.value, bc.weight, "lbs", bc.source.value, "{}"))
    if bc.body_fat_pct:
        conn.execute("INSERT OR REPLACE INTO health_metrics (id, user_id, timestamp, metric_type, value, unit, source, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), user_id, bc.date.isoformat(), MetricType.body_fat_pct.value, bc.body_fat_pct, "%", bc.source.value, "{}"))

    conn.commit()
    conn.close()

from fastapi import Header

@router.post("/csv", response_model=List[BodyComposition])
async def upload_csv(file: UploadFile = File(...), x_user_id: str = Header(...)):
    """Parse a FITINDEX export CSV."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "Must be a CSV file")
        
    content = await file.read()
    results = fitindex.parse_csv(content.decode("utf-8"))
    
    for r in results:
        save_body_composition(x_user_id, r)
        
    return results

@router.post("/screenshot", response_model=BodyComposition)
async def upload_screenshot(file: UploadFile = File(...), x_user_id: str = Header(...)):
    """Extract metrics from FITINDEX app screenshot."""
    content = await file.read()
    try:
        result = await fitindex.extract_from_image(content)
        save_body_composition(x_user_id, result)
        return result
    except Exception as e:
        raise HTTPException(500, f"Failed to extract from image: {e}")

@router.post("/manual", response_model=BodyComposition)
async def upload_manual(text: str = Form(...), x_user_id: str = Header(...)):
    """Parse free-text manual entry."""
    try:
        result = await fitindex.extract_from_text(text)
        save_body_composition(x_user_id, result)
        return result
    except Exception as e:
        raise HTTPException(500, f"Failed to extract from text: {e}")
