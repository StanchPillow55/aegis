"""aegis FastAPI app — local-first open-source foundation."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.config import get_settings
from backend.intake.schema import IntakeResult
from backend.providers.llm import LocalLLMProvider
from backend.providers.memory import LocalMemoryProvider
from backend.providers.speech import LocalSpeechProvider
from backend.providers.tracing import init_tracing, start_span
from backend.reasoner import compose_directive

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"

app = FastAPI(title="aegis", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_tracer = init_tracing()
_llm = LocalLLMProvider()
_memory = LocalMemoryProvider()
_speech = LocalSpeechProvider()


class TextUpdate(BaseModel):
    text: str = Field(..., min_length=1, description="Daily training/recovery/nutrition update")
    speak: bool = Field(False, description="Opt-in TTS for the directive")


class DirectiveResponse(BaseModel):
    intake: IntakeResult
    directive: str
    scores: dict
    evidence: dict
    log_id: str
    tts: dict | None = None


@app.on_event("startup")
def _startup() -> None:
    get_settings()  # ensure data dir exists
    init_tracing()


@app.get("/health")
def health_check() -> dict:
    settings = get_settings()
    stt = _speech.stt_status()
    tts = _speech.tts_status()
    return {
        "status": "ok",
        "mode": settings.aegis_mode,
        "voice": {
            "stt": {"enabled": _speech.stt_enabled, "ready": stt.ok, "detail": stt.detail},
            "tts": {"enabled": _speech.tts_enabled, "ready": tts.ok, "detail": tts.detail},
        },
    }


@app.post("/api/intake", response_model=IntakeResult)
def api_intake(body: TextUpdate) -> IntakeResult:
    with start_span("api.intake", chars=len(body.text)) as span:
        intake = _llm.extract_intake(body.text)
        span.set_attribute("readiness", intake.subjective_readiness)
        return intake


@app.post("/api/directive", response_model=DirectiveResponse)
def api_directive(body: TextUpdate) -> DirectiveResponse:
    with start_span("api.directive", chars=len(body.text)) as span:
        intake = _llm.extract_intake(body.text)
        log_id = _memory.store(intake)
        hits = _memory.search(
            f"Readiness: {intake.subjective_readiness}",
            k=3,
        )
        # exclude the just-written log from context notes when identical
        context_notes = [
            h.content for h in hits if h.log_id != log_id
        ][:3]
        composed = compose_directive(intake, context_notes=context_notes)
        tts_payload = None
        if body.speak:
            spoken = _speech.synthesize(composed["directive"])
            tts_payload = {
                "ok": spoken.ok,
                "detail": spoken.detail,
                "audio_path": spoken.audio_path,
            }
        span.set_attribute("log_id", log_id)
        span.set_attribute("readiness_score", composed["evidence"]["readiness"])
        return DirectiveResponse(
            intake=intake,
            directive=composed["directive"],
            scores=composed["scores"],
            evidence=composed["evidence"],
            log_id=log_id,
            tts=tts_payload,
        )


@app.get("/api/logs/recent")
def api_recent_logs(n: int = 10) -> dict:
    n = max(1, min(n, 50))
    hits = _memory.recent(n)
    return {
        "logs": [
            {
                "log_id": h.log_id,
                "timestamp": h.timestamp,
                "content": h.content,
                "intake": h.intake,
            }
            for h in hits
        ]
    }


@app.get("/api/voice/status")
def api_voice_status() -> dict:
    stt = _speech.stt_status()
    tts = _speech.tts_status()
    return {
        "stt": {"enabled": _speech.stt_enabled, "ready": stt.ok, "detail": stt.detail},
        "tts": {"enabled": _speech.tts_enabled, "ready": tts.ok, "detail": tts.detail},
    }


@app.get("/")
def index() -> FileResponse:
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="frontend/index.html missing")
    return FileResponse(index_path)


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
