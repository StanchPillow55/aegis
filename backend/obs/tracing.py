"""Sentry tracing and error capture utilities.

Provides safe no-op wrappers when SENTRY_DSN is not configured.
"""

import os
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Optional

import sentry_sdk
from sentry_sdk import start_span
from sentry_sdk.integrations.redis import RedisIntegration

_sentry_initialized = False


def init_sentry() -> None:
    """Initialize Sentry SDK if SENTRY_DSN is configured.
    
    No-op if SENTRY_DSN is missing or empty.
    """
    global _sentry_initialized
    
    if _sentry_initialized:
        return
    
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        return
    
    sentry_sdk.init(
        dsn=dsn,
        integrations=[RedisIntegration()],
        traces_sample_rate=1.0,
    )
    _sentry_initialized = True


def traced_span(name: str, **context: Any) -> Callable:
    """Decorator to wrap a function in a Sentry span.
    
    Args:
        name: Span name
        **context: Additional context to attach to the span
        
    Returns:
        Decorator function
        
    Example:
        @traced_span("redis.store_log", operation="write")
        def store_log(data):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not _sentry_initialized:
                return func(*args, **kwargs)
            
            with start_span(op=name) as span:
                for key, value in context.items():
                    span.set_data(key, value)
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


@contextmanager
def traced_span_context(name: str, **context: Any):
    """Context manager to wrap a block in a Sentry span.
    
    Args:
        name: Span name
        **context: Additional context to attach to the span
        
    Example:
        with traced_span_context("browserbase.fetch", url="https://..."):
            page.goto(url)
    """
    if not _sentry_initialized:
        yield
        return
    
    with start_span(op=name) as span:
        for key, value in context.items():
            span.set_data(key, value)
        yield


def capture_exception_with_context(error: Exception, **context: Any) -> None:
    """Capture an exception with additional context.
    
    Args:
        error: The exception to capture
        **context: Additional context to attach to the event
    """
    if not _sentry_initialized:
        return
    
    with sentry_sdk.push_scope() as scope:
        for key, value in context.items():
            scope.set_extra(key, value)
        sentry_sdk.capture_exception(error)
