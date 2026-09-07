"""Local OpenTelemetry tracing scaffold (no Sentry required)."""

from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator


@dataclass
class Span:
    name: str
    trace_id: str
    span_id: str
    start_ns: int
    attributes: dict[str, Any] = field(default_factory=dict)
    end_ns: int | None = None
    status: str = "unset"

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def end(self, status: str = "ok") -> None:
        self.end_ns = time.time_ns()
        self.status = status

    @property
    def duration_ms(self) -> float:
        end = self.end_ns if self.end_ns is not None else time.time_ns()
        return (end - self.start_ns) / 1_000_000


class LocalTracer:
    """Minimal tracer that records spans in-memory and optionally prints them."""

    def __init__(self, service_name: str = "aegis", exporter: str = "console") -> None:
        self.service_name = service_name
        self.exporter = exporter
        self.spans: list[Span] = []

    def start_span(self, name: str, **attributes: Any) -> Span:
        span = Span(
            name=name,
            trace_id=uuid.uuid4().hex,
            span_id=uuid.uuid4().hex[:16],
            start_ns=time.time_ns(),
            attributes=dict(attributes),
        )
        self.spans.append(span)
        return span

    def export(self, span: Span) -> None:
        if self.exporter == "none":
            return
        # console exporter
        attrs = " ".join(f"{k}={v!r}" for k, v in span.attributes.items())
        print(
            f"[otel] service={self.service_name} span={span.name} "
            f"status={span.status} duration_ms={span.duration_ms:.2f} {attrs}".rstrip()
        )


_TRACER: LocalTracer | None = None


def init_tracing() -> LocalTracer:
    """Initialize (or return) the process-local tracer."""
    global _TRACER
    if _TRACER is not None:
        return _TRACER
    try:
        from backend.config import get_settings

        settings = get_settings()
        _TRACER = LocalTracer(
            service_name=settings.otel_service_name,
            exporter=settings.otel_exporter,
        )
    except Exception:
        _TRACER = LocalTracer()
    return _TRACER


@contextmanager
def start_span(name: str, **attributes: Any) -> Iterator[Span]:
    tracer = init_tracing()
    span = tracer.start_span(name, **attributes)
    try:
        yield span
        span.end("ok")
    except Exception:
        span.end("error")
        raise
    finally:
        tracer.export(span)
