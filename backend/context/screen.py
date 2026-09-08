"""GL5 — validated typed screen context (no raw HTML to the LLM)."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


_HTML_RE = re.compile(r"<[^>]+>")
_FORBIDDEN_KEYS = {"html", "script", "innerHTML", "outerHTML", "onclick", "onerror"}


def _strip_html(value: str) -> str:
    return _HTML_RE.sub("", value or "").strip()


class PinRef(BaseModel):
    id: str
    label: str = ""
    snippet: str = ""

    @field_validator("id", "label", "snippet", mode="before")
    @classmethod
    def clean_str(cls, v: Any) -> str:
        return _strip_html(str(v if v is not None else ""))[:240]


class DateRangeCtx(BaseModel):
    horizon: str | None = None
    start: float | None = None
    end: float | None = None


class ScreenContext(BaseModel):
    """Typed AIContextProvider payload — forbid HTML dumps."""

    model_config = {"extra": "ignore"}

    route: str = "/"
    panel: str = "overview"
    dashboard: str | None = None
    selected_goal_id: str | None = None
    selected_task_id: str | None = None
    selected_chart_metric: str | None = None
    date_range: DateRangeCtx | None = None
    filters: dict[str, Any] = Field(default_factory=dict)
    expanded_evidence: bool = False
    alerts_visible: bool = False
    stale_sources: list[str] = Field(default_factory=list)
    visible_progress: dict[str, Any] | None = None
    session_id: str | None = None
    pins: list[PinRef] = Field(default_factory=list)
    input: str | None = None  # composer | voice | …

    @field_validator(
        "route",
        "panel",
        "dashboard",
        "selected_goal_id",
        "selected_task_id",
        "selected_chart_metric",
        "session_id",
        "input",
        mode="before",
    )
    @classmethod
    def clean_optional_str(cls, v: Any) -> Any:
        if v is None:
            return None
        return _strip_html(str(v))[:120]

    @field_validator("stale_sources", mode="before")
    @classmethod
    def clean_stale(cls, v: Any) -> list[str]:
        if not v:
            return []
        return [_strip_html(str(x))[:64] for x in list(v)[:20]]

    @model_validator(mode="before")
    @classmethod
    def reject_html_payloads(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        lower_keys = {str(k).lower() for k in data}
        if lower_keys & _FORBIDDEN_KEYS:
            raise ValueError("Screen context must not include HTML/script fields")
        # Drop any nested html-ish blobs
        for key in list(data.keys()):
            if str(key).lower() in _FORBIDDEN_KEYS:
                raise ValueError(f"Forbidden context field: {key}")
        return data


def parse_screen_context(raw: dict[str, Any] | None) -> ScreenContext:
    """Validate and normalize client screen context."""
    return ScreenContext.model_validate(raw or {})


def screen_context_summary(ctx: ScreenContext) -> str:
    parts = [f"route={ctx.route}", f"panel={ctx.panel}"]
    if ctx.selected_goal_id:
        parts.append(f"goal={ctx.selected_goal_id}")
    if ctx.selected_task_id:
        parts.append(f"task={ctx.selected_task_id}")
    if ctx.selected_chart_metric:
        parts.append(f"chart={ctx.selected_chart_metric}")
    if ctx.date_range and ctx.date_range.horizon:
        parts.append(f"horizon={ctx.date_range.horizon}")
    if ctx.pins:
        parts.append("pins=" + ",".join(p.id for p in ctx.pins[:6]))
    if ctx.stale_sources:
        parts.append("stale=" + ",".join(ctx.stale_sources[:6]))
    return "; ".join(parts)
