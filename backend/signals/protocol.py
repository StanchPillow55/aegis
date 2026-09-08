"""Pluggable health signal providers (GL1).

Wraps existing scorers. Fixed FR/Sleep/Diet/WP/Overall remain available;
selection is dynamic based on goals/tasks/view. ``score_canonical`` stays
the MVP compat contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from backend.intake.schema import IntakeResult


@dataclass
class SignalContext:
    intake: IntakeResult
    active_goals: list[Any] = field(default_factory=list)
    active_tasks: list[Any] = field(default_factory=list)
    recent_text: str = ""
    view: str = "directive"  # directive | dashboard | ask
    include_overall: bool | None = None  # None = auto
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass
class SignalResult:
    id: str
    label: str
    score: int | None
    factors: dict[str, Any]
    rationale: str
    available: bool = True
    selected: bool = False
    relevance: str = ""  # why selected / skipped


class SignalProvider(Protocol):
    id: str
    label: str

    def compute(self, ctx: SignalContext) -> SignalResult: ...

    def relevant(self, ctx: SignalContext) -> tuple[bool, str]: ...
