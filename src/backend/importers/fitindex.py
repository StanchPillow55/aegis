import csv
import io
import json
import base64
from datetime import datetime, date, timezone
from typing import List, Optional
import uuid

import httpx

from src.backend.config import get_settings
from src.backend.models.health_metrics import BodyComposition, DataSource

_SYSTEM_PROMPT_TEXT = """You extract body composition data from free text.
Return a JSON object exactly matching this structure:
{
    "weight": number_in_lbs,
    "body_fat_pct": number_or_null,
    "muscle_mass_pct": number_or_null,
    "bone_mass": number_in_lbs_or_null,
    "bmi": number_or_null,
    "visceral_fat": number_or_null,
    "body_water_pct": number_or_null,
    "metabolic_age": integer_or_null
}
Return ONLY valid JSON. Omit fields not mentioned (use null).
"""

_VISION_PROMPT = """Look at this FITINDEX app screenshot and extract the body composition metrics.
Return a JSON object exactly matching this structure:
{
    "weight": number_in_lbs,
    "body_fat_pct": number_or_null,
    "muscle_mass_pct": number_or_null,
    "bone_mass": number_in_lbs_or_null,
    "bmi": number_or_null,
    "visceral_fat": number_or_null,
    "body_water_pct": number_or_null,
    "metabolic_age": integer_or_null
}
Return ONLY valid JSON. Use null if a metric is not found.
"""

def parse_csv(content: str) -> List[BodyComposition]:
    """Parse a FITINDEX export CSV."""
    # FITINDEX CSV typically has columns like: Time, Weight(lb), BMI, Body Fat(%), Fat-free Body Weight(lb), Subcutaneous Fat(%), Visceral Fat, Body Water(%), Skeletal Muscle(%), Muscle Mass(lb), Bone Mass(lb), Protein(%), BMR(kcal), Metabolic Age
    results = []
    reader = csv.DictReader(io.StringIO(content))
    
    for row in reader:
        # Get date
        time_str = row.get("Time", "")
        if not time_str:
            continue
        try:
            dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            try:
                dt = datetime.strptime(time_str, "%Y-%m-%d")
            except ValueError:
                continue
                
        def get_float(key: str) -> Optional[float]:
            val = row.get(key)
            if not val or val.strip() == "--":
                return None
            try:
                return float(val.strip())
            except ValueError:
                return None
                
        weight = get_float("Weight(lb)")
        if weight is None:
            continue
            
        bc = BodyComposition(
            id=str(uuid.uuid4()),
            date=dt.date(),
            weight=weight,
            bmi=get_float("BMI"),
            body_fat_pct=get_float("Body Fat(%)"),
            muscle_mass_pct=get_float("Skeletal Muscle(%)"),
            bone_mass=get_float("Bone Mass(lb)"),
            visceral_fat=get_float("Visceral Fat"),
            body_water_pct=get_float("Body Water(%)"),
            metabolic_age=int(get_float("Metabolic Age")) if get_float("Metabolic Age") else None,
            source=DataSource.fitindex
        )
        results.append(bc)
        
    return results

async def extract_from_text(text: str) -> BodyComposition:
    """Extract body composition from manual text entry using Ollama."""
    settings = get_settings()
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{settings.ollama_base_url}/api/generate",
            json={
                "model": settings.ollama_model,
                "prompt": text,
                "system": _SYSTEM_PROMPT_TEXT,
                "stream": False,
                "format": "json",
            },
        )
        response.raise_for_status()
        result = response.json()
        
    raw_text = result.get("response", "")
    parsed = json.loads(raw_text)
    
    return BodyComposition(
        id=str(uuid.uuid4()),
        date=date.today(),
        source=DataSource.fitindex,
        **parsed
    )

async def extract_from_image(image_bytes: bytes) -> BodyComposition:
    """Extract body composition from screenshot using Ollama vision."""
    settings = get_settings()
    b64_image = base64.b64encode(image_bytes).decode("utf-8")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{settings.ollama_base_url}/api/generate",
            json={
                "model": settings.ollama_vision_model,
                "prompt": _VISION_PROMPT,
                "images": [b64_image],
                "stream": False,
                "format": "json",
            },
        )
        response.raise_for_status()
        result = response.json()
        
    raw_text = result.get("response", "")
    parsed = json.loads(raw_text)
    
    return BodyComposition(
        id=str(uuid.uuid4()),
        date=date.today(),
        source=DataSource.fitindex,
        **parsed
    )
