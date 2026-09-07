import logging
import json
import zipfile
import io
from typing import List, Dict, Any
import uuid
from datetime import datetime, timezone

from src.backend.models.health_metrics import DataSource, MetricType
from src.backend.storage.sqlite_store import _get_connection

logger = logging.getLogger(__name__)

def parse_takeout_zip(file_bytes: bytes) -> List[Dict[str, Any]]:
    results = []
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            for filename in z.namelist():
                if not filename.endswith('.json'):
                    continue
                
                name_lower = filename.lower()
                metric = None
                unit = ""
                if "heart_rate_variability" in name_lower or "hrv" in name_lower:
                    metric = MetricType.hrv.value
                    unit = "ms"
                elif "heart_rate" in name_lower:
                    metric = MetricType.heart_rate.value
                    unit = "bpm"
                elif "step_count" in name_lower:
                    metric = MetricType.steps.value
                    unit = "steps"
                elif "calories" in name_lower:
                    metric = MetricType.calories.value
                    unit = "kcal"
                elif "sleep_segment" in name_lower:
                    metric = MetricType.sleep_duration.value
                    unit = "minutes"
                    
                if not metric:
                    continue
                    
                try:
                    data = json.loads(z.read(filename))
                    points = data.get("Data Points", [])
                    for pt in points:
                        try:
                            start_n = int(pt["startTimeNanos"])
                            ts = datetime.fromtimestamp(start_n / 1e9, tz=timezone.utc).isoformat()
                            if metric == MetricType.sleep_duration.value:
                                end_n = int(pt["endTimeNanos"])
                                val = (end_n - start_n) / 1e9 / 60.0
                            else:
                                val = float(pt["fitValue"][0]["value"]["fpVal"])
                                
                            results.append({
                                "metric": metric,
                                "value": val,
                                "timestamp": ts,
                                "unit": unit
                            })
                        except Exception:
                            continue
                except Exception:
                    continue
    except zipfile.BadZipFile:
        raise ValueError("Invalid zip file")
        
    return results

def process_takeout(user_id: str, file_bytes: bytes):
    records = parse_takeout_zip(file_bytes)
    
    conn = _get_connection()
    for r in records:
        conn.execute(
            "INSERT OR REPLACE INTO health_metrics (id, user_id, timestamp, metric_type, value, unit, source, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), user_id, r["timestamp"], r["metric"], r["value"], r.get("unit", "bpm"), DataSource.google_health.value, "{}")
        )
    conn.commit()
    conn.close()
    
    return {"records_imported": len(records)}
