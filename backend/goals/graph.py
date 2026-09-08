"""Goal Graph schema (GL0) — hierarchy, tasks, suggestions, audit.

Compat metric-target ``GoalStore`` remains in ``backend.goals`` package init.
Meaningful mutations of graph entities that originate as suggestions must go
through approve/edit/reject/defer — never silent apply.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class GoalType(str, Enum):
    OUTCOME = "outcome"
    PROCESS = "process"
    MAINTENANCE = "maintenance"
    HABIT = "habit"
    PROJECT = "project"


class GraphGoalStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class GoalDirection(str, Enum):
    INCREASE = "increase"
    DECREASE = "decrease"
    MAINTAIN = "maintain"
    ACHIEVE = "achieve"
    AVOID = "avoid"


class GoalOrigin(str, Enum):
    MANUAL = "manual"
    CONVERSATION = "conversation"
    JOURNAL = "journal"
    IMPORTED = "imported"


class TaskType(str, Enum):
    ACTION = "action"
    MILESTONE = "milestone"
    HABIT = "habit"
    REVIEW = "review"
    DATA_ENTRY = "data-entry"


class TaskStatus(str, Enum):
    INBOX = "inbox"
    PROPOSED = "proposed"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    CANCELED = "canceled"


class ContributionEffect(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    PARTIAL = "partial"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    CONFLICTING = "conflicting"


class SuggestionKind(str, Enum):
    CREATE_GOAL = "create_goal"
    REWRITE_GOAL = "rewrite_goal"
    CREATE_TASK = "create_task"
    UPDATE_TASK = "update_task"
    COMPLETE_TASK = "complete_task"
    ARCHIVE = "archive"
    OTHER = "other"


class SuggestionDecision(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    EDITED = "edited"
    REJECTED = "rejected"
    DEFERRED = "deferred"


class GraphGoal(BaseModel):
    id: str
    title: str
    description: str = ""
    original_wording: str | None = None
    goal_type: GoalType = GoalType.OUTCOME
    status: GraphGoalStatus = GraphGoalStatus.IN_PROGRESS
    parent_goal_id: str | None = None
    metric: str | None = None
    target: float | None = None
    unit: str | None = None
    direction: GoalDirection | None = None
    timeframe: str | None = None
    success_criteria: str | None = None
    priority: int = 0
    origin: GoalOrigin = GoalOrigin.MANUAL
    user_approved: bool = True
    created_at: float
    updated_at: float


class GraphTask(BaseModel):
    id: str
    title: str
    description: str = ""
    goal_id: str
    parent_task_id: str | None = None
    task_type: TaskType = TaskType.ACTION
    status: TaskStatus = TaskStatus.INBOX
    priority: int = 0
    due_date: str | None = None
    recurrence: str | None = None
    estimated_effort: str | None = None
    source: str = "manual"
    user_approved: bool = True
    created_at: float
    updated_at: float
    completed_at: float | None = None


class EvidenceLink(BaseModel):
    id: str
    goal_id: str | None = None
    task_id: str | None = None
    kind: str  # metric | journal | chart | import | other
    ref: str
    snippet: str = ""
    created_at: float


class JournalContribution(BaseModel):
    id: str
    journal_ref: str
    goal_id: str
    effect: ContributionEffect
    evidence: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    confidence: str = "medium"  # low | medium | high
    proposed_update: str = ""
    user_decision: SuggestionDecision = SuggestionDecision.PENDING
    created_at: float
    decided_at: float | None = None


class Suggestion(BaseModel):
    id: str
    kind: SuggestionKind
    title: str
    reason: str
    evidence: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    confidence: str = "medium"
    affected_goal_id: str | None = None
    affected_task_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    decision: SuggestionDecision = SuggestionDecision.PENDING
    requires_confirmation: bool = True
    created_at: float
    decided_at: float | None = None


class AuditEntry(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    action: str
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    reason: str | None = None
    at: float


class GraphGoalCreate(BaseModel):
    title: str
    description: str = ""
    original_wording: str | None = None
    goal_type: GoalType = GoalType.OUTCOME
    parent_goal_id: str | None = None
    metric: str | None = None
    target: float | None = None
    unit: str | None = None
    direction: GoalDirection | None = None
    timeframe: str | None = None
    success_criteria: str | None = None
    priority: int = 0
    origin: GoalOrigin = GoalOrigin.MANUAL
    user_approved: bool = True


class GraphTaskCreate(BaseModel):
    title: str
    goal_id: str
    description: str = ""
    parent_task_id: str | None = None
    task_type: TaskType = TaskType.ACTION
    status: TaskStatus = TaskStatus.INBOX
    priority: int = 0
    due_date: str | None = None
    recurrence: str | None = None
    estimated_effort: str | None = None
    source: str = "manual"
    user_approved: bool = True


class SuggestionCreate(BaseModel):
    kind: SuggestionKind
    title: str
    reason: str
    evidence: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    confidence: str = "medium"
    affected_goal_id: str | None = None
    affected_task_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class GoalGraphStore:
    """SQLite-backed Goal Graph (GL0)."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is None:
            from backend.config import get_settings

            db_path = Path(get_settings().data_dir) / "aegis_goal_graph.sqlite3"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            for table, ddl in (
                (
                    "graph_goals",
                    """
                    CREATE TABLE IF NOT EXISTS graph_goals (
                        id TEXT PRIMARY KEY,
                        payload_json TEXT NOT NULL
                    )
                    """,
                ),
                (
                    "graph_tasks",
                    """
                    CREATE TABLE IF NOT EXISTS graph_tasks (
                        id TEXT PRIMARY KEY,
                        goal_id TEXT NOT NULL,
                        payload_json TEXT NOT NULL
                    )
                    """,
                ),
                (
                    "evidence_links",
                    """
                    CREATE TABLE IF NOT EXISTS evidence_links (
                        id TEXT PRIMARY KEY,
                        payload_json TEXT NOT NULL
                    )
                    """,
                ),
                (
                    "journal_contributions",
                    """
                    CREATE TABLE IF NOT EXISTS journal_contributions (
                        id TEXT PRIMARY KEY,
                        payload_json TEXT NOT NULL
                    )
                    """,
                ),
                (
                    "suggestions",
                    """
                    CREATE TABLE IF NOT EXISTS suggestions (
                        id TEXT PRIMARY KEY,
                        payload_json TEXT NOT NULL
                    )
                    """,
                ),
                (
                    "audit_log",
                    """
                    CREATE TABLE IF NOT EXISTS audit_log (
                        id TEXT PRIMARY KEY,
                        at REAL NOT NULL,
                        payload_json TEXT NOT NULL
                    )
                    """,
                ),
            ):
                conn.execute(ddl)
            conn.execute(
                "CREATE TABLE IF NOT EXISTS graph_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            conn.execute(
                "INSERT OR REPLACE INTO graph_meta(key, value) VALUES ('schema_version', '1')"
            )
            conn.commit()

    def schema_version(self) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM graph_meta WHERE key = 'schema_version'"
            ).fetchone()
        return int(row["value"]) if row else 0

    def _audit(
        self,
        *,
        entity_type: str,
        entity_id: str,
        action: str,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
        reason: str | None = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            id=uuid.uuid4().hex[:12],
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            before=before,
            after=after,
            reason=reason,
            at=time.time(),
        )
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO audit_log(id, at, payload_json) VALUES (?, ?, ?)",
                (entry.id, entry.at, entry.model_dump_json()),
            )
            conn.commit()
        return entry

    def audit_history(self, *, entity_id: str | None = None, limit: int = 50) -> list[AuditEntry]:
        limit = max(1, min(limit, 200))
        with self._connect() as conn:
            if entity_id:
                rows = conn.execute(
                    """
                    SELECT payload_json FROM audit_log
                    WHERE json_extract(payload_json, '$.entity_id') = ?
                    ORDER BY at DESC LIMIT ?
                    """,
                    (entity_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT payload_json FROM audit_log ORDER BY at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [AuditEntry.model_validate_json(r["payload_json"]) for r in rows]

    # --- Goals ---
    def create_goal(self, body: GraphGoalCreate) -> GraphGoal:
        now = time.time()
        goal = GraphGoal(
            id=uuid.uuid4().hex[:12],
            title=body.title,
            description=body.description,
            original_wording=body.original_wording,
            goal_type=body.goal_type,
            parent_goal_id=body.parent_goal_id,
            metric=body.metric,
            target=body.target,
            unit=body.unit,
            direction=body.direction,
            timeframe=body.timeframe,
            success_criteria=body.success_criteria,
            priority=body.priority,
            origin=body.origin,
            user_approved=body.user_approved,
            created_at=now,
            updated_at=now,
        )
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO graph_goals(id, payload_json) VALUES (?, ?)",
                (goal.id, goal.model_dump_json()),
            )
            conn.commit()
        self._audit(
            entity_type="goal",
            entity_id=goal.id,
            action="created",
            after=goal.model_dump(),
        )
        return goal

    def get_goal(self, goal_id: str) -> GraphGoal:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM graph_goals WHERE id = ?", (goal_id,)
            ).fetchone()
        if not row:
            raise KeyError(goal_id)
        return GraphGoal.model_validate_json(row["payload_json"])

    def list_goals(self) -> list[GraphGoal]:
        with self._connect() as conn:
            rows = conn.execute("SELECT payload_json FROM graph_goals").fetchall()
        goals = [GraphGoal.model_validate_json(r["payload_json"]) for r in rows]
        goals.sort(key=lambda g: (-g.priority, g.created_at))
        return goals

    def goal_tree(self) -> list[dict[str, Any]]:
        goals = self.list_goals()
        by_parent: dict[str | None, list[GraphGoal]] = {}
        for g in goals:
            by_parent.setdefault(g.parent_goal_id, []).append(g)

        def node(g: GraphGoal) -> dict[str, Any]:
            children = [node(c) for c in by_parent.get(g.id, [])]
            return {"goal": g.model_dump(), "children": children}

        return [node(g) for g in by_parent.get(None, [])]

    # --- Tasks ---
    def create_task(self, body: GraphTaskCreate) -> GraphTask:
        self.get_goal(body.goal_id)  # ensure exists
        now = time.time()
        task = GraphTask(
            id=uuid.uuid4().hex[:12],
            title=body.title,
            description=body.description,
            goal_id=body.goal_id,
            parent_task_id=body.parent_task_id,
            task_type=body.task_type,
            status=body.status,
            priority=body.priority,
            due_date=body.due_date,
            recurrence=body.recurrence,
            estimated_effort=body.estimated_effort,
            source=body.source,
            user_approved=body.user_approved,
            created_at=now,
            updated_at=now,
        )
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO graph_tasks(id, goal_id, payload_json) VALUES (?, ?, ?)",
                (task.id, task.goal_id, task.model_dump_json()),
            )
            conn.commit()
        self._audit(
            entity_type="task",
            entity_id=task.id,
            action="created",
            after=task.model_dump(),
        )
        return task

    def list_tasks(
        self, *, goal_id: str | None = None, status: TaskStatus | None = None
    ) -> list[GraphTask]:
        with self._connect() as conn:
            rows = conn.execute("SELECT payload_json FROM graph_tasks").fetchall()
        tasks = [GraphTask.model_validate_json(r["payload_json"]) for r in rows]
        if goal_id:
            tasks = [t for t in tasks if t.goal_id == goal_id]
        if status:
            tasks = [t for t in tasks if t.status == status]
        tasks.sort(key=lambda t: (-t.priority, t.created_at))
        return tasks

    def inbox(self) -> list[GraphTask]:
        return self.list_tasks(status=TaskStatus.INBOX) + self.list_tasks(
            status=TaskStatus.PROPOSED
        )

    # --- Evidence / contributions / suggestions ---
    def add_evidence_link(
        self,
        *,
        kind: str,
        ref: str,
        goal_id: str | None = None,
        task_id: str | None = None,
        snippet: str = "",
    ) -> EvidenceLink:
        link = EvidenceLink(
            id=uuid.uuid4().hex[:12],
            goal_id=goal_id,
            task_id=task_id,
            kind=kind,
            ref=ref,
            snippet=snippet,
            created_at=time.time(),
        )
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO evidence_links(id, payload_json) VALUES (?, ?)",
                (link.id, link.model_dump_json()),
            )
            conn.commit()
        return link

    def record_contribution(
        self,
        *,
        journal_ref: str,
        goal_id: str,
        effect: ContributionEffect,
        evidence: list[str] | None = None,
        assumptions: list[str] | None = None,
        confidence: str = "medium",
        proposed_update: str = "",
    ) -> JournalContribution:
        self.get_goal(goal_id)
        contrib = JournalContribution(
            id=uuid.uuid4().hex[:12],
            journal_ref=journal_ref,
            goal_id=goal_id,
            effect=effect,
            evidence=list(evidence or []),
            assumptions=list(assumptions or []),
            confidence=confidence,
            proposed_update=proposed_update,
            user_decision=SuggestionDecision.PENDING,
            created_at=time.time(),
        )
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO journal_contributions(id, payload_json) VALUES (?, ?)",
                (contrib.id, contrib.model_dump_json()),
            )
            conn.commit()
        self._audit(
            entity_type="contribution",
            entity_id=contrib.id,
            action="proposed",
            after=contrib.model_dump(),
        )
        return contrib

    def decide_contribution(
        self, contrib_id: str, decision: SuggestionDecision
    ) -> JournalContribution:
        if decision == SuggestionDecision.PENDING:
            raise ValueError("decision must not remain pending")
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM journal_contributions WHERE id = ?",
                (contrib_id,),
            ).fetchone()
        if not row:
            raise KeyError(contrib_id)
        before = JournalContribution.model_validate_json(row["payload_json"])
        after = before.model_copy(
            update={"user_decision": decision, "decided_at": time.time()}
        )
        with self._connect() as conn:
            conn.execute(
                "UPDATE journal_contributions SET payload_json = ? WHERE id = ?",
                (after.model_dump_json(), contrib_id),
            )
            conn.commit()
        self._audit(
            entity_type="contribution",
            entity_id=contrib_id,
            action=f"decision:{decision.value}",
            before=before.model_dump(),
            after=after.model_dump(),
        )
        return after

    def propose_suggestion(self, body: SuggestionCreate) -> Suggestion:
        sug = Suggestion(
            id=uuid.uuid4().hex[:12],
            kind=body.kind,
            title=body.title,
            reason=body.reason,
            evidence=list(body.evidence),
            assumptions=list(body.assumptions),
            confidence=body.confidence,
            affected_goal_id=body.affected_goal_id,
            affected_task_id=body.affected_task_id,
            payload=dict(body.payload),
            decision=SuggestionDecision.PENDING,
            requires_confirmation=True,
            created_at=time.time(),
        )
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO suggestions(id, payload_json) VALUES (?, ?)",
                (sug.id, sug.model_dump_json()),
            )
            conn.commit()
        self._audit(
            entity_type="suggestion",
            entity_id=sug.id,
            action="proposed",
            after=sug.model_dump(),
        )
        return sug

    def decide_suggestion(
        self,
        suggestion_id: str,
        decision: SuggestionDecision,
        *,
        edited_payload: dict[str, Any] | None = None,
    ) -> Suggestion:
        if decision == SuggestionDecision.PENDING:
            raise ValueError("decision must not remain pending")
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM suggestions WHERE id = ?",
                (suggestion_id,),
            ).fetchone()
        if not row:
            raise KeyError(suggestion_id)
        before = Suggestion.model_validate_json(row["payload_json"])
        updates: dict[str, Any] = {
            "decision": decision,
            "decided_at": time.time(),
        }
        if edited_payload is not None:
            updates["payload"] = edited_payload
            if decision == SuggestionDecision.APPROVED:
                updates["decision"] = SuggestionDecision.EDITED
        after = before.model_copy(update=updates)
        with self._connect() as conn:
            conn.execute(
                "UPDATE suggestions SET payload_json = ? WHERE id = ?",
                (after.model_dump_json(), suggestion_id),
            )
            conn.commit()
        # Apply create_task only after explicit approval/edit
        if after.decision in {SuggestionDecision.APPROVED, SuggestionDecision.EDITED}:
            if after.kind == SuggestionKind.CREATE_TASK and after.affected_goal_id:
                title = after.payload.get("title") or after.title
                self.create_task(
                    GraphTaskCreate(
                        title=str(title),
                        goal_id=after.affected_goal_id,
                        description=str(after.payload.get("description") or after.reason),
                        source="suggestion",
                        status=TaskStatus.PLANNED,
                        user_approved=True,
                    )
                )
        self._audit(
            entity_type="suggestion",
            entity_id=suggestion_id,
            action=f"decision:{after.decision.value}",
            before=before.model_dump(),
            after=after.model_dump(),
        )
        return after

    def list_suggestions(
        self, *, pending_only: bool = False
    ) -> list[Suggestion]:
        with self._connect() as conn:
            rows = conn.execute("SELECT payload_json FROM suggestions").fetchall()
        items = [Suggestion.model_validate_json(r["payload_json"]) for r in rows]
        if pending_only:
            items = [s for s in items if s.decision == SuggestionDecision.PENDING]
        items.sort(key=lambda s: s.created_at, reverse=True)
        return items

    def list_contributions(
        self, *, pending_only: bool = False
    ) -> list[JournalContribution]:
        with self._connect() as conn:
            rows = conn.execute("SELECT payload_json FROM journal_contributions").fetchall()
        items = [JournalContribution.model_validate_json(r["payload_json"]) for r in rows]
        if pending_only:
            items = [c for c in items if c.user_decision == SuggestionDecision.PENDING]
        items.sort(key=lambda c: c.created_at, reverse=True)
        return items

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version(),
            "goals": [g.model_dump() for g in self.list_goals()],
            "goal_tree": self.goal_tree(),
            "tasks": [t.model_dump() for t in self.list_tasks()],
            "suggestions_pending": [
                s.model_dump() for s in self.list_suggestions(pending_only=True)
            ],
            "contributions_pending": [
                c.model_dump() for c in self.list_contributions(pending_only=True)
            ],
            "audit": [a.model_dump() for a in self.audit_history(limit=20)],
        }
