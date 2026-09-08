"""Local chat grounded in health tools + screen context (no fake cloud success)."""

from __future__ import annotations

import re
import time
import uuid
from typing import Any

from pydantic import BaseModel, Field

from backend.health.schema import SAFETY_DISCLAIMER
from backend.tools import HealthQueryTools


class ChatMessage(BaseModel):
    role: str
    content: str
    at: float = Field(default_factory=time.time)
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)


class ChatTurnRequest(BaseModel):
    message: str = Field(..., min_length=1)
    screen_context: dict[str, Any] | None = None
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    history: list[ChatMessage] = Field(default_factory=list)
    session_id: str | None = None


class ChatTurnResponse(BaseModel):
    reply: str
    disclaimer: str
    citations: list[dict[str, Any]] = Field(default_factory=list)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    chart_hints: list[str] = Field(default_factory=list)
    vision: dict[str, Any] | None = None
    turn_id: str
    session_id: str


_METRIC_HINTS = {
    "sleep": "sleep_hours",
    "steps": "steps",
    "heart": "resting_hr",
    "hr": "resting_hr",
    "weight": "weight_kg",
    "spo2": "spo2",
    "hrv": "hrv",
    "calories": "calories",
    "distance": "distance",
}


def vision_status() -> dict[str, Any]:
    """Honest local vision readiness (Ollama llava optional)."""
    import json
    from urllib import error, request

    try:
        req = request.Request("http://127.0.0.1:11434/api/tags", method="GET")
        with request.urlopen(req, timeout=1.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        names = [m.get("name", "") for m in data.get("models") or []]
        llava = [n for n in names if "llava" in n.lower()]
        if llava:
            return {
                "available": True,
                "mode": "ollama_llava",
                "models": llava,
                "detail": "Local llava model detected.",
            }
        return {
            "available": False,
            "mode": "disabled",
            "models": names[:8],
            "detail": "Ollama running but no llava model; vision disabled.",
        }
    except (error.URLError, error.HTTPError, TimeoutError, OSError, ValueError):
        return {
            "available": False,
            "mode": "disabled",
            "models": [],
            "detail": "Vision disabled — Ollama/llava not available.",
        }


class ChatService:
    def __init__(self, tools: HealthQueryTools | None = None) -> None:
        self.tools = tools or HealthQueryTools()
        self._sessions: dict[str, list[ChatMessage]] = {}

    def history(self, limit: int = 40, session_id: str | None = None) -> list[ChatMessage]:
        if session_id:
            return (self._sessions.get(session_id) or [])[-limit:]
        # flatten recent across sessions
        all_msgs: list[ChatMessage] = []
        for msgs in self._sessions.values():
            all_msgs.extend(msgs)
        all_msgs.sort(key=lambda m: m.at)
        return all_msgs[-limit:]

    def list_sessions(self) -> list[dict[str, Any]]:
        out = []
        for sid, msgs in self._sessions.items():
            title = "Chat"
            for m in msgs:
                if m.role == "user" and m.content.strip():
                    title = m.content.strip()[:48]
                    break
            out.append({"session_id": sid, "message_count": len(msgs), "title": title})
        return out

    def turn(self, req: ChatTurnRequest) -> ChatTurnResponse:
        from backend.safety.guardrails import apply_guardrails

        session_id = req.session_id or str(uuid.uuid4())
        hist = self._sessions.setdefault(session_id, [])
        user = ChatMessage(
            role="user",
            content=req.message,
            attachments=list(req.attachments or []),
        )
        hist.append(user)

        tool_results: list[dict[str, Any]] = []
        citations: list[dict[str, Any]] = []
        chart_hints: list[str] = []
        lower = req.message.lower()

        metric = None
        for hint, name in _METRIC_HINTS.items():
            if hint in lower:
                metric = name
                break

        if any(w in lower for w in ("alert", "alerts")):
            out = self.tools.active_alerts()
            tool_results.append({"tool": "active_alerts", "result": out})
        if any(w in lower for w in ("goal", "goals", "progress")):
            out = self.tools.goal_progress()
            tool_results.append({"tool": "goal_progress", "result": out})
        if any(w in lower for w in ("sync", "stale", "source", "fresh")):
            out = self.tools.source_freshness()
            tool_results.append({"tool": "source_freshness", "result": out})
        if any(w in lower for w in ("body fat", "body composition", "weight")):
            out = self.tools.body_composition()
            tool_results.append({"tool": "body_composition", "result": out})
        if any(w in lower for w in ("calendar", "travel", "meeting")):
            out = self.tools.calendar_context()
            tool_results.append({"tool": "calendar_context", "result": out})
        if any(w in lower for w in ("correlat", "trend", "pattern")):
            out = self.tools.correlate("sleep_hours", "steps")
            tool_results.append({"tool": "correlate", "result": out})
            out2 = self.tools.trend("sleep_hours")
            tool_results.append({"tool": "trend", "result": out2})
        if metric:
            latest = self.tools.latest(metric)
            tool_results.append({"tool": "latest", "result": latest})
            if latest.get("value") is not None:
                citations.append(
                    {
                        "metric": metric,
                        "value": latest.get("value"),
                        "source": latest.get("source"),
                        "quality": latest.get("quality"),
                        "day": latest.get("day"),
                    }
                )
            chart_hints.append(metric)
            series = self.tools.series(metric, limit=14)
            tool_results.append({"tool": "series", "result": series})

        evidence = self.tools.evidence(req.message[:80])
        tool_results.append({"tool": "evidence", "result": evidence})
        for h in (evidence.get("history") or [])[:3]:
            citations.append(
                {
                    "record_id": h.get("record_id"),
                    "provenance": h.get("provenance"),
                    "snippet": (h.get("content") or "")[:120],
                }
            )

        vision = None
        if req.attachments:
            vision = vision_status()
            tool_results.append(
                {
                    "tool": "vision",
                    "result": {
                        "processed": False,
                        "detail": vision.get("detail"),
                        "attachment_count": len(req.attachments),
                        "available": vision.get("available"),
                    },
                }
            )

        reply = self._compose_reply(
            req.message,
            tool_results=tool_results,
            citations=citations,
            screen_context=req.screen_context,
            vision=vision,
        )
        goal_metrics = []
        try:
            for g in (self.tools.goal_progress().get("goals") or []):
                m = (g.get("goal") or {}).get("metric") or g.get("metric")
                if m:
                    goal_metrics.append(str(m))
        except Exception:
            pass
        reply = apply_guardrails(reply, goal_metrics)

        assistant = ChatMessage(
            role="assistant",
            content=reply,
            tool_results=tool_results,
        )
        hist.append(assistant)
        return ChatTurnResponse(
            reply=reply,
            disclaimer=SAFETY_DISCLAIMER,
            citations=citations,
            tool_results=tool_results,
            chart_hints=chart_hints,
            vision=vision,
            turn_id=str(uuid.uuid4()),
            session_id=session_id,
        )

    def _compose_reply(
        self,
        message: str,
        *,
        tool_results: list[dict[str, Any]],
        citations: list[dict[str, Any]],
        screen_context: dict[str, Any] | None,
        vision: dict[str, Any] | None,
    ) -> str:
        parts: list[str] = []
        if screen_context:
            panel = screen_context.get("panel") or screen_context.get("view")
            if panel:
                parts.append(f"(Context: viewing {panel}.)")

        metric_hit = next((t for t in tool_results if t.get("tool") == "latest"), None)
        if metric_hit:
            r = metric_hit["result"]
            if r.get("value") is None:
                parts.append(
                    f"I don't have stored data for {r.get('metric')} yet. "
                    "Sync a source or add a manual log."
                )
            else:
                parts.append(
                    f"{r.get('metric')} is {r.get('value')} "
                    f"(source={r.get('source')}, quality={r.get('quality')}"
                    f"{', day=' + str(r.get('day')) if r.get('day') else ''})."
                )

        alerts = next((t for t in tool_results if t.get("tool") == "active_alerts"), None)
        if alerts:
            n = len((alerts["result"].get("alerts") or []))
            parts.append(f"Active alerts: {n}.")

        goals = next((t for t in tool_results if t.get("tool") == "goal_progress"), None)
        if goals:
            gs = goals["result"].get("goals") or []
            parts.append(f"Tracked goals: {len(gs)}.")

        freshness = next((t for t in tool_results if t.get("tool") == "source_freshness"), None)
        if freshness:
            stale = [s for s in freshness["result"].get("sources") or [] if s.get("stale")]
            if stale:
                parts.append(
                    "Stale sources: " + ", ".join(s["source_id"] for s in stale) + "."
                )
            else:
                parts.append("No enabled sources are marked stale.")

        if vision and not vision.get("available") and any(
            t.get("tool") == "vision" for t in tool_results
        ):
            parts.append(f"Image note: {vision.get('detail')}")

        if not parts:
            if citations:
                parts.append(
                    "I found related history entries with provenance. "
                    "Ask about a metric (sleep, steps, heart), alerts, goals, or sync status."
                )
            else:
                parts.append(
                    "Ask about a metric (sleep, steps, HR), alerts, goals, or sync freshness. "
                    "Answers use local store data with source citations when available."
                )

        if citations:
            cited = []
            for c in citations[:3]:
                if c.get("metric"):
                    cited.append(f"{c['metric']}←{c.get('source')}")
                elif c.get("record_id"):
                    cited.append(str(c["record_id"])[:8])
            if cited:
                parts.append("Citations: " + ", ".join(cited) + ".")

        parts.append("Not medical advice — informational only.")
        return " ".join(parts)
