"""Context package — typed screen context for GL5."""

from backend.context.screen import (
    PinRef,
    ScreenContext,
    parse_screen_context,
    screen_context_summary,
)

__all__ = [
    "PinRef",
    "ScreenContext",
    "parse_screen_context",
    "screen_context_summary",
]
