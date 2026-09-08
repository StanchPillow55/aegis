# Aegis Goal Graph and Context-Aware Planning Layer

**Status:** In progress (GL0–GL3 fixture-verified 2026-09-08) · **Do not mark complete** without the tested path:  
`journal → evidence → suggestion → human approval → dashboard update`

**Related:** `docs/PRODUCT_SPEC.md` · `docs/IMPLEMENTATION_PLAN.md` · `docs/SC_MATURITY.md` · `success_criteria.yaml` (`GG-*`)

---

## 1. Product framing

This is **not** a Google Tasks clone. Aegis combines:

| Inspiration | Role in Aegis |
|---|---|
| Fitbit-style long-term progress | Trend charts, goal bands, multi-horizon dashboards |
| NotebookLM-style synthesis | Evidence-grounded explanations with citations |
| Google Tasks-style actions | Inbox / today / upcoming / completed task surfaces |
| Notion-style hierarchy | Editable Vision → Goal → Project → Milestone → Task tree |
| Aegis-specific | Health metrics, journal, RAG, screen-context, dual safety outputs |

**Core refinement:** Health data does not merely generate fixed scores. It explains how daily behavior affects **larger goals** and proposes the next useful action **without silently taking control**.

---

## 2. Product-model change — scores → pluggable signals

Fixed score cards (`front_rack`, `sleep`, `diet`, `workout_preparation`, `overall`) are **no longer the permanent universal dashboard contract**.

They become **pluggable, goal-relevant signal providers**. Preserve existing scorers as a backward-compatible signal layer.

| Signal id | Role when relevant |
|---|---|
| `front_rack` | Mobility / loaded upper-body readiness |
| `sleep` | Overnight recovery |
| `diet` | Fueling vs Macro Pool |
| `workout_preparation` | Readiness for today’s plan / WOD |
| `body_composition` | Weight / body-fat trends |
| `running_pace` | Conditioning / pace history |
| `strength` | Strength volume / progress |
| `hydration` | Hydration factor |
| `recovery` | Recovery / HRV / load |
| `activity_volume` | Steps / active minutes |
| `mobility` | Mobility habits |
| `environmental_exposure` | Weather / AQI / travel context |

**Dynamic selection inputs:** active goals · current tasks · recent journal · available metrics · selected dashboard view · current question · data freshness/confidence.

**Overall score** becomes **optional**. Prefer goal-specific progress + evidence summaries over one number representing “all of health.”

Dashboard and daily directive surface **whichever signals are relevant**, not a hardcoded four-card layout.

---

## 3. Conceptual hierarchy

```text
Vision
  → Goal
      → Project / objective
          → Milestone
              → Task
                  → Subtask
                      → Evidence and journal contributions
```

| Concept | Meaning |
|---|---|
| **Goal** | Desired outcome or maintained condition |
| **Task** | Actionable work item |
| **Metric** | Measured observation |
| **Journal entry** | User-reported evidence |
| **Suggestion** | Proposed mutation requiring confirmation |

Example (body composition):

```text
Vision: Maintain long-term functional longevity
Goal: Reduce body fat below 20%
  Project: Improve nutrition consistency
    Task: Log meals for the next 7 days
    Task: Review weekly protein average
    Milestone: Reach 20% body fat
  Evidence: FITINDEX body-fat · Fitbit weight · nutrition journal
```

---

## 4. Goal model

| Field | Notes |
|---|---|
| `id` | Stable id |
| `title` | Display title |
| `description` | Free text; preserve user’s original wording when extracted |
| `original_wording` | Optional verbatim user phrase |
| `goal_type` | `outcome` \| `process` \| `maintenance` \| `habit` \| `project` |
| `status` | `in_progress` \| `paused` \| `completed` \| `abandoned` |
| `parent_goal_id` | Hierarchy |
| `metric` / `target` / `unit` / `direction` | Optional quantitative binding |
| `direction` | `increase` \| `decrease` \| `maintain` \| `achieve` \| `avoid` |
| `timeframe` | Optional |
| `success_criteria` | Free text |
| `priority` | Ordinal / label |
| `origin` | `manual` \| `conversation` \| `journal` \| `imported` |
| `user_approved` | bool |
| `created_at` / `updated_at` | timestamps |

