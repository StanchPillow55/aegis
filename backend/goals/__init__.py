"""Goal planning with confirmation-before-complete."""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from backend.health.store import HealthMetricsStore


class GoalStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    PAUSED = "paused"


class Goal(BaseModel):
    goal_id: str
    metric: str
    target: float
    direction: str = "lte"  # lte | gte
    timeframe: str | None = None
    success_criteria: str | None = None
    status: GoalStatus = GoalStatus.IN_PROGRESS
    created_at: float
    confirmation_state: str = "none"  # none | pending | confirmed
    history: list[dict[str, Any]] = Field(default_factory=list)


class GoalCreate(BaseModel):
    metric: str
    target: float
    direction: str = "lte"
    timeframe: str | None = None
    success_criteria: str | None = None


class GoalStore:
    def __init__(self, db_path: Path | str | None = None, metrics: HealthMetricsStore | None = None) -> None:
        if db_path is None:
            from backend.config import get_settings

            db_path = Path(get_settings().data_dir) / "aegis_goals.sqlite3"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.metrics = metrics or HealthMetricsStore()
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS goals (
                    goal_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def _save(self, goal: Goal) -> Goal:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO goals(goal_id, payload_json) VALUES (?, ?)",
                (goal.goal_id, goal.model_dump_json()),
            )
            conn.commit()
        return goal

    def create(self, body: GoalCreate) -> Goal:
        goal = Goal(
            goal_id=uuid.uuid4().hex[:12],
            metric=body.metric,
            target=body.target,
            direction=body.direction,
            timeframe=body.timeframe,
            success_criteria=body.success_criteria,
            created_at=time.time(),
            history=[{"event": "created", "at": time.time()}],
        )
        return self._save(goal)

    def list(self) -> list[Goal]:
        with self._connect() as conn:
            rows = conn.execute("SELECT payload_json FROM goals").fetchall()
        return [Goal.model_validate_json(r["payload_json"]) for r in rows]

    def get(self, goal_id: str) -> Goal:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM goals WHERE goal_id = ?", (goal_id,)
            ).fetchone()
        if not row:
            raise KeyError(goal_id)
        return Goal.model_validate_json(row["payload_json"])

    def _met(self, goal: Goal, value: float) -> bool:
        if goal.direction == "gte":
            return value >= goal.target
        return value <= goal.target

    def evaluate(self, goal_id: str) -> dict[str, Any]:
        goal = self.get(goal_id)
        latest = self.metrics.latest(goal.metric)
        if latest is None:
            return {"goal": goal.model_dump(), "possible_completion": False, "evidence": None}
        met = self._met(goal, latest.value)
        if met and goal.status == GoalStatus.IN_PROGRESS:
            goal.confirmation_state = "pending"
            goal.history.append(
                {
                    "event": "possible_completion",
                    "at": time.time(),
                    "value": latest.value,
                    "source": latest.provenance.source.value,
                }
            )
            self._save(goal)
        return {
            "goal": goal.model_dump(),
            "possible_completion": met and goal.status == GoalStatus.IN_PROGRESS,
            "evidence": latest.model_dump(),
        }

    def confirm_complete(self, goal_id: str) -> Goal:
        goal = self.get(goal_id)
        if goal.confirmation_state != "pending" and goal.status == GoalStatus.IN_PROGRESS:
            # allow manual complete
            pass
        goal.status = GoalStatus.COMPLETED
        goal.confirmation_state = "confirmed"
        goal.history.append({"event": "completed", "at": time.time()})
        return self._save(goal)

    def abandon(self, goal_id: str) -> Goal:
        goal = self.get(goal_id)
        goal.status = GoalStatus.ABANDONED
        goal.history.append({"event": "abandoned", "at": time.time()})
        return self._save(goal)

    def pause(self, goal_id: str) -> Goal:
        goal = self.get(goal_id)
        goal.status = GoalStatus.PAUSED
        goal.history.append({"event": "paused", "at": time.time()})
        return self._save(goal)

    def chart_bands(self) -> list[dict[str, Any]]:
        bands = []
        for g in self.list():
            if g.status in {GoalStatus.ABANDONED}:
                continue
            bands.append(
                {
                    "goal_id": g.goal_id,
                    "metric": g.metric,
                    "target": g.target,
                    "direction": g.direction,
                    "status": g.status.value,
                }
            )
        return bands
