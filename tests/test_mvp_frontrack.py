from tests.test_mvp_product_wave import test_wod_negotiation_substitutes_front_rack as test_mvp_frontrack
from backend.scorers.canonical import score_front_rack
from backend.intake.schema import IntakeResult


def test_front_rack_influences_score():
    limited = IntakeResult.model_validate(
        {
            "soreness": [{"body_part": "wrists", "severity": 5}],
            "sleep": {"quality": "good", "hours": 8},
            "meals": [{"description": "chicken", "protein_g": 40}],
            "todays_wod": {"movements": ["cleans"], "raw": "cleans"},
            "subjective_readiness": "moderate",
        }
    )
    open_ = IntakeResult.model_validate(
        {
            "soreness": [],
            "sleep": {"quality": "good", "hours": 8},
            "meals": [{"description": "chicken", "protein_g": 40}],
            "todays_wod": {"movements": ["cleans"], "raw": "cleans"},
            "subjective_readiness": "moderate",
        }
    )
    assert score_front_rack(limited)["score"] < score_front_rack(open_)["score"]