Vague goals are allowed (“I want to feel healthier”). Aegis may **suggest** clarifying definitions while preserving original wording in an editable structured draft.

---

## 5. Task model

| Field | Notes |
|---|---|
| `id` | Stable id |
| `title` / `description` | |
| `goal_id` | Parent goal |
| `parent_task_id` | Subtasks |
| `task_type` | `action` \| `milestone` \| `habit` \| `review` \| `data-entry` |
| `status` | `inbox` \| `proposed` \| `planned` \| `in_progress` \| `completed` \| `skipped` \| `canceled` |
| `priority` | |
| `due_date` | Optional |
| `recurrence` | Optional |
| `estimated_effort` | Optional |
| `source` | Origin channel |
| `user_approved` | bool |
| timestamps | created / updated / completed |

**Views:** Today · Upcoming · Inbox · Goals · Projects · Completed · Review suggestions.

Do **not** turn every journal statement into a task. Suggest only when the entry implies an actionable next step, unresolved commitment, recurring behavior, or useful review.

---

## 6. Journal → goal contribution pipeline

On new journal / directive intake:

1. Parse structured observations.  
2. RAG prior journal entries.  
3. Load active goals / projects / tasks / suggestions.  
4. Retrieve relevant health metrics (Fitbit, FITINDEX, Calendar, Takeout, env).  
5. Identify affected goals.  
6. Classify contribution: `positive` \| `negative` \| `neutral` \| `insufficient_evidence` \| `conflicting` (also `partial` when justified).  
7. Generate progress update draft.  
8. Generate task suggestions only when justified.  
9. Show evidence, assumptions, confidence.  
10. User **approve / edit / reject / defer** before state changes.

Example entry: *“Ate beef and rice, run was good, averaged 10:30 for 3 miles.”*

- Conditioning goal → positive (pace evidence)  
- Nutrition goal → partial (meal recorded; protein estimate needs confirm)  
- Running task → suggest pace tracking / weekly review  
- Recovery goal → insufficient evidence  
- Body-composition goal → no direct update  

---

## 7. Human-in-the-loop task management

Aegis may **suggest** create/rewrite/split/add/complete/reopen/replace/archive/merge/retire/habitize/convert — but must **never silently** perform meaningful goal/task mutations. This is a strict **human-in-the-loop** contract.

Every suggestion UI must show: proposed change · why · evidence · assumptions · confidence · affected entities · **Edit / Approve / Reject / Defer**.

Maintain revision / audit history.

---

## 8. Progress workspace

Horizons: Today · This week · This month · This year · All time.

Per goal: current/target state · progress % when meaningful · trend · goal line/band · milestones · related tasks · journal evidence · provenance · confidence/quality warnings · alerts · annotations.

Interactions: explain trend · cause · journal impact · create task from chart · update goal · add milestone · compare periods · filter sources · show missing/stale.

---

## 9. Screen context (typed)

Extend `AIContextProvider` with validated fields (no raw HTML dump):

route · dashboard · selected goal/task/chart/metric · date range · filters · expanded evidence · alerts · stale sources · visible progress · session id · pinned UI sections.

Chat must answer: “What am I looking at?”, “Why did this trend drop?”, “Does this entry help my goal?”, “Turn this chart into a task”, etc.

---

## 10. LLM tools (read vs mutate)

**Read-only:** list goal tree · goal progress/evidence · task inbox · tasks for goal · search journal/conversation · compare periods · explain chart · find stale/missing evidence.

**Mutation preview only until confirm:** propose goal/task changes · generate breakdown · preview rewrite · create/update/delete **after explicit confirmation**.

---

## 11. Safety / uncertainty language

Distinguish: observed data · user-stated · imported · derived · LLM interpretation · hypothesis · recommended action.

Prefer: “This may support…”, “Based on available entries…”, “Insufficient to determine…”, “Would you like to update the goal?”

Do not claim one journal entry proves long-term progress.

---

## 12. Completion bar (non-negotiable)

Placeholders / API stubs / empty UI **do not** complete this feature.

Required E2E (fixture-first, then browser):

1. Create goal from conversation  
2. Submit journal entry  
3. Retrieve prior evidence  
4. Propose goal contribution  
5. Suggest a task  
6. Edit + approve suggestion  
7. Dashboard + goal history update  
8. Screen-aware chat about the updated dashboard  
