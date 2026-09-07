"""POST /api/intake — process a new daily entry."""

import logging
import uuid
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Header

from src.backend.extraction.ollama import extract_with_ollama
from src.backend.extraction.vision import extract_wod_from_image
from src.backend.models.intake import DailyLog, IntakeResult, ScoreSet
from src.backend.scorers import score_all
from src.backend.storage.sqlite_store import save_log
from src.backend.storage.chroma_store import store_embedding

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["intake"])


@router.post("/intake")
async def create_intake(
    text: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    entry_date: Optional[str] = Form(None),  # ISO format, defaults to today
    x_user_id: str = Header(...),
):
    """Process a new daily entry from text and/or image."""
    if not text and not image:
        raise HTTPException(status_code=400, detail="Provide text or image input")

    target_date = date.fromisoformat(entry_date) if entry_date else date.today()

    # Extract from text
    intake: Optional[IntakeResult] = None
    if text:
        try:
            intake = await extract_with_ollama(text)
        except Exception as e:
            logger.error(f"Ollama extraction failed: {e}")
            raise HTTPException(
                status_code=502,
                detail=f"Extraction failed: {str(e)}. Is Ollama running with llama3.2 pulled?",
            )

    # If image provided, extract WOD and merge
    if image:
        try:
            image_bytes = await image.read()
            wod = await extract_wod_from_image(image_bytes)
            if intake:
                intake.todays_wod = wod
            else:
                from src.backend.models.intake import Sleep
                intake = IntakeResult(sleep=Sleep(quality="not reported"), todays_wod=wod)
        except Exception as e:
            logger.error(f"Vision extraction failed: {e}")
            raise HTTPException(
                status_code=502,
                detail=f"Image extraction failed: {str(e)}. Is Ollama running with llava pulled?",
            )

    if intake is None:
        raise HTTPException(status_code=400, detail="Could not extract any data from input")

    # Score
    scores_raw = score_all(intake)
    scores = ScoreSet(
        sleep=scores_raw["sleep"]["score"],
        soreness=scores_raw["soreness"]["score"],
        diet=scores_raw["diet"]["score"],
        hydration=scores_raw["hydration"]["score"],
        performance=scores_raw["performance"]["score"],
        readiness=scores_raw["readiness"]["score"],
    )

    # Build and store the log
    log = DailyLog(
        id=f"{target_date.isoformat()}-{uuid.uuid4().hex[:8]}",
        date=target_date,
        created_at=datetime.now(timezone.utc),
        raw_input=text,
        intake=intake,
        scores=scores,
    )

    save_log(x_user_id, log)
    store_embedding(x_user_id, log)

    return {
        "id": log.id,
        "date": log.date.isoformat(),
        "scores": scores.model_dump(),
        "intake": intake.model_dump(),
    }
