"""aegis FastAPI app — local-first open-source foundation."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.alerts import AlertEngine, AlertRule
from backend.charts import build_metric_trend, validate_chart_spec
from backend.config import get_settings
from backend.goals import GoalCreate, GoalStore
from backend.health.evidence import build_evidence_bundle
from backend.health.schema import SAFETY_DISCLAIMER, DataQuality, DataSource
from backend.health.store import (
    FitindexManualIn,
    HealthMetricsStore,
    ManualMetricIn,
)
from backend.intake.schema import IntakeResult
from backend.providers.llm import LocalLLMProvider
from backend.providers.memory import LocalMemoryProvider
from backend.providers.speech import LocalSpeechProvider
from backend.providers.tracing import init_tracing, start_span
from backend.reasoner import compose_directive
from backend.sync import SourceRegistry, SyncConfig
from backend.tools import HealthQueryTools

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"

app = FastAPI(title="aegis", version="0.5.0")
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
_sync = SourceRegistry()
_metrics = HealthMetricsStore()
_alerts = AlertEngine(metrics=_metrics)
_goals = GoalStore(metrics=_metrics)
_tools = HealthQueryTools(metrics=_metrics, alerts=_alerts, goals=_goals, sync=_sync, memory=_memory)


class TextUpdate(BaseModel):
    text: str = Field(..., min_length=1, description="Daily training/recovery/nutrition update")
    speak: bool = Field(False, description="Opt-in TTS for the directive")


class DirectiveResponse(BaseModel):
    intake: IntakeResult
    directive: str
    disclaimer: str
    scores: dict
    wod_decision: dict
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
        span.set_attribute("overall_score", composed["evidence"].get("overall"))
        return DirectiveResponse(
            intake=intake,
            directive=composed["directive"],
            disclaimer=composed.get("disclaimer") or SAFETY_DISCLAIMER,
            scores=composed["scores"],
            wod_decision=composed.get("wod_decision") or {},
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


class SourceEnableBody(BaseModel):
    enabled: bool


class SyncRequest(BaseModel):
    source_id: str | None = Field(
        None, description="Optional single source; omit to sync all enabled non-manual sources"
    )
    force: bool = False


@app.get("/api/sources")
def api_list_sources() -> dict:
    return _sync.snapshot()


@app.post("/api/sources/{source_id}/enable")
def api_enable_source(source_id: str, body: SourceEnableBody) -> dict:
    try:
        status = _sync.set_enabled(source_id, body.enabled)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown source: {source_id}") from exc
    return status.model_dump()


@app.get("/api/sync/config")
def api_get_sync_config() -> dict:
    return _sync.get_config().model_dump()


@app.put("/api/sync/config")
def api_put_sync_config(body: SyncConfig) -> dict:
    return _sync.set_config(body).model_dump()


@app.post("/api/sync")
def api_sync(body: SyncRequest | None = None) -> dict:
    """On-demand sync. External sources fail soft when not configured."""
    req = body or SyncRequest()
    with start_span("api.sync", source=req.source_id or "all"):
        if req.source_id:
            try:
                result = _sync.sync_one(req.source_id, force=req.force)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            return {"results": [result.model_dump()], "stale": [s.source_id.value for s in _sync.stale_sources()]}
        results = _sync.sync_all(only_enabled=not req.force)
        return {
            "results": [r.model_dump() for r in results],
            "stale": [s.source_id.value for s in _sync.stale_sources()],
        }


@app.get("/api/sync/history")
def api_sync_history(source_id: str | None = None, limit: int = 50) -> dict:
    entries = _sync.history(source_id=source_id, limit=limit)
    return {"history": [e.model_dump() for e in entries]}


@app.get("/api/sync/stale")
def api_sync_stale() -> dict:
    return {"stale": [s.model_dump() for s in _sync.stale_sources()]}


@app.get("/api/metrics")
def api_list_metrics() -> dict:
    return {"metrics": _metrics.list_metrics(), "count": _metrics.count()}


@app.get("/api/metrics/{metric}/latest")
def api_metric_latest(metric: str) -> dict:
    point = _metrics.latest(metric)
    if point is None:
        raise HTTPException(status_code=404, detail=f"No data for metric {metric}")
    return point.model_dump()


@app.get("/api/metrics/{metric}/series")
def api_metric_series(metric: str, limit: int = 100) -> dict:
    points = _metrics.series(metric, limit=limit)
    return {"metric": metric, "points": [p.model_dump() for p in points]}


@app.post("/api/metrics/manual")
def api_manual_metric(body: ManualMetricIn) -> dict:
    point = _metrics.add_manual(body)
    # bump manual source success
    try:
        _sync.sync_one("manual", force=True)
    except Exception:
        pass
    return point.model_dump()


@app.post("/api/ingest/fixture")
def api_ingest_fixture() -> dict:
    result = _metrics.ingest_fixture()
    _sync.sync_one("fixture", force=True)
    return result


@app.post("/api/fitindex/manual")
def api_fitindex_manual(body: FitindexManualIn) -> dict:
    """Create a FITINDEX draft for user review (not saved until confirm)."""
    draft = _metrics.fitindex_propose(body)
    return draft.model_dump()


@app.post("/api/fitindex/confirm/{draft_id}")
def api_fitindex_confirm(draft_id: str, body: FitindexManualIn | None = None) -> dict:
    try:
        if body is None:
            body = FitindexManualIn(confirmed=True)
        elif not body.confirmed:
            body = body.model_copy(update={"confirmed": True})
        return _metrics.fitindex_confirm(draft_id, body)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Unknown draft") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/fitindex/csv")
def api_fitindex_csv(body: dict) -> dict:
    """CSV text → review draft (must confirm before save)."""
    text = body.get("csv") or body.get("text") or ""
    try:
        draft = _metrics.ingest_fitindex_csv(text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return draft.model_dump()


@app.get("/api/alerts/rules")
def api_alert_rules() -> dict:
    return {"rules": [r.model_dump() for r in _alerts.list_rules()]}


@app.post("/api/alerts/rules")
def api_upsert_alert_rule(body: AlertRule) -> dict:
    body.custom = True
    return _alerts.upsert_rule(body).model_dump()


@app.post("/api/alerts/rules/{rule_id}/enable")
def api_enable_alert_rule(rule_id: str, body: dict) -> dict:
    try:
        return _alerts.set_enabled(rule_id, bool(body.get("enabled", True))).model_dump()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Unknown rule") from exc


@app.post("/api/alerts/evaluate")
def api_eval_alerts() -> dict:
    fired = _alerts.evaluate()
    return {
        "fired": [a.model_dump() for a in fired],
        "active": [a.model_dump() for a in _alerts.active()],
    }


@app.get("/api/alerts")
def api_alerts() -> dict:
    return {
        "active": [a.model_dump() for a in _alerts.active()],
        "history": [a.model_dump() for a in _alerts.history()],
    }


@app.post("/api/goals")
def api_create_goal(body: GoalCreate) -> dict:
    return _goals.create(body).model_dump()


@app.get("/api/goals")
def api_list_goals() -> dict:
    return {"goals": [g.model_dump() for g in _goals.list()], "bands": _goals.chart_bands()}


@app.post("/api/goals/{goal_id}/evaluate")
def api_eval_goal(goal_id: str) -> dict:
    try:
        return _goals.evaluate(goal_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Unknown goal") from exc


@app.post("/api/goals/{goal_id}/complete")
def api_complete_goal(goal_id: str) -> dict:
    try:
        return _goals.confirm_complete(goal_id).model_dump()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Unknown goal") from exc


@app.post("/api/goals/{goal_id}/abandon")
def api_abandon_goal(goal_id: str) -> dict:
    try:
        return _goals.abandon(goal_id).model_dump()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Unknown goal") from exc


@app.post("/api/tools/{tool_name}")
def api_tool(tool_name: str, body: dict | None = None) -> dict:
    body = body or {}
    return _tools.dispatch(tool_name, **body)


@app.get("/api/charts/{metric}")
def api_chart(metric: str) -> dict:
    spec = build_metric_trend(metric, metrics=_metrics, goals=_goals)
    return spec.model_dump()


@app.post("/api/charts/validate")
def api_validate_chart(body: dict) -> dict:
    try:
        return validate_chart_spec(body).model_dump()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/geo/status")
def api_geo_status() -> dict:
    # Location disabled by default; never sent to cloud LLM
    return {
        "enabled": False,
        "default": "off",
        "revocable": True,
        "cloud_llm": False,
        "detail": "Geolocation is opt-in and disabled by default.",
    }


@app.get("/api/environment")
def api_environment() -> dict:
    # Soft offline fixture when Open-Meteo unavailable
    return {
        "ok": True,
        "mode": "fixture",
        "weather": {"temp_c": 18, "conditions": "partly_cloudy"},
        "aqi": {"us_aqi": 42, "category": "Good"},
        "detail": "Offline fixture — live Open-Meteo optional later",
    }


@app.get("/")
def index() -> FileResponse:
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="frontend/index.html missing")
    return FileResponse(index_path)


@app.get("/manifest.webmanifest")
def manifest() -> FileResponse:
    path = FRONTEND_DIR / "manifest.webmanifest"
    if not path.exists():
        raise HTTPException(status_code=404, detail="manifest missing")
    return FileResponse(path, media_type="application/manifest+json")


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
