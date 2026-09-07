import pytest
from pydantic import ValidationError
from datetime import date

from src.backend.models.health_metrics import BodyComposition, DataSource
from src.backend.importers.fitindex import parse_csv, extract_from_text

def test_body_composition_validation():
    # Valid
    bc = BodyComposition(id="1", date=date.today(), weight=180, body_fat_pct=15, source=DataSource.fitindex)
    assert bc.weight == 180
    
    # Invalid weight
    with pytest.raises(ValidationError):
        BodyComposition(id="1", date=date.today(), weight=10, source=DataSource.fitindex)
        
    # Invalid body fat
    with pytest.raises(ValidationError):
        BodyComposition(id="1", date=date.today(), weight=180, body_fat_pct=0, source=DataSource.fitindex)

def test_parse_csv():
    csv_content = """Time,Weight(lb),BMI,Body Fat(%),Fat-free Body Weight(lb),Subcutaneous Fat(%),Visceral Fat,Body Water(%),Skeletal Muscle(%),Muscle Mass(lb),Bone Mass(lb),Protein(%),BMR(kcal),Metabolic Age
2024-05-12 08:00:00,183.0,24.5,21.0,144.5,15.0,8,55.0,40.0,138.0,6.5,18.0,1800,35"""
    
    results = parse_csv(csv_content)
    assert len(results) == 1
    r = results[0]
    assert r.weight == 183.0
    assert r.bmi == 24.5
    assert r.body_fat_pct == 21.0
    assert r.visceral_fat == 8.0
    assert r.metabolic_age == 35

@pytest.mark.asyncio
async def test_extract_from_text(mocker):
    mock_post = mocker.patch("src.backend.importers.fitindex.httpx.AsyncClient.post")
    mock_resp = mocker.MagicMock()
    mock_resp.json.return_value = {
        "response": '{"weight": 185.0, "body_fat_pct": 22.0}'
    }
    mock_post.return_value = mock_resp
    
    result = await extract_from_text("185 lbs, 22% body fat")
    assert result.weight == 185.0
    assert result.body_fat_pct == 22.0
