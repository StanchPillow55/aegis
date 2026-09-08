"""Pluggable health signals (GL1)."""

from backend.signals.protocol import SignalContext, SignalResult
from backend.signals.providers import default_providers
from backend.signals.select import (
    SignalRegistry,
    build_context,
    get_registry,
    select_signals,
    signals_payload,
)

__all__ = [
    "SignalContext",
    "SignalRegistry",
    "SignalResult",
    "build_context",
    "default_providers",
    "get_registry",
    "select_signals",
    "signals_payload",
]
