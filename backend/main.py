"""aegis FastAPI app — local-first open-source foundation."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.config import get_settings
from backend.health.evidence import build_evidence_bundle
from backend.health.schema import SAFETY_DISCLAIMER, DataQuality, DataSource
from backend.intake.schema import IntakeResult
from backend.providers.llm import LocalLLMProvider
from backend.providers.memory import LocalMemoryProvider
from backend.providers.speech import LocalSpeechProvider
from backend.providers.tracing import init_tracing, start_span
from backend.reasoner import compose_directive

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"

app = FastAPI(title="aegis", version="0.2.0")
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
    disclaimer: str
    scores: dict
    evidence: dict
    log_id: str
    extractor: str
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
        "schema_version": _memory.schema_version(),
        "voice": {
            "stt": {"enabled": _speech.stt_enabled, "ready": stt.ok, "detail": stt.detail},
            "tts": {"enabled": _speech.tts_enabled, "ready": tts.ok, "detail": tts.detail},
        },
    }


@app.post("/api/intake", response_model=IntakeResult)
def api_intake(body: TextUpdate) -> IntakeResult:
    with start_span("api.intake", chars=len(body.text)) as span:
        intake, extractor = _llm.extract_intake_with_meta(body.text)
        span.set_attribute("readiness", intake.subjective_readiness)
        span.set_attribute("extractor", extractor)
        return intake


@app.post("/api/directive", response_model=DirectiveResponse)
def api_directive(body: TextUpdate) -> DirectiveResponse:
    with start_span("api.directive", chars=len(body.text)) as span:
        intake, extractor = _llm.extract_intake_with_meta(body.text)
        source = (
            DataSource.OLLAMA_EXTRACT
            if extractor == "ollama"
            else DataSource.HEURISTIC_EXTRACT
        )
        log_id = _memory.store(
            intake,
            source=source,
            extractor=extractor,
            quality=DataQuality.MEDIUM if extractor == "ollama" else DataQuality.LOW,
        )
        hits = _memory.search(
            f"Readiness: {intake.subjective_readiness} sleep {intake.sleep.quality}",
            k=5,
            exclude_ids={log_id},
            dedupe=True,
        )
        history = [h.to_history_hit() for h in hits]
        bundle = build_evidence_bundle(
            intake=intake,
            log_id=log_id,
            history=history,
            extractor=extractor,
        )
        composed = compose_directive(
            intake,
            context_notes=[h.content for h in hits],
            evidence_bundle=bundle,
        )
        tts_payload = None
        if body.speak:
            spoken = _speech.synthesize(composed["directive"])
            tts_payload = {
                "ok": spoken.ok,
                "detail": spoken.detail,
                "audio_path": spoken.audio_path,
            }
        else:
            tts_payload = {
                "ok": False,
                "detail": "TTS not requested (speak=false).",
                "audio_path": None,
            }
        span.set_attribute("log_id", log_id)
        span.set_attribute("extractor", extractor)
        span.set_attribute("readiness_score", composed["evidence"]["readiness"])
        return DirectiveResponse(
            intake=intake,
            directive=composed["directive"],
            disclaimer=composed.get("disclaimer") or SAFETY_DISCLAIMER,
            scores=composed["scores"],
            evidence=composed["evidence"],
            log_id=log_id,
            extractor=extractor,
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
                "provenance": h.provenance,
                "content_hash": h.content_hash,
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
