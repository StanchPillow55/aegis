"""GL2 — journal → goal contribution engine (heuristic + HITL drafts).

Produces *proposals* only. Persisting contributions/suggestions never applies
goal/task mutations until the user approves/edits via GoalGraphStore decide_*.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from backend.goals.graph import (
    ContributionEffect,
    GoalGraphStore,
    GraphGoal,
    GraphGoalStatus,
    SuggestionCreate,
    SuggestionKind,
    TaskStatus,
)
from backend.signals.providers import PROVIDER_KEYWORDS


@dataclass
class ContributionDraft:
    goal_id: str
    goal_title: str
    effect: ContributionEffect
    evidence: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    confidence: str = "medium"
    proposed_update: str = ""


@dataclass
class TaskSuggestionDraft:
    title: str
    reason: str
    goal_id: str
    evidence: list[str] = field(default_factory=list)
    confidence: str = "medium"


@dataclass
class AnalysisResult:
    journal_ref: str
    text: str
    contributions: list[ContributionDraft] = field(default_factory=list)
    task_suggestions: list[TaskSuggestionDraft] = field(default_factory=list)
    prior_hits: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "journal_ref": self.journal_ref,
            "text": self.text,
            "goal_contributions": [
                {
                    "goal_id": c.goal_id,
                    "goal": c.goal_title,
                    "effect": c.effect.value,
                    "evidence": c.evidence,
                    "assumptions": c.assumptions,
                    "confidence": c.confidence,
                    "proposed_update": c.proposed_update,
                }
                for c in self.contributions
            ],
            "task_suggestions": [
                {
                    "title": t.title,
                    "reason": t.reason,
                    "goal_id": t.goal_id,
                    "evidence": t.evidence,
                    "confidence": t.confidence,
                    "requires_confirmation": True,
                }
                for t in self.task_suggestions
            ],
            "prior_hits": self.prior_hits,
            "notes": self.notes,
            "human_in_the_loop": True,
            "applied": False,
        }


_PACE_RE = re.compile(
    r"(?:averaged|avg|pace|at)\s*(\d{1,2})[:\.](\d{2})\s*(?:/?\s*(?:mi|mile|km))?",
    re.I,
)
_DISTANCE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:miles?|mi|km)\b", re.I)
_RUN_RE = re.compile(r"\b(run|ran|running|jog|jogged)\b", re.I)
_MEAL_RE = re.compile(
    r"\b(ate|eaten|meal|beef|chicken|rice|eggs|protein|dinner|lunch|breakfast)\b", re.I
)
_SLEEP_RE = re.compile(r"\b(slept|sleep|insomnia|restless)\b", re.I)
_NEGATIVE_RE = re.compile(
    r"\b(bad|poor|awful|terrible|missed|failed|skipped|injured|worse)\b", re.I
)
_POSITIVE_RE = re.compile(
    r"\b(good|great|solid|strong|pr|improved|better|consistent)\b", re.I
)


def _blob_for_goal(goal: GraphGoal) -> str:
    return " ".join(
        filter(
            None,
            [
                goal.title,
                goal.description,
                goal.metric or "",
                goal.original_wording or "",
                goal.success_criteria or "",
            ],
        )
    ).lower()


def _goal_themes(goal: GraphGoal) -> set[str]:
    themes: set[str] = set()
    blob = _blob_for_goal(goal)
    metric = (goal.metric or "").lower()
    if metric:
        themes.add(metric)
    for sid, kws in PROVIDER_KEYWORDS.items():
        if any(k in blob for k in kws) or metric == sid:
            themes.add(sid)
    # Soft aliases
    if any(w in blob for w in ("condition", "endurance", "cardio", "running")):
        themes.add("running_pace")
        themes.add("workout_preparation")
    if any(w in blob for w in ("nutrition", "diet", "protein", "meal")):
        themes.add("diet")
    if any(w in blob for w in ("body fat", "composition", "weight loss", "bf")):
        themes.add("body_composition")
    if any(w in blob for w in ("recover", "recovery", "rest")):
        themes.add("recovery")
    if any(w in blob for w in ("sleep",)):
        themes.add("sleep")
    return themes


def _entry_themes(text: str) -> dict[str, list[str]]:
    """Map theme → evidence snippets found in the entry."""
    t = text or ""
    out: dict[str, list[str]] = {}

    if _RUN_RE.search(t):
        out.setdefault("running_pace", []).append("Run activity mentioned")
        out.setdefault("workout_preparation", []).append("Training session mentioned")
        out.setdefault("activity_volume", []).append("Activity mentioned")
    pace = _PACE_RE.search(t)
    if pace:
        out.setdefault("running_pace", []).append(
            f"Average pace noted: {pace.group(1)}:{pace.group(2)}"
        )
    elif re.search(r"\bpace\b", t, re.I):
        out.setdefault("running_pace", []).append("Qualitative pace mentioned")
    dist = _DISTANCE_RE.search(t)
    if dist:
        out.setdefault("running_pace", []).append(f"Distance noted: {dist.group(0)}")
        out.setdefault("activity_volume", []).append(f"Distance noted: {dist.group(0)}")
    five_k = re.search(r"\b(\d+(?:\.\d+)?)\s*k\b", t, re.I)
    if five_k and not dist:
        snippet = f"Distance noted: {five_k.group(0)}"
        out.setdefault("running_pace", []).append(snippet)
        out.setdefault("activity_volume", []).append(snippet)

    if _MEAL_RE.search(t):
        foods = []
        for food in ("beef", "rice", "chicken", "eggs", "protein"):
            if re.search(rf"\b{food}\b", t, re.I):
                foods.append(food)
        snippet = "Meal recorded: " + (", ".join(foods) if foods else "food mentioned")
        out.setdefault("diet", []).append(snippet)
        out.setdefault("body_composition", [])  # may be insufficient

    if _SLEEP_RE.search(t):
        out.setdefault("sleep", []).append("Sleep mentioned in journal")
        out.setdefault("recovery", []).append("Sleep/rest mention")

    return out


def _classify(
    goal: GraphGoal,
    entry_themes: dict[str, list[str]],
    text: str,
) -> ContributionDraft | None:
    themes = _goal_themes(goal)
    if not themes:
        return None

    matched_evidence: list[str] = []
    matched_themes: list[str] = []
    for theme in themes:
        if theme not in entry_themes:
            continue
        if entry_themes[theme]:
            matched_evidence.extend(entry_themes[theme])
            matched_themes.append(theme)
        elif theme not in matched_themes:
            matched_themes.append(theme)

    # Prefer specific signal themes when several match
    priority = (
        "running_pace",
        "diet",
        "body_composition",
        "recovery",
        "sleep",
        "workout_preparation",
        "activity_volume",
    )
    matched_theme = None
    for pref in priority:
        if pref in matched_themes:
            matched_theme = pref
            break
    if matched_theme is None and matched_themes:
        matched_theme = matched_themes[0]

    # Deduplicate evidence snippets while preserving order
    if matched_evidence:
        seen: set[str] = set()
        deduped: list[str] = []
        for e in matched_evidence:
            if e not in seen:
                seen.add(e)
                deduped.append(e)
        matched_evidence = deduped

    if matched_theme is None and not any(t in entry_themes for t in themes):
        return None

    assumptions = [
        "Journal self-report is treated as user-stated evidence, not clinical measurement.",
        "Contribution is a draft until the user approves or edits it.",
    ]

    # Body composition with only a meal → insufficient / no direct update
    if "body_composition" in themes and matched_theme == "body_composition":
        if not any("weight" in e.lower() or "fat" in e.lower() for e in matched_evidence):
            return ContributionDraft(
                goal_id=goal.id,
                goal_title=goal.title,
                effect=ContributionEffect.INSUFFICIENT_EVIDENCE,
                evidence=matched_evidence or ["Meal logged without body-composition metric"],
                assumptions=assumptions
                + ["A single meal does not update body-composition progress."],
                confidence="low",
                proposed_update="No direct body-composition update from this entry",
            )

    # Diet with meal but no protein grams → partial
    if matched_theme == "diet":
        effect = ContributionEffect.PARTIAL
        confidence = "medium"
        if _NEGATIVE_RE.search(text) and not _POSITIVE_RE.search(text):
            effect = ContributionEffect.NEGATIVE
        proposed = "Record nutrition observation after user confirmation"
        if "protein" not in text.lower() and "g" not in text.lower():
            assumptions.append("Protein amount was not stated; estimate withheld.")
            proposed = "Record estimated protein only after user confirmation"
        return ContributionDraft(
            goal_id=goal.id,
            goal_title=goal.title,
            effect=effect,
            evidence=matched_evidence or ["Nutrition-related language in journal"],
            assumptions=assumptions,
            confidence=confidence,
            proposed_update=proposed,
        )

    # Running / conditioning
    if matched_theme in {"running_pace", "workout_preparation", "activity_volume"}:
        if matched_evidence:
            effect = ContributionEffect.POSITIVE
            if _NEGATIVE_RE.search(text) and not _POSITIVE_RE.search(text):
                effect = ContributionEffect.NEGATIVE
            return ContributionDraft(
                goal_id=goal.id,
                goal_title=goal.title,
                effect=effect,
                evidence=matched_evidence,
                assumptions=assumptions,
                confidence="high" if any("pace" in e.lower() for e in matched_evidence) else "medium",
                proposed_update="Add this session to the conditioning progress history",
            )
        return ContributionDraft(
            goal_id=goal.id,
            goal_title=goal.title,
            effect=ContributionEffect.INSUFFICIENT_EVIDENCE,
            evidence=[],
            assumptions=assumptions,
            confidence="low",
            proposed_update="Insufficient detail to update this goal",
        )

    # Recovery with no recovery markers
    if "recovery" in themes and matched_theme is None:
        return ContributionDraft(
            goal_id=goal.id,
            goal_title=goal.title,
            effect=ContributionEffect.INSUFFICIENT_EVIDENCE,
            evidence=[],
            assumptions=assumptions
            + ["Entry does not clearly address recovery markers (HRV, soreness, rest)."],
            confidence="low",
            proposed_update="Insufficient evidence for recovery goal",
        )

    if matched_evidence:
        effect = ContributionEffect.NEUTRAL
        if _POSITIVE_RE.search(text):
            effect = ContributionEffect.POSITIVE
        elif _NEGATIVE_RE.search(text):
            effect = ContributionEffect.NEGATIVE
        return ContributionDraft(
            goal_id=goal.id,
            goal_title=goal.title,
            effect=effect,
            evidence=matched_evidence,
            assumptions=assumptions,
            confidence="medium",
            proposed_update=f"Link journal evidence to goal '{goal.title}' after confirmation",
        )

    # Goal matched thematically but no evidence → insufficient
    if any(t in entry_themes for t in themes):
        return ContributionDraft(
            goal_id=goal.id,
            goal_title=goal.title,
            effect=ContributionEffect.INSUFFICIENT_EVIDENCE,
            evidence=[],
            assumptions=assumptions,
            confidence="low",
            proposed_update="Insufficient evidence to determine progress",
        )
    return None


def _task_suggestions_for(
    goal: GraphGoal,
    draft: ContributionDraft,
    text: str,
) -> list[TaskSuggestionDraft]:
    out: list[TaskSuggestionDraft] = []
    themes = _goal_themes(goal)
    # Only suggest when contribution is actionable / positive / partial
    if draft.effect in {
        ContributionEffect.INSUFFICIENT_EVIDENCE,
        ContributionEffect.NEUTRAL,
        ContributionEffect.CONFLICTING,
    }:
        return out

    if "running_pace" in themes and _RUN_RE.search(text):
        out.append(
            TaskSuggestionDraft(
                title="Review weekly running pace",
                reason="A new run was recorded in the journal",
                goal_id=goal.id,
                evidence=list(draft.evidence),
                confidence="medium",
            )
        )
    if "diet" in themes and _MEAL_RE.search(text):
        out.append(
            TaskSuggestionDraft(
                title="Review weekly protein average",
                reason="A nutrition observation was logged",
                goal_id=goal.id,
                evidence=list(draft.evidence),
                confidence="medium",
            )
        )
    return out


def analyze_journal_entry(
    text: str,
    *,
    store: GoalGraphStore,
    journal_ref: str,
    memory_hits: list[dict[str, Any]] | None = None,
) -> AnalysisResult:
    """Analyze text against active goals; return drafts only (not persisted)."""
    active = [
        g for g in store.list_goals() if g.status == GraphGoalStatus.IN_PROGRESS
    ]
    result = AnalysisResult(
        journal_ref=journal_ref,
        text=text,
        prior_hits=list(memory_hits or []),
    )
    if not active:
        result.notes.append(
            "No active goals yet — directive/scores still work; create a goal to enable contributions."
        )
        return result

    entry_themes = _entry_themes(text)
    for goal in active:
        draft = _classify(goal, entry_themes, text)
        if draft is None:
            # Explicit insufficient when goal is recovery-like and entry is training/nutrition only
            themes = _goal_themes(goal)
            if "recovery" in themes and not (
                "recovery" in entry_themes or "sleep" in entry_themes
            ):
                draft = ContributionDraft(
                    goal_id=goal.id,
                    goal_title=goal.title,
                    effect=ContributionEffect.INSUFFICIENT_EVIDENCE,
                    evidence=[],
                    assumptions=[
                        "Journal self-report is treated as user-stated evidence.",
                        "No recovery markers found in this entry.",
                    ],
                    confidence="low",
                    proposed_update="Insufficient evidence for recovery goal",
                )
            elif "body_composition" in themes and "diet" in entry_themes:
                draft = ContributionDraft(
                    goal_id=goal.id,
                    goal_title=goal.title,
                    effect=ContributionEffect.INSUFFICIENT_EVIDENCE,
                    evidence=entry_themes.get("diet") or [],
                    assumptions=[
                        "A meal alone is not a body-composition measurement.",
                    ],
                    confidence="low",
                    proposed_update="No direct body-composition update from this entry",
                )
            else:
                continue
        result.contributions.append(draft)
        result.task_suggestions.extend(_task_suggestions_for(goal, draft, text))

    if not result.contributions:
        result.notes.append("No active goals appeared related to this journal entry.")
    return result


def persist_analysis_as_pending(
    analysis: AnalysisResult, *, store: GoalGraphStore
) -> dict[str, Any]:
    """Write contribution + suggestion rows as PENDING (no mutations applied)."""
    contrib_ids = []
    suggestion_ids = []
    for c in analysis.contributions:
        saved = store.record_contribution(
            journal_ref=analysis.journal_ref,
            goal_id=c.goal_id,
            effect=c.effect,
            evidence=c.evidence,
            assumptions=c.assumptions,
            confidence=c.confidence,
            proposed_update=c.proposed_update,
        )
        contrib_ids.append(saved.id)
        store.add_evidence_link(
            kind="journal",
            ref=analysis.journal_ref,
            goal_id=c.goal_id,
            snippet=analysis.text[:240],
        )
    # Deduplicate task suggestions by title+goal
    seen: set[tuple[str, str]] = set()
    for t in analysis.task_suggestions:
        key = (t.title.lower(), t.goal_id)
        if key in seen:
            continue
        seen.add(key)
        # Skip if an open task with same title already exists
        existing = [
            x
            for x in store.list_tasks(goal_id=t.goal_id)
            if x.title.lower() == t.title.lower()
            and x.status
            not in {TaskStatus.COMPLETED, TaskStatus.CANCELED, TaskStatus.SKIPPED}
        ]
        if existing:
            continue
        sug = store.propose_suggestion(
            SuggestionCreate(
                kind=SuggestionKind.CREATE_TASK,
                title=t.title,
                reason=t.reason,
                evidence=t.evidence,
                assumptions=[
                    "Suggested from journal analysis; not created until approved."
                ],
                confidence=t.confidence,
                affected_goal_id=t.goal_id,
                payload={"title": t.title, "description": t.reason},
            )
        )
        suggestion_ids.append(sug.id)

    payload = analysis.to_dict()
    payload["persisted"] = {
        "contribution_ids": contrib_ids,
        "suggestion_ids": suggestion_ids,
    }
    return payload
