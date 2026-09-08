"""aegis FastAPI app — local-first open-source foundation."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.alerts import AlertEngine, AlertRule
from backend.charts import build_metric_trend, validate_chart_spec
from backend.chat import ChatService, ChatTurnRequest, vision_status
from backend.config import get_settings
from backend.connectors import fitbit_oauth
from backend.connectors.calendar_signals import summarize_calendar_signals
from backend.connectors.fitindex_ocr import propose_from_image, propose_from_text_heuristic
from backend.connectors.status import enrich_source_status
from backend.connectors.takeout import ingest_takeout_bytes
from backend.environment import fetch_environment
from backend.goals import GoalCreate, GoalStore
from backend.health.evidence import build_evidence_bundle
from backend.health.schema import SAFETY_DISCLAIMER, DataQuality, DataSource
from backend.health.store import (
    FitindexManualIn,
    HealthMetricsStore,
    ManualMetricIn,
)
from backend.intake.schema import IntakeResult
from backend.intelligence.context import build_system_context, format_context_text
from backend.patterns.correlations import correlate_metrics, day_before_metric_performance
from backend.patterns.trends import trend_direction, weekly_metric_averages
from backend.providers.llm import LocalLLMProvider
from backend.providers.memory import LocalMemoryProvider
from backend.providers.speech import LocalSpeechProvider
from backend.providers.tracing import init_tracing, start_span
from backend.reasoner import compose_directive
from backend.sync import SourceRegistry, SyncConfig
from backend.tools import HealthQueryTools
from backend.tools.dates import parse_date_range

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"

app = FastAPI(title="aegis", version="0.7.0")
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
_chat = ChatService(tools=_tools)


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
    snap = _sync.snapshot()
    # mode=json so enums become strings before enrichment
    sources = []
    for s in _sync.list_sources():
        sources.append(enrich_source_status(s.model_dump(mode="json")))
    snap["sources"] = sources
    return snap


@app.post("/api/sources/{source_id}/enable")
def api_enable_source(source_id: str, body: SourceEnableBody) -> dict:
    try:
        status = _sync.set_enabled(source_id, body.enabled)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown source: {source_id}") from exc
    return enrich_source_status(status.model_dump())


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


@app.post("/api/fitindex/ocr")
async def api_fitindex_ocr(file: UploadFile = File(...)) -> dict:
    """Screenshot → OCR draft via local llava when available (confirm before save)."""
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty upload")
    with start_span("api.fitindex.ocr", bytes=len(data)):
        return propose_from_image(data, store=_metrics)


@app.post("/api/fitindex/text")
def api_fitindex_text(body: dict) -> dict:
    """NL body-comp text → heuristic draft (confirm before save)."""
    text = body.get("text") or ""
    if not text.strip():
        raise HTTPException(status_code=400, detail="text required")
    return propose_from_text_heuristic(text, store=_metrics).model_dump()


@app.get("/api/fitbit/status")
def api_fitbit_status() -> dict:
    return fitbit_oauth.status()


@app.get("/api/fitbit/auth")
def api_fitbit_auth() -> dict:
    url = fitbit_oauth.auth_url()
    if not url:
        return {
            **fitbit_oauth.status(),
            "detail": "Fitbit OAuth not configured — set FITBIT_CLIENT_ID and FITBIT_CLIENT_SECRET.",
        }
    return {"auth_url": url, **fitbit_oauth.status()}


@app.get("/api/fitbit/callback")
def api_fitbit_callback(code: str, redirect_uri: str | None = None) -> dict:
    result = fitbit_oauth.exchange_code(code, redirect_uri)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("detail") or "OAuth failed")
    return result


@app.post("/api/takeout/zip")
async def api_takeout_zip(file: UploadFile = File(...)) -> dict:
    """Upload a Google Takeout ZIP (future-compatible fallback)."""
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Expected a .zip Takeout archive")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty upload")
    with start_span("api.takeout.zip", bytes=len(data)):
        result = ingest_takeout_bytes(_metrics, data)
        try:
            _sync.set_enabled("takeout", True)
            _sync.sync_one("takeout", force=True)
        except Exception:
            pass
        return result


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
    """Live Open-Meteo when reachable; otherwise labeled offline/disabled."""
    return fetch_environment()


@app.post("/api/chat", response_model=None)
def api_chat(body: ChatTurnRequest) -> dict:
    with start_span("api.chat", chars=len(body.message)):
        return _chat.turn(body).model_dump()


@app.get("/api/chat/history")
def api_chat_history(limit: int = 40, session_id: str | None = None) -> dict:
    msgs = _chat.history(limit=limit, session_id=session_id)
    return {"messages": [m.model_dump() for m in msgs], "count": len(msgs), "session_id": session_id}


@app.get("/api/chat/sessions")
def api_chat_sessions() -> dict:
    return {"sessions": _chat.list_sessions()}


@app.get("/api/vision/status")
def api_vision_status() -> dict:
    return vision_status()


@app.get("/api/context/screen")
def api_screen_context(panel: str = "overview") -> dict:
    """Rich AIContext feed for chat (vitals, alerts, goals, sync, calendar)."""
    ctx = build_system_context(
        metrics=_metrics, alerts=_alerts, goals=_goals, sync=_sync, panel=panel
    )
    ctx["text"] = format_context_text(ctx)
    return ctx


@app.get("/api/patterns/trend/{metric}")
def api_pattern_trend(metric: str) -> dict:
    return trend_direction(metric, metrics=_metrics)


@app.get("/api/patterns/weekly/{metric}")
def api_pattern_weekly(metric: str) -> dict:
    return weekly_metric_averages(metric, metrics=_metrics)


@app.get("/api/patterns/correlate")
def api_pattern_correlate(metric_a: str, metric_b: str) -> dict:
    return correlate_metrics(metric_a, metric_b, metrics=_metrics)


@app.get("/api/patterns/predictors")
def api_pattern_predictors() -> dict:
    return day_before_metric_performance(metrics=_metrics)


@app.get("/api/calendar/signals")
def api_calendar_signals() -> dict:
    events = []
    for pt in _metrics.series("calendar_event", limit=40):
        events.append(pt.meta or {"value": pt.value})
    return summarize_calendar_signals(events)


@app.post("/api/tools/parse_date")
def api_parse_date(body: dict) -> dict:
    text = body.get("text") or body.get("query") or ""
    return parse_date_range(str(text))


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
