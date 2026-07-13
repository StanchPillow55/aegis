"""OpenTelemetry tracing and error capture utilities.

Replaces Sentry with local OTel + Jaeger.
"""

import os
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Optional
import logging

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

logger = logging.getLogger(__name__)

_otel_initialized = False
_tracer = trace.get_tracer(__name__)


def init_tracing() -> None:
    """Initialize OpenTelemetry SDK.

    If OTEL_EXPORTER_OTLP_ENDPOINT is not set, tracing falls back to console or no-op.
    """
    global _otel_initialized, _tracer

    if _otel_initialized:
        return

    resource = Resource.create({"service.name": "aegis"})
    provider = TracerProvider(resource=resource)

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

    try:
        exporter = OTLPSpanExporter(endpoint=endpoint)
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer(__name__)
        _otel_initialized = True
        logger.info(f"OpenTelemetry tracing initialized with endpoint {endpoint}")
    except Exception as e:
        logger.warning(f"Failed to initialize OTLP exporter: {e}")


def traced_span(name: str, **context: Any) -> Callable:
    """Decorator to wrap a function in an OpenTelemetry span.

    Args:
        name: Span name
        **context: Additional context to attach to the span
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not _otel_initialized:
                # If not initialized, try to init once lazily
                init_tracing()

            with _tracer.start_as_current_span(name) as span:
                for key, value in context.items():
                    span.set_attribute(key, str(value))
                return func(*args, **kwargs)

        return wrapper

    return decorator


@contextmanager
def traced_span_context(name: str, **context: Any):
    """Context manager to wrap a block in an OpenTelemetry span."""
    if not _otel_initialized:
        init_tracing()

    with _tracer.start_as_current_span(name) as span:
        for key, value in context.items():
            span.set_attribute(key, str(value))
        yield span


def capture_exception_with_context(error: Exception, **context: Any) -> None:
    """Capture an exception with additional context to the current span."""
    span = trace.get_current_span()
    if span.is_recording():
        span.record_exception(error)
        for key, value in context.items():
            span.set_attribute(f"error_context.{key}", str(value))
