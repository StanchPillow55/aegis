import pytest
import zipfile
import io
import json
from fastapi.testclient import TestClient

from src.backend.main import app

client = TestClient(app)

def test_takeout_upload():
    # Create a fake zip in memory
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        hr_data = {
            "Data Points": [
                {
                    "startTimeNanos": "1672531200000000000",
                    "endTimeNanos": "1672531200000000000",
                    "fitValue": [{"value": {"fpVal": 72.5}}]
                }
            ]
        }
        z.writestr('Takeout/Fit/All Data/derived_com.google.heart_rate.bpm_fake.json', json.dumps(hr_data))
        
    buf.seek(0)
    
    response = client.post(
        "/api/import/takeout",
        files={"file": ("export.zip", buf.read(), "application/zip")},
        headers={"X-User-ID": "test_user"}
    )
    
    assert response.status_code == 200
    assert response.json()["imported"] == 1
