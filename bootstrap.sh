#!/bin/bash
set -e

# ═══════════════════════════════════════════════════════════════════════
# aegis v2 bootstrap — run from the repo root
# ═══════════════════════════════════════════════════════════════════════

REPO="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO"

echo "╔═══════════════════════════════════════════╗"
echo "║   aegis v2 bootstrap                      ║"
echo "╚═══════════════════════════════════════════╝"

# ─── Phase 1: Move hackathon code to legacy/ ─────────────────────────
echo ""
echo "▶ Phase 1: Moving hackathon code to legacy/..."

mkdir -p legacy

# Move directories
for dir in backend council importer scripts tests legacy_hackathon; do
  [ -d "$dir" ] && mv "$dir" legacy/ && echo "  moved $dir/"
done

# Move hackathon files
HACK_FILES=(
  AGENT_HANDOFF.md CLAUDE.md pytest.ini success_criteria.yaml
  fix_14.py fix_and_merge.sh fix_prs.sh
  pr_body.txt pr13_output.txt pr14_output.txt pr15_output.txt
  qa_commands.sh qa_final_results.txt qa_results.txt
  qa_results_recent.txt qa_workflow_results.txt
  repair_13.py repair_14.py repair_15.py repair_all.sh
  run_final_qa.sh run_qa.sh run_qa_recent.sh run_qa_workflow.sh
  uagents_core.log
)
for f in "${HACK_FILES[@]}"; do
  [ -f "$f" ] && mv "$f" legacy/ && echo "  moved $f"
done

echo "  ✓ Hackathon code preserved in legacy/"


# ─── Phase 2: Create directory tree ──────────────────────────────────
echo ""
echo "▶ Phase 2: Creating src/ directory tree..."

mkdir -p src/backend/{models,extraction,scorers,storage,patterns,api,importers}
mkdir -p src/frontend
mkdir -p data
mkdir -p tests

echo "  ✓ Directory tree created"

# ─── Phase 3: Write Python backend files ─────────────────────────────
echo ""
echo "▶ Phase 3: Writing Python backend..."

# ─── pyproject.toml ───────────────────────────────────────────────────
cat > pyproject.toml << 'PYPROJECT'
[project]
name = "aegis"
version = "2.0.0"
description = "Voice-first fitness tracking copilot for functional longevity"
requires-python = ">=3.11"

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
PYPROJECT

# ─── requirements.txt ────────────────────────────────────────────────
cat > requirements.txt << 'REQS'
# Core
fastapi==0.115.0
uvicorn[standard]==0.30.6
pydantic==2.9.2
pydantic-settings==2.5.2

# Storage
chromadb==0.5.7
aiosqlite==0.20.0

# Extraction
httpx==0.27.2
ollama==0.3.3
Pillow==10.4.0

# Optional cloud extraction
anthropic==0.34.2

# Utilities
python-multipart==0.0.9
python-dotenv==1.0.1

# Testing
pytest==8.3.3
pytest-asyncio==0.24.0
REQS

# ─── .env.example ────────────────────────────────────────────────────
cat > .env.example << 'ENVEX'
# Aegis v2 Configuration
# Copy to .env and fill in as needed. NEVER commit .env.

# ─── Ollama (local, required) ───────────────────────────────────────
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
OLLAMA_VISION_MODEL=llava

# ─── Claude (optional cloud fallback) ──────────────────────────────
# ANTHROPIC_API_KEY=
# ANTHROPIC_MODEL=claude-haiku-4-5

# ─── Storage paths ──────────────────────────────────────────────────
SQLITE_DB_PATH=./data/aegis.db
CHROMA_PERSIST_DIR=./data/chroma

# ─── Fitbit (optional, for history import) ──────────────────────────
# FITBIT_CLIENT_ID=
# FITBIT_CLIENT_SECRET=

# ─── Server ─────────────────────────────────────────────────────────
HOST=0.0.0.0
PORT=8000
ENVEX

# ─── .gitignore (updated) ────────────────────────────────────────────
cat > .gitignore << 'GITIGNORE'
.env
__pycache__/
*.pyc
node_modules/
.venv/
dist/
.next/
data/
*.log
.DS_Store
GITIGNORE

# ─── src/backend/__init__.py ─────────────────────────────────────────
cat > src/__init__.py << 'EOF'
EOF

cat > src/backend/__init__.py << 'EOF'
"""aegis backend — voice-first fitness tracking copilot."""
EOF

# ─── src/backend/config.py ───────────────────────────────────────────
cat > src/backend/config.py << 'EOF'
"""Application settings loaded from environment / .env file."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Ollama (local LLM)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    ollama_vision_model: str = "llava"

    # Claude (optional cloud fallback)
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-haiku-4-5"

    # Storage
    sqlite_db_path: str = "./data/aegis.db"
    chroma_persist_dir: str = "./data/chroma"

    # Fitbit (optional)
    fitbit_client_id: str | None = None
    fitbit_client_secret: str | None = None

    # Server
    host: str = "0.0.0.0"
    port: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()
EOF

# ─── src/backend/models/__init__.py ──────────────────────────────────
cat > src/backend/models/__init__.py << 'EOF'
"""Core data models for aegis."""
from src.backend.models.intake import (
    IntakeResult,
    Sleep,
    Soreness,
    Meal,
    Hydration,
    WOD,
    WorkoutType,
    PerformanceLog,
    RoundSplit,
    DailyLog,
    ScoreSet,
    ReadinessLevel,
)

__all__ = [
    "IntakeResult", "Sleep", "Soreness", "Meal", "Hydration",
    "WOD", "WorkoutType", "PerformanceLog", "RoundSplit",
    "DailyLog", "ScoreSet", "ReadinessLevel",
]
EOF

# ─── src/backend/models/intake.py ────────────────────────────────────
cat > src/backend/models/intake.py << 'EOF'
"""Core data models for aegis.

These are the authoritative shapes for the entire system. Everything builds
against these: extraction, scoring, storage, API responses, and the frontend.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ReadinessLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class WorkoutType(str, Enum):
    AMRAP = "amrap"
    FOR_TIME = "for_time"
    EMOM = "emom"
    STRENGTH = "strength"
    CHIPPER = "chipper"
    INTERVAL = "interval"
    OTHER = "other"


class Soreness(BaseModel):
    body_part: str = Field(..., description="Body part, e.g. 'forearms', 'lower back'.")
    severity: int = Field(..., ge=1, le=5, description="1 (barely sore) to 5 (severe).")
    notes: Optional[str] = Field(None, description="Additional context.")


class Sleep(BaseModel):
    quality: str = Field(..., description="Subjective quality: 'good', 'poor', etc.")
    hours: Optional[float] = Field(None, description="Hours slept.")
    notes: Optional[str] = None


class Meal(BaseModel):
    description: str = Field(..., description="What was eaten.")
    protein_g: Optional[int] = Field(None, description="Protein in grams.")
    calories: Optional[int] = None
    timing: Optional[str] = Field(None, description="'breakfast', 'post-workout', etc.")


class Hydration(BaseModel):
    water_oz: Optional[float] = Field(None, description="Ounces of water.")
    alcohol_drinks: Optional[int] = Field(None, description="Number of alcoholic drinks.")
    notes: Optional[str] = None


class WOD(BaseModel):
    workout_type: Optional[WorkoutType] = None
    movements: list[str] = Field(default_factory=list)
    prescribed_weight: Optional[str] = None
    time_cap: Optional[int] = Field(None, description="Time cap in minutes.")
    rounds: Optional[int] = None
    raw: Optional[str] = Field(None, description="Raw WOD text.")


class RoundSplit(BaseModel):
    round_number: int
    time_seconds: Optional[float] = None
    reps_completed: Optional[int] = None
    notes: Optional[str] = None


class PerformanceLog(BaseModel):
    total_time_seconds: Optional[float] = None
    total_rounds: Optional[int] = None
    total_reps: Optional[int] = None
    rx: Optional[bool] = None
    scaled_notes: Optional[str] = None
    hr_avg: Optional[int] = None
    hr_max: Optional[int] = None
    rpe: Optional[int] = Field(None, ge=1, le=10)
    splits: list[RoundSplit] = Field(default_factory=list)
    rep_breakdown: Optional[str] = None
    feel: Optional[str] = None
    notes: Optional[str] = None


class IntakeResult(BaseModel):
    """Full structured result of parsing one daily update."""
    soreness: list[Soreness] = Field(default_factory=list)
    sleep: Sleep
    meals: list[Meal] = Field(default_factory=list)
    hydration: Optional[Hydration] = None
    todays_wod: Optional[WOD] = None
    performance: Optional[PerformanceLog] = None
    subjective_readiness: Optional[str] = None
    notes: Optional[str] = None


class ScoreSet(BaseModel):
    sleep: int = Field(..., ge=0, le=100)
    soreness: int = Field(..., ge=0, le=100)
    diet: int = Field(..., ge=0, le=100)
    hydration: int = Field(..., ge=0, le=100)
    performance: Optional[int] = Field(None, ge=0, le=100)
    readiness: int = Field(..., ge=0, le=100)


class DailyLog(BaseModel):
    """A complete persisted daily log."""
    id: str
    date: date
    created_at: datetime
    updated_at: Optional[datetime] = None
    raw_input: Optional[str] = None
    intake: IntakeResult
    scores: Optional[ScoreSet] = None
    summary_text: Optional[str] = None
EOF

# ─── src/backend/scorers/__init__.py ─────────────────────────────────
cat > src/backend/scorers/__init__.py << 'EOF'
"""Deterministic readiness scorers. Pure rule-based, no LLM."""
from src.backend.scorers.sleep import score_sleep
from src.backend.scorers.soreness import score_soreness
from src.backend.scorers.diet import score_diet
from src.backend.scorers.hydration import score_hydration
from src.backend.scorers.performance import score_performance
from src.backend.scorers.readiness import score_readiness

def score_all(intake) -> dict:
    """Run all scorers and return results keyed by dimension."""
    return {
        "sleep": score_sleep(intake),
        "soreness": score_soreness(intake),
        "diet": score_diet(intake),
        "hydration": score_hydration(intake),
        "performance": score_performance(intake),
        "readiness": score_readiness(intake),
    }

__all__ = [
    "score_sleep", "score_soreness", "score_diet",
    "score_hydration", "score_performance", "score_readiness",
    "score_all",
]
EOF

# ─── src/backend/scorers/sleep.py ────────────────────────────────────
cat > src/backend/scorers/sleep.py << 'EOF'
"""Sleep scorer. Higher = better recovered."""

from src.backend.models.intake import IntakeResult

_POSITIVE = {"great", "excellent", "amazing", "good", "solid", "deep", "well", "restful"}
_NEUTRAL = {"ok", "okay", "fair", "decent", "average", "meh", "fine", "alright"}
_NEGATIVE = {"poor", "bad", "terrible", "awful", "horrible", "broken", "rough", "barely"}


def _clamp(n: int) -> int:
    return max(0, min(100, n))


def _quality_score(quality: str | None) -> tuple[int, str]:
    q = (quality or "").lower()
    if any(w in q for w in _NEGATIVE):
        return 20, "poor"
    if any(w in q for w in _POSITIVE):
        return 88, "good"
    if any(w in q for w in _NEUTRAL):
        return 60, "neutral"
    if q:
        return 55, "unrecognized"
    return 50, "unknown"


def _hours_score(hours: float) -> int:
    if 7 <= hours <= 9:
        return 95
    if 6 <= hours < 7 or 9 < hours <= 10:
        return 75
    if 5 <= hours < 6:
        return 50
    if hours < 5:
        return 25
    return 60  # oversleep (>10h)


def score_sleep(intake: IntakeResult) -> dict:
    sleep = intake.sleep
    qscore, qband = _quality_score(sleep.quality)

    factors = {"quality": sleep.quality, "quality_band": qband, "quality_score": qscore, "hours": sleep.hours}

    if sleep.hours is not None:
        hscore = _hours_score(sleep.hours)
        factors["hours_score"] = hscore
        value = _clamp(round(0.5 * qscore + 0.5 * hscore))
    else:
        value = _clamp(qscore)

    return {"score": value, "factors": factors}
EOF

# ─── src/backend/scorers/soreness.py ─────────────────────────────────
cat > src/backend/scorers/soreness.py << 'EOF'
"""Soreness scorer. Higher = less sore = more recovered."""

from src.backend.models.intake import IntakeResult

_SEVERITY_PENALTY = {1: 8, 2: 18, 3: 30, 4: 45, 5: 60}
_PENALTY_CAP = 90


def _clamp(n: int) -> int:
    return max(0, min(100, n))


def score_soreness(intake: IntakeResult) -> dict:
    soreness = intake.soreness
    if not soreness:
        return {"score": 100, "factors": {"sore_areas": 0, "total_penalty": 0}}

    per_area = []
    for s in soreness:
        sev = max(1, min(5, s.severity))
        penalty = _SEVERITY_PENALTY[sev]
        per_area.append({"body_part": s.body_part, "severity": sev, "penalty": penalty})

    total_penalty = min(_PENALTY_CAP, sum(a["penalty"] for a in per_area))
    value = _clamp(100 - total_penalty)

    return {"score": value, "factors": {"sore_areas": len(soreness), "areas": per_area, "total_penalty": total_penalty}}
EOF

# ─── src/backend/scorers/diet.py ─────────────────────────────────────
cat > src/backend/scorers/diet.py << 'EOF'
"""Diet scorer. Higher = better fuelled."""

from src.backend.models.intake import IntakeResult, Meal

_PROTEIN_WORDS = {
    "chicken", "beef", "steak", "fish", "salmon", "tuna", "egg", "eggs",
    "tofu", "beans", "lentils", "turkey", "pork", "yogurt", "whey",
    "protein", "shake", "cottage",
}
_COUNT_SCORE = {0: 10, 1: 45, 2: 70, 3: 88}


def _clamp(n: int) -> int:
    return max(0, min(100, n))


def _has_protein(meal: Meal) -> bool:
    if meal.protein_g:
        return True
    return any(w in meal.description.lower() for w in _PROTEIN_WORDS)


def score_diet(intake: IntakeResult) -> dict:
    meals = intake.meals
    n = len(meals)
    count_score = _COUNT_SCORE.get(n, 95 if n >= 4 else 10)
    protein_count = sum(1 for m in meals if _has_protein(m))
    protein_ratio = (protein_count / n) if n else 0.0
    protein_bonus = round(protein_ratio * 10)
    value = _clamp(count_score + protein_bonus)

    return {"score": value, "factors": {"meal_count": n, "protein_meals": protein_count, "protein_bonus": protein_bonus}}
EOF

# ─── src/backend/scorers/hydration.py ────────────────────────────────
cat > src/backend/scorers/hydration.py << 'EOF'
"""Hydration scorer. Higher = better hydrated."""

from src.backend.models.intake import IntakeResult


def _clamp(n: int) -> int:
    return max(0, min(100, n))


def score_hydration(intake: IntakeResult) -> dict:
    h = intake.hydration
    if h is None:
        return {"score": 50, "factors": {"reported": False}}

    # Water scoring (target: 64-100oz for active male)
    water_score = 50
    if h.water_oz is not None:
        if h.water_oz >= 80:
            water_score = 95
        elif h.water_oz >= 64:
            water_score = 85
        elif h.water_oz >= 48:
            water_score = 70
        elif h.water_oz >= 32:
            water_score = 50
        else:
            water_score = 30

    # Alcohol penalty
    alcohol_penalty = 0
    if h.alcohol_drinks is not None:
        alcohol_penalty = min(40, h.alcohol_drinks * 15)

    value = _clamp(water_score - alcohol_penalty)
    return {
        "score": value,
        "factors": {
            "water_oz": h.water_oz,
            "water_score": water_score,
            "alcohol_drinks": h.alcohol_drinks,
            "alcohol_penalty": alcohol_penalty,
        },
    }
EOF

# ─── src/backend/scorers/performance.py ──────────────────────────────
cat > src/backend/scorers/performance.py << 'EOF'
"""Performance scorer. How well the workout went."""

from src.backend.models.intake import IntakeResult


def _clamp(n: int) -> int:
    return max(0, min(100, n))


_FEEL_POSITIVE = {"strong", "great", "good", "fast", "sharp", "solid", "smooth"}
_FEEL_NEUTRAL = {"ok", "okay", "decent", "average", "fine"}
_FEEL_NEGATIVE = {"bad", "sluggish", "gassed", "weak", "awful", "terrible", "slow", "heavy"}


def score_performance(intake: IntakeResult) -> dict:
    perf = intake.performance
    if perf is None:
        return {"score": None, "factors": {"logged": False}}

    components = []

    # RPE contribution (inverted: lower RPE with completion = good)
    if perf.rpe is not None:
        # RPE 6-7 with completion = peak performance zone
        if perf.rpe <= 7:
            components.append(90)
        elif perf.rpe <= 8:
            components.append(75)
        elif perf.rpe <= 9:
            components.append(55)
        else:
            components.append(35)

    # Rx bonus
    if perf.rx is True:
        components.append(90)
    elif perf.rx is False:
        components.append(60)

    # Feel
    if perf.feel:
        feel_lower = perf.feel.lower()
        if any(w in feel_lower for w in _FEEL_POSITIVE):
            components.append(90)
        elif any(w in feel_lower for w in _FEEL_NEGATIVE):
            components.append(30)
        elif any(w in feel_lower for w in _FEEL_NEUTRAL):
            components.append(60)

    # HR zone (max HR 170-185 typical for CrossFit = in the zone)
    if perf.hr_max is not None:
        if 160 <= perf.hr_max <= 185:
            components.append(85)
        elif perf.hr_max > 185:
            components.append(60)  # possibly overexerted
        else:
            components.append(70)

    if not components:
        return {"score": 50, "factors": {"logged": True, "insufficient_data": True}}

    value = _clamp(round(sum(components) / len(components)))
    return {"score": value, "factors": {"logged": True, "components": components}}
EOF

# ─── src/backend/scorers/readiness.py ────────────────────────────────
cat > src/backend/scorers/readiness.py << 'EOF'
"""Overall readiness scorer. Weighted blend of all sub-scores."""

from src.backend.models.intake import IntakeResult
from src.backend.scorers.sleep import score_sleep
from src.backend.scorers.soreness import score_soreness
from src.backend.scorers.diet import score_diet
from src.backend.scorers.hydration import score_hydration

_WEIGHTS = {"sleep": 0.30, "soreness": 0.30, "subjective": 0.20, "diet": 0.10, "hydration": 0.10}
_SUBJECTIVE_MAP = {"low": 25, "moderate": 60, "high": 90}
_SUBJECTIVE_POS = {"great", "good", "ready", "fresh", "strong"}
_SUBJECTIVE_NEG = {"low", "poor", "bad", "tired", "exhausted", "drained", "flat"}


def _clamp(n: int) -> int:
    return max(0, min(100, n))


def _subjective_score(label: str | None) -> int:
    s = (label or "").lower().strip()
    if s in _SUBJECTIVE_MAP:
        return _SUBJECTIVE_MAP[s]
    if any(w in s for w in _SUBJECTIVE_NEG):
        return 25
    if any(w in s for w in _SUBJECTIVE_POS):
        return 80
    return 55  # unknown / not stated


def score_readiness(intake: IntakeResult) -> dict:
    sleep_s = score_sleep(intake)["score"]
    soreness_s = score_soreness(intake)["score"]
    diet_s = score_diet(intake)["score"]
    hydration_s = score_hydration(intake)["score"]
    subjective_s = _subjective_score(intake.subjective_readiness)

    components = {
        "sleep": sleep_s,
        "soreness": soreness_s,
        "diet": diet_s,
        "hydration": hydration_s,
        "subjective": subjective_s,
    }

    value = _clamp(round(
        sleep_s * _WEIGHTS["sleep"]
        + soreness_s * _WEIGHTS["soreness"]
        + diet_s * _WEIGHTS["diet"]
        + hydration_s * _WEIGHTS["hydration"]
        + subjective_s * _WEIGHTS["subjective"]
    ))

    return {"score": value, "factors": {"components": components, "weights": _WEIGHTS}}
EOF

# ─── src/backend/extraction/__init__.py ──────────────────────────────
cat > src/backend/extraction/__init__.py << 'EOF'
"""Extraction: turn free text or images into structured IntakeResult."""
EOF

# ─── src/backend/extraction/ollama.py ────────────────────────────────
cat > src/backend/extraction/ollama.py << 'EOF'
"""Ollama-based extraction using Llama 3.2 with structured JSON output."""

import json
from typing import Optional

import httpx

from src.backend.config import get_settings
from src.backend.models.intake import IntakeResult

_SYSTEM_PROMPT = """You are the intake parser for a voice-first training copilot. The user speaks a short daily update covering sleep, soreness, nutrition, hydration, and workout details.

Extract ONLY what is stated or clearly implied. Do not invent details.

Return a JSON object matching this exact structure:
{
  "soreness": [{"body_part": "string", "severity": 1-5, "notes": "optional"}],
  "sleep": {"quality": "string", "hours": number_or_null, "notes": "optional"},
  "meals": [{"description": "string", "protein_g": number_or_null, "calories": number_or_null, "timing": "optional"}],
  "hydration": {"water_oz": number_or_null, "alcohol_drinks": number_or_null, "notes": "optional"},
  "todays_wod": {"workout_type": "amrap|for_time|emom|strength|chipper|interval|other", "movements": ["list"], "prescribed_weight": "optional", "time_cap": number_or_null, "rounds": number_or_null, "raw": "optional"},
  "performance": {"total_time_seconds": number_or_null, "total_rounds": number_or_null, "total_reps": number_or_null, "rx": bool_or_null, "scaled_notes": "optional", "hr_avg": number_or_null, "hr_max": number_or_null, "rpe": 1-10_or_null, "splits": [], "rep_breakdown": "optional", "feel": "optional", "notes": "optional"},
  "subjective_readiness": "low|moderate|high",
  "notes": "optional"
}

Rules:
- severity is 1 (barely sore) to 5 (severe)
- For subjective_readiness, infer from overall tone if not stated explicitly
- Convert time formats: "8:42" = 522 seconds
- Omit fields that weren't mentioned (use null)
- Return ONLY valid JSON, no markdown fences or explanation
"""


async def extract_with_ollama(
    text: str,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> IntakeResult:
    """Extract structured intake from free text using Ollama."""
    settings = get_settings()
    url = base_url or settings.ollama_base_url
    mdl = model or settings.ollama_model

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{url}/api/generate",
            json={
                "model": mdl,
                "prompt": text,
                "system": _SYSTEM_PROMPT,
                "stream": False,
                "format": "json",
            },
        )
        response.raise_for_status()
        result = response.json()

    raw_text = result.get("response", "")
    parsed = json.loads(raw_text)
    return IntakeResult.model_validate(parsed)
EOF

# ─── src/backend/extraction/claude.py ────────────────────────────────
cat > src/backend/extraction/claude.py << 'EOF'
"""Claude Haiku extraction fallback (optional cloud path)."""

from typing import Any, Optional

import anthropic

from src.backend.config import get_settings
from src.backend.models.intake import IntakeResult

_SYSTEM = (
    "You are the intake parser for a voice-first training copilot. The user "
    "speaks a short daily update covering sleep, soreness, nutrition, hydration, "
    "and workout performance. Extract ONLY what is stated or clearly implied. "
    "Call the record_intake tool exactly once."
)

_TOOL_NAME = "record_intake"


def _tool_definition() -> dict[str, Any]:
    return {
        "name": _TOOL_NAME,
        "description": "Record structured daily training/recovery/nutrition intake.",
        "input_schema": IntakeResult.model_json_schema(),
    }


async def extract_with_claude(
    text: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> IntakeResult:
    """Extract structured intake using Claude tool-use."""
    settings = get_settings()
    key = api_key or settings.anthropic_api_key
    if not key:
        raise ValueError("ANTHROPIC_API_KEY not configured")

    mdl = model or settings.anthropic_model
    client = anthropic.Anthropic(api_key=key)

    response = client.messages.create(
        model=mdl,
        max_tokens=1024,
        temperature=0,
        system=_SYSTEM,
        tools=[_tool_definition()],
        tool_choice={"type": "tool", "name": _TOOL_NAME},
        messages=[{"role": "user", "content": text}],
    )

    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == _TOOL_NAME:
            return IntakeResult.model_validate(block.input)

    raise ValueError("Claude returned no tool call")
EOF

# ─── src/backend/extraction/vision.py ────────────────────────────────
cat > src/backend/extraction/vision.py << 'EOF'
"""Vision extraction: screenshot/image -> WOD structure using Ollama multimodal."""

import base64
import json
from pathlib import Path
from typing import Optional

import httpx

from src.backend.config import get_settings
from src.backend.models.intake import WOD

_VISION_PROMPT = """Look at this CrossFit workout screenshot and extract the workout details.

Return JSON:
{
  "workout_type": "amrap|for_time|emom|strength|chipper|interval|other",
  "movements": ["movement1", "movement2"],
  "prescribed_weight": "e.g. 135/95 or null",
  "time_cap": minutes_or_null,
  "rounds": number_or_null,
  "raw": "the full workout text as shown"
}

Return ONLY valid JSON."""


async def extract_wod_from_image(
    image_bytes: bytes,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> WOD:
    """Extract WOD from a screenshot using Ollama vision model."""
    settings = get_settings()
    url = base_url or settings.ollama_base_url
    mdl = model or settings.ollama_vision_model

    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{url}/api/generate",
            json={
                "model": mdl,
                "prompt": _VISION_PROMPT,
                "images": [b64_image],
                "stream": False,
                "format": "json",
            },
        )
        response.raise_for_status()
        result = response.json()

    raw_text = result.get("response", "")
    parsed = json.loads(raw_text)
    return WOD.model_validate(parsed)
EOF

# ─── src/backend/storage/__init__.py ─────────────────────────────────
cat > src/backend/storage/__init__.py << 'EOF'
"""Storage layer: SQLite for structured data, ChromaDB for vectors."""
EOF

# ─── src/backend/storage/sqlite_store.py ─────────────────────────────
cat > src/backend/storage/sqlite_store.py << 'EOF'
"""SQLite storage for daily logs, scores, and time-series queries."""

import json
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from src.backend.config import get_settings
from src.backend.models.intake import DailyLog, IntakeResult, ScoreSet


def _get_db_path() -> Path:
    settings = get_settings()
    path = Path(settings.sqlite_db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _get_connection() -> sqlite3.Connection:
    db_path = _get_db_path()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    """Create tables if they don't exist."""
    conn = _get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS daily_logs (
            id TEXT PRIMARY KEY,
            date TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            updated_at TEXT,
            raw_input TEXT,
            intake_json TEXT NOT NULL,
            scores_json TEXT,
            summary_text TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_logs_date ON daily_logs(date);

        CREATE TABLE IF NOT EXISTS score_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_id TEXT NOT NULL REFERENCES daily_logs(id),
            date TEXT NOT NULL,
            sleep INTEGER,
            soreness INTEGER,
            diet INTEGER,
            hydration INTEGER,
            performance INTEGER,
            readiness INTEGER
        );

        CREATE INDEX IF NOT EXISTS idx_scores_date ON score_history(date);
    """)
    conn.commit()
    conn.close()


def save_log(log: DailyLog) -> str:
    """Insert or update a daily log."""
    conn = _get_connection()
    scores_json = log.scores.model_dump_json() if log.scores else None

    conn.execute("""
        INSERT INTO daily_logs (id, date, created_at, updated_at, raw_input, intake_json, scores_json, summary_text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(date) DO UPDATE SET
            updated_at = excluded.updated_at,
            raw_input = excluded.raw_input,
            intake_json = excluded.intake_json,
            scores_json = excluded.scores_json,
            summary_text = excluded.summary_text
    """, (
        log.id, log.date.isoformat(), log.created_at.isoformat(),
        log.updated_at.isoformat() if log.updated_at else None,
        log.raw_input, log.intake.model_dump_json(), scores_json, log.summary_text,
    ))

    if log.scores:
        conn.execute("""
            INSERT OR REPLACE INTO score_history (log_id, date, sleep, soreness, diet, hydration, performance, readiness)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            log.id, log.date.isoformat(),
            log.scores.sleep, log.scores.soreness, log.scores.diet,
            log.scores.hydration, log.scores.performance, log.scores.readiness,
        ))

    conn.commit()
    conn.close()
    return log.id


def get_log_by_date(d: date) -> Optional[DailyLog]:
    """Retrieve a single day's log."""
    conn = _get_connection()
    row = conn.execute("SELECT * FROM daily_logs WHERE date = ?", (d.isoformat(),)).fetchone()
    conn.close()
    if not row:
        return None
    return _row_to_log(row)


def get_logs_range(start: date, end: date) -> list[DailyLog]:
    """Get all logs in a date range (inclusive)."""
    conn = _get_connection()
    rows = conn.execute(
        "SELECT * FROM daily_logs WHERE date >= ? AND date <= ? ORDER BY date",
        (start.isoformat(), end.isoformat()),
    ).fetchall()
    conn.close()
    return [_row_to_log(r) for r in rows]


def get_scores_range(start: date, end: date) -> list[dict]:
    """Get score time-series for trend charts."""
    conn = _get_connection()
    rows = conn.execute(
        "SELECT * FROM score_history WHERE date >= ? AND date <= ? ORDER BY date",
        (start.isoformat(), end.isoformat()),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _row_to_log(row) -> DailyLog:
    intake = IntakeResult.model_validate_json(row["intake_json"])
    scores = ScoreSet.model_validate_json(row["scores_json"]) if row["scores_json"] else None
    return DailyLog(
        id=row["id"],
        date=date.fromisoformat(row["date"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
        raw_input=row["raw_input"],
        intake=intake,
        scores=scores,
        summary_text=row["summary_text"],
    )
EOF

# ─── src/backend/storage/chroma_store.py ─────────────────────────────
cat > src/backend/storage/chroma_store.py << 'EOF'
"""ChromaDB vector storage for semantic search and pattern matching."""

from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from src.backend.config import get_settings
from src.backend.models.intake import DailyLog

_client: Optional[chromadb.ClientAPI] = None
_collection: Optional[chromadb.Collection] = None

COLLECTION_NAME = "daily_logs"


def _get_collection() -> chromadb.Collection:
    global _client, _collection
    if _collection is None:
        settings = get_settings()
        _client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def _build_summary(log: DailyLog) -> str:
    """Build a human-readable summary for embedding."""
    parts = []
    intake = log.intake

    if intake.sleep:
        s = f"Sleep: {intake.sleep.quality}"
        if intake.sleep.hours:
            s += f", {intake.sleep.hours}h"
        parts.append(s)

    if intake.soreness:
        areas = [f"{s.body_part} ({s.severity}/5)" for s in intake.soreness]
        parts.append(f"Soreness: {', '.join(areas)}")

    if intake.meals:
        parts.append(f"Meals: {', '.join(m.description for m in intake.meals)}")

    if intake.hydration:
        h_parts = []
        if intake.hydration.water_oz:
            h_parts.append(f"{intake.hydration.water_oz}oz water")
        if intake.hydration.alcohol_drinks:
            h_parts.append(f"{intake.hydration.alcohol_drinks} drinks")
        if h_parts:
            parts.append(f"Hydration: {', '.join(h_parts)}")

    if intake.todays_wod and intake.todays_wod.movements:
        wod = f"WOD: {', '.join(intake.todays_wod.movements)}"
        if intake.todays_wod.raw:
            wod += f" ({intake.todays_wod.raw})"
        parts.append(wod)

    if intake.performance:
        perf_parts = []
        if intake.performance.feel:
            perf_parts.append(f"felt {intake.performance.feel}")
        if intake.performance.hr_max:
            perf_parts.append(f"HR max {intake.performance.hr_max}")
        if intake.performance.total_time_seconds:
            mins = intake.performance.total_time_seconds / 60
            perf_parts.append(f"{mins:.1f} min")
        if perf_parts:
            parts.append(f"Performance: {', '.join(perf_parts)}")

    if intake.subjective_readiness:
        parts.append(f"Readiness: {intake.subjective_readiness}")

    return " | ".join(parts) if parts else "No data"


def store_embedding(log: DailyLog) -> None:
    """Store a daily log's embedding in ChromaDB."""
    collection = _get_collection()
    summary = log.summary_text or _build_summary(log)

    metadata = {
        "date": log.date.isoformat(),
        "readiness": log.scores.readiness if log.scores else 0,
        "sleep_score": log.scores.sleep if log.scores else 0,
        "soreness_score": log.scores.soreness if log.scores else 0,
    }

    # Add soreness body parts and WOD movements for filtering
    if log.intake.soreness:
        metadata["sore_areas"] = ",".join(s.body_part for s in log.intake.soreness)
    if log.intake.todays_wod:
        metadata["movements"] = ",".join(log.intake.todays_wod.movements)
    if log.intake.performance and log.intake.performance.feel:
        metadata["feel"] = log.intake.performance.feel

    collection.upsert(
        ids=[log.id],
        documents=[summary],
        metadatas=[metadata],
    )


def search_similar(query: str, n: int = 5, where: Optional[dict] = None) -> list[dict]:
    """Semantic search across all logs."""
    collection = _get_collection()
    kwargs = {"query_texts": [query], "n_results": n}
    if where:
        kwargs["where"] = where

    results = collection.query(**kwargs)

    logs = []
    if results and results["ids"]:
        for i, doc_id in enumerate(results["ids"][0]):
            logs.append({
                "id": doc_id,
                "document": results["documents"][0][i] if results["documents"] else "",
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else None,
            })
    return logs


def get_similar_days(log: DailyLog, n: int = 5) -> list[dict]:
    """Find days most similar to a given log."""
    summary = log.summary_text or _build_summary(log)
    return search_similar(summary, n=n)
EOF

# ─── src/backend/patterns/__init__.py ────────────────────────────────
cat > src/backend/patterns/__init__.py << 'EOF'
"""Pattern analysis engine: trends, correlations, and insights."""
EOF

# ─── src/backend/patterns/trends.py ──────────────────────────────────
cat > src/backend/patterns/trends.py << 'EOF'
"""SQL-based trend analysis over score history."""

import sqlite3
from datetime import date, timedelta
from typing import Optional

from src.backend.storage.sqlite_store import _get_connection


def weekly_averages(end_date: Optional[date] = None, weeks: int = 4) -> list[dict]:
    """Get weekly average scores for the last N weeks."""
    if end_date is None:
        end_date = date.today()
    start_date = end_date - timedelta(weeks=weeks)

    conn = _get_connection()
    rows = conn.execute("""
        SELECT
            strftime('%Y-W%W', date) as week,
            AVG(sleep) as avg_sleep,
            AVG(soreness) as avg_soreness,
            AVG(diet) as avg_diet,
            AVG(hydration) as avg_hydration,
            AVG(readiness) as avg_readiness,
            AVG(performance) as avg_performance,
            COUNT(*) as log_count
        FROM score_history
        WHERE date >= ? AND date <= ?
        GROUP BY week
        ORDER BY week
    """, (start_date.isoformat(), end_date.isoformat())).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def trend_direction(dimension: str, days: int = 14) -> dict:
    """Determine if a score dimension is trending up, down, or flat."""
    end = date.today()
    start = end - timedelta(days=days)
    mid = start + timedelta(days=days // 2)

    conn = _get_connection()

    first_half = conn.execute(f"""
        SELECT AVG({dimension}) as avg_score FROM score_history
        WHERE date >= ? AND date < ?
    """, (start.isoformat(), mid.isoformat())).fetchone()

    second_half = conn.execute(f"""
        SELECT AVG({dimension}) as avg_score FROM score_history
        WHERE date >= ? AND date <= ?
    """, (mid.isoformat(), end.isoformat())).fetchone()

    conn.close()

    avg1 = first_half["avg_score"] if first_half and first_half["avg_score"] else None
    avg2 = second_half["avg_score"] if second_half and second_half["avg_score"] else None

    if avg1 is None or avg2 is None:
        return {"direction": "insufficient_data", "change": 0}

    change = avg2 - avg1
    if change > 5:
        direction = "up"
    elif change < -5:
        direction = "down"
    else:
        direction = "flat"

    return {"direction": direction, "change": round(change, 1), "first_half_avg": round(avg1, 1), "second_half_avg": round(avg2, 1)}


def best_days(n: int = 5) -> list[dict]:
    """Find the N best readiness days for pattern analysis."""
    conn = _get_connection()
    rows = conn.execute("""
        SELECT * FROM score_history
        ORDER BY readiness DESC
        LIMIT ?
    """, (n,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def worst_days(n: int = 5) -> list[dict]:
    """Find the N worst readiness days."""
    conn = _get_connection()
    rows = conn.execute("""
        SELECT * FROM score_history
        ORDER BY readiness ASC
        LIMIT ?
    """, (n,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
EOF

# ─── src/backend/patterns/correlations.py ────────────────────────────
cat > src/backend/patterns/correlations.py << 'EOF'
"""Score correlation detection across history."""

import sqlite3
from datetime import date, timedelta
from typing import Optional

from src.backend.storage.sqlite_store import _get_connection


def day_before_performance(min_days: int = 7) -> Optional[dict]:
    """Analyze what the day-before scores look like for best vs worst performance days.
    
    Answers: 'What patterns precede my best training days?'
    """
    conn = _get_connection()
    
    # Get all days with performance scores
    rows = conn.execute("""
        SELECT s1.date as perf_date, s1.performance,
               s2.sleep as prev_sleep, s2.soreness as prev_soreness,
               s2.diet as prev_diet, s2.hydration as prev_hydration,
               s2.readiness as prev_readiness
        FROM score_history s1
        JOIN score_history s2 ON date(s1.date, '-1 day') = s2.date
        WHERE s1.performance IS NOT NULL
        ORDER BY s1.performance DESC
    """).fetchall()
    conn.close()
    
    if len(rows) < min_days:
        return None
    
    rows_list = [dict(r) for r in rows]
    top_quarter = rows_list[:len(rows_list) // 4] or rows_list[:1]
    bottom_quarter = rows_list[-(len(rows_list) // 4):] or rows_list[-1:]
    
    def avg_dict(subset, keys):
        return {k: round(sum(r[k] for r in subset if r[k] is not None) / max(1, len(subset)), 1) for k in keys}
    
    keys = ["prev_sleep", "prev_soreness", "prev_diet", "prev_hydration", "prev_readiness"]
    
    return {
        "best_performance_preceded_by": avg_dict(top_quarter, keys),
        "worst_performance_preceded_by": avg_dict(bottom_quarter, keys),
        "sample_size": len(rows_list),
    }


def soreness_after_movements(body_part: str) -> list[dict]:
    """Find which movements tend to precede soreness in a specific body part."""
    conn = _get_connection()
    
    # This requires joining with the daily_logs table to get movement data
    rows = conn.execute("""
        SELECT dl.date, dl.intake_json
        FROM daily_logs dl
        JOIN score_history sh ON dl.id = sh.log_id
        WHERE dl.intake_json LIKE ?
        ORDER BY dl.date DESC
        LIMIT 30
    """, (f'%{body_part}%',)).fetchall()
    conn.close()
    
    return [{"date": r["date"], "intake": r["intake_json"]} for r in rows]
EOF

# ─── src/backend/patterns/insights.py ────────────────────────────────
cat > src/backend/patterns/insights.py << 'EOF'
"""LLM-powered pattern narratives (optional, uses Ollama)."""

from typing import Optional

import httpx

from src.backend.config import get_settings
from src.backend.patterns.trends import weekly_averages, trend_direction, best_days


async def generate_weekly_insight(base_url: Optional[str] = None) -> str:
    """Generate a natural language summary of the week's patterns."""
    settings = get_settings()
    url = base_url or settings.ollama_base_url

    # Gather data
    averages = weekly_averages(weeks=2)
    trends = {
        dim: trend_direction(dim, days=14)
        for dim in ["sleep", "soreness", "diet", "hydration", "readiness"]
    }
    best = best_days(3)

    prompt = f"""You are a concise fitness analyst. Based on this athlete's recent data, give a 2-3 sentence insight about their patterns and one actionable suggestion.

Weekly averages (last 2 weeks): {averages}
Trends (14-day direction): {trends}
Best readiness days: {best}

Be specific and data-driven. No fluff."""

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{url}/api/generate",
            json={
                "model": settings.ollama_model,
                "prompt": prompt,
                "stream": False,
            },
        )
        response.raise_for_status()
        result = response.json()

    return result.get("response", "Unable to generate insight.")
EOF

# ─── src/backend/api/__init__.py ─────────────────────────────────────
cat > src/backend/api/__init__.py << 'EOF'
"""API route modules."""
EOF

# ─── src/backend/api/intake.py ───────────────────────────────────────
cat > src/backend/api/intake.py << 'EOF'
"""POST /api/intake — process a new daily entry."""

import uuid
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile

from src.backend.extraction.ollama import extract_with_ollama
from src.backend.extraction.vision import extract_wod_from_image
from src.backend.models.intake import DailyLog, IntakeResult, ScoreSet
from src.backend.scorers import score_all
from src.backend.storage.sqlite_store import save_log
from src.backend.storage.chroma_store import store_embedding

router = APIRouter(prefix="/api", tags=["intake"])


@router.post("/intake")
async def create_intake(
    text: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    entry_date: Optional[str] = Form(None),  # ISO format, defaults to today
):
    """Process a new daily entry from text and/or image."""
    target_date = date.fromisoformat(entry_date) if entry_date else date.today()
    
    # Extract from text
    intake: Optional[IntakeResult] = None
    if text:
        intake = await extract_with_ollama(text)

    # If image provided, extract WOD and merge
    if image:
        image_bytes = await image.read()
        wod = await extract_wod_from_image(image_bytes)
        if intake:
            intake.todays_wod = wod
        else:
            # Image-only submission (just the WOD)
            from src.backend.models.intake import Sleep
            intake = IntakeResult(sleep=Sleep(quality="not reported"), todays_wod=wod)

    if intake is None:
        return {"error": "Provide text or image input"}, 400

    # Score
    scores_raw = score_all(intake)
    scores = ScoreSet(
        sleep=scores_raw["sleep"]["score"],
        soreness=scores_raw["soreness"]["score"],
        diet=scores_raw["diet"]["score"],
        hydration=scores_raw["hydration"]["score"],
        performance=scores_raw["performance"]["score"],
        readiness=scores_raw["readiness"]["score"],
    )

    # Build and store the log
    log = DailyLog(
        id=f"{target_date.isoformat()}-{uuid.uuid4().hex[:8]}",
        date=target_date,
        created_at=datetime.utcnow(),
        raw_input=text,
        intake=intake,
        scores=scores,
    )
    
    save_log(log)
    store_embedding(log)

    return {
        "id": log.id,
        "date": log.date.isoformat(),
        "scores": scores.model_dump(),
        "intake": intake.model_dump(),
    }
EOF

# ─── src/backend/api/logs.py ─────────────────────────────────────────
cat > src/backend/api/logs.py << 'EOF'
"""GET /api/logs — retrieve daily logs by date range."""

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Query

from src.backend.storage.sqlite_store import get_log_by_date, get_logs_range

router = APIRouter(prefix="/api", tags=["logs"])


@router.get("/logs")
async def list_logs(
    start: Optional[str] = Query(None, description="Start date (ISO format)"),
    end: Optional[str] = Query(None, description="End date (ISO format)"),
    days: int = Query(7, description="Number of days back from end (default 7)"),
):
    """Get logs for a date range. Defaults to last 7 days."""
    end_date = date.fromisoformat(end) if end else date.today()
    start_date = date.fromisoformat(start) if start else end_date - timedelta(days=days)

    logs = get_logs_range(start_date, end_date)
    return {
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "count": len(logs),
        "logs": [
            {
                "id": log.id,
                "date": log.date.isoformat(),
                "scores": log.scores.model_dump() if log.scores else None,
                "intake": log.intake.model_dump(),
                "raw_input": log.raw_input,
            }
            for log in logs
        ],
    }


@router.get("/logs/{log_date}")
async def get_log(log_date: str):
    """Get a single day's log."""
    d = date.fromisoformat(log_date)
    log = get_log_by_date(d)
    if not log:
        return {"error": "No log found for this date"}, 404
    return {
        "id": log.id,
        "date": log.date.isoformat(),
        "scores": log.scores.model_dump() if log.scores else None,
        "intake": log.intake.model_dump(),
        "raw_input": log.raw_input,
    }
EOF

# ─── src/backend/api/trends.py ───────────────────────────────────────
cat > src/backend/api/trends.py << 'EOF'
"""GET /api/trends — aggregated score trends for charts."""

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Query

from src.backend.storage.sqlite_store import get_scores_range
from src.backend.patterns.trends import weekly_averages, trend_direction

router = APIRouter(prefix="/api", tags=["trends"])


@router.get("/trends/scores")
async def score_trends(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    days: int = Query(30, description="Days of history (default 30)"),
):
    """Get daily score time-series for charts."""
    end_date = date.fromisoformat(end) if end else date.today()
    start_date = date.fromisoformat(start) if start else end_date - timedelta(days=days)
    
    scores = get_scores_range(start_date, end_date)
    return {"start": start_date.isoformat(), "end": end_date.isoformat(), "scores": scores}


@router.get("/trends/weekly")
async def weekly_trend(weeks: int = Query(4)):
    """Get weekly average scores."""
    return {"weeks": weekly_averages(weeks=weeks)}


@router.get("/trends/direction")
async def trend_directions():
    """Get trend direction (up/down/flat) for each dimension."""
    dimensions = ["sleep", "soreness", "diet", "hydration", "readiness"]
    return {dim: trend_direction(dim) for dim in dimensions}
EOF

# ─── src/backend/api/patterns.py ─────────────────────────────────────
cat > src/backend/api/patterns.py << 'EOF'
"""GET /api/patterns — semantic search and pattern detection."""

from typing import Optional

from fastapi import APIRouter, Query

from src.backend.storage.chroma_store import search_similar
from src.backend.patterns.correlations import day_before_performance
from src.backend.patterns.insights import generate_weekly_insight

router = APIRouter(prefix="/api", tags=["patterns"])


@router.get("/patterns/search")
async def semantic_search(
    query: str = Query(..., description="Natural language search query"),
    n: int = Query(5, description="Number of results"),
):
    """Semantic search across all logged days."""
    results = search_similar(query, n=n)
    return {"query": query, "results": results}


@router.get("/patterns/performance-predictors")
async def performance_predictors():
    """What patterns precede best vs worst performance days?"""
    result = day_before_performance()
    if result is None:
        return {"message": "Not enough data yet (need 7+ days with performance logged)"}
    return result


@router.get("/patterns/insight")
async def weekly_insight():
    """LLM-generated weekly insight (requires Ollama running)."""
    try:
        insight = await generate_weekly_insight()
        return {"insight": insight}
    except Exception as e:
        return {"error": f"Could not generate insight: {str(e)}"}
EOF

# ─── src/backend/api/directive.py ────────────────────────────────────
cat > src/backend/api/directive.py << 'EOF'
"""GET /api/directive — today's training recommendation."""

from datetime import date

from fastapi import APIRouter

from src.backend.storage.sqlite_store import get_log_by_date
from src.backend.storage.chroma_store import get_similar_days

router = APIRouter(prefix="/api", tags=["directive"])


@router.get("/directive")
async def todays_directive():
    """Generate today's training recommendation based on current state."""
    today_log = get_log_by_date(date.today())

    if not today_log or not today_log.scores:
        return {
            "directive": "No data logged today yet. Log your daily update to get a recommendation.",
            "has_data": False,
        }

    scores = today_log.scores
    readiness = scores.readiness
    
    # Find similar historical days for context
    similar = get_similar_days(today_log, n=3)

    # Rule-based directive generation
    directives = []
    
    if readiness >= 80:
        directives.append("You're in a great spot. Full send on today's workout.")
    elif readiness >= 60:
        directives.append("Solid readiness. Train as programmed.")
    elif readiness >= 40:
        directives.append("Moderate readiness. Consider scaling intensity by 10-15%.")
    else:
        directives.append("Low readiness. Prioritize recovery — active rest or mobility work.")

    # Soreness-specific guidance
    if today_log.intake.soreness:
        high_soreness = [s for s in today_log.intake.soreness if s.severity >= 3]
        if high_soreness:
            areas = ", ".join(s.body_part for s in high_soreness)
            directives.append(f"Watch {areas} — consider movement substitutions that reduce load on these areas.")

    # Sleep warning
    if scores.sleep < 50:
        directives.append("Poor sleep recovery. Keep volume moderate and avoid max-effort lifts.")

    # Hydration warning
    if scores.hydration < 50:
        directives.append("Hydration is low. Prioritize water intake before and during training.")

    return {
        "directive": " ".join(directives),
        "readiness_score": readiness,
        "scores": scores.model_dump(),
        "similar_days": similar[:2],
        "has_data": True,
    }
EOF

# ─── src/backend/main.py ─────────────────────────────────────────────
cat > src/backend/main.py << 'EOF'
"""aegis FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.backend.storage.sqlite_store import init_db
from src.backend.api.intake import router as intake_router
from src.backend.api.logs import router as logs_router
from src.backend.api.trends import router as trends_router
from src.backend.api.patterns import router as patterns_router
from src.backend.api.directive import router as directive_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize storage on startup."""
    init_db()
    yield


app = FastAPI(
    title="aegis",
    description="Voice-first fitness tracking copilot for functional longevity",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server and local network access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(intake_router)
app.include_router(logs_router)
app.include_router(trends_router)
app.include_router(patterns_router)
app.include_router(directive_router)


@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0"}
EOF

# ─── src/backend/importers/__init__.py ───────────────────────────────
cat > src/backend/importers/__init__.py << 'EOF'
"""Data importers for Fitbit, Google Health, etc."""
EOF

# ─── src/backend/importers/fitbit.py ─────────────────────────────────
cat > src/backend/importers/fitbit.py << 'EOF'
"""Fitbit Web API importer.

OAuth2 flow:
1. User visits /api/import/fitbit/auth -> redirect to Fitbit authorization
2. Fitbit redirects back with code -> /api/import/fitbit/callback
3. We exchange code for access token, store it
4. Pull historical data: sleep, heart rate, activities

Fitbit API docs: https://dev.fitbit.com/build/reference/web-api/

Requires FITBIT_CLIENT_ID and FITBIT_CLIENT_SECRET in .env.
Register app at https://dev.fitbit.com/apps/new (set type to "Personal")
"""

from datetime import date, timedelta
from typing import Optional

import httpx

from src.backend.config import get_settings

FITBIT_AUTH_URL = "https://www.fitbit.com/oauth2/authorize"
FITBIT_TOKEN_URL = "https://api.fitbit.com/oauth2/token"
FITBIT_API_BASE = "https://api.fitbit.com"

# Scopes we need
SCOPES = "sleep heartrate activity"


def get_auth_url(redirect_uri: str) -> Optional[str]:
    """Generate Fitbit OAuth authorization URL."""
    settings = get_settings()
    if not settings.fitbit_client_id:
        return None

    params = {
        "response_type": "code",
        "client_id": settings.fitbit_client_id,
        "redirect_uri": redirect_uri,
        "scope": SCOPES,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{FITBIT_AUTH_URL}?{query}"


async def exchange_code(code: str, redirect_uri: str) -> dict:
    """Exchange authorization code for access token."""
    settings = get_settings()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            FITBIT_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": settings.fitbit_client_id,
                "client_secret": settings.fitbit_client_secret,
            },
        )
        response.raise_for_status()
        return response.json()


async def fetch_sleep_data(access_token: str, start: date, end: date) -> list[dict]:
    """Fetch sleep data from Fitbit API."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{FITBIT_API_BASE}/1.2/user/-/sleep/date/{start.isoformat()}/{end.isoformat()}.json",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        data = response.json()
        return data.get("sleep", [])


async def fetch_heart_rate(access_token: str, day: date) -> dict:
    """Fetch intraday heart rate for a specific day."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{FITBIT_API_BASE}/1/user/-/activities/heart/date/{day.isoformat()}/1d/1min.json",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return response.json()


async def fetch_activities(access_token: str, start: date, end: date) -> list[dict]:
    """Fetch activity/exercise logs."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{FITBIT_API_BASE}/1/user/-/activities/list.json",
            params={"afterDate": start.isoformat(), "sort": "asc", "limit": 100, "offset": 0},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        data = response.json()
        return data.get("activities", [])
EOF

# ─── src/backend/importers/google_health.py ──────────────────────────
cat > src/backend/importers/google_health.py << 'EOF'
"""Google Health Connect / Google Fit importer skeleton.

Google Fit REST API is being deprecated in favor of Health Connect (Android).
For now, this supports manual export import (Google Takeout) and will
be extended for Health Connect API when available on web.

Google Takeout exports fitness data as JSON/TCX files.
"""

import json
from pathlib import Path
from typing import Optional


async def import_from_takeout(export_dir: Path) -> dict:
    """Import from a Google Takeout fitness export directory.
    
    Expected structure:
    Takeout/Fit/
        Activities/
            *.tcx (activity files)
        Daily activity metrics/
            *.json (daily summaries)
    """
    results = {"activities": 0, "daily_metrics": 0, "errors": []}
    
    activities_dir = export_dir / "Activities"
    if activities_dir.exists():
        for f in activities_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                results["activities"] += 1
                # TODO: parse and store activity data
            except Exception as e:
                results["errors"].append(str(e))

    metrics_dir = export_dir / "Daily activity metrics"
    if metrics_dir.exists():
        for f in metrics_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                results["daily_metrics"] += 1
                # TODO: parse and store daily metrics
            except Exception as e:
                results["errors"].append(str(e))

    return results
EOF

# ─── tests/__init__.py ───────────────────────────────────────────────
cat > tests/__init__.py << 'EOF'
EOF

# ─── tests/test_models.py ────────────────────────────────────────────
cat > tests/test_models.py << 'EOF'
"""Test that core models validate correctly."""

from datetime import date, datetime

from src.backend.models.intake import (
    DailyLog, IntakeResult, Meal, Sleep, Soreness, WOD,
    PerformanceLog, Hydration, ScoreSet, WorkoutType,
)


def test_minimal_intake():
    """Minimum valid intake: just sleep."""
    intake = IntakeResult(sleep=Sleep(quality="good"))
    assert intake.sleep.quality == "good"
    assert intake.soreness == []
    assert intake.meals == []


def test_full_intake():
    """Fully populated intake."""
    intake = IntakeResult(
        sleep=Sleep(quality="good", hours=7.5),
        soreness=[Soreness(body_part="quads", severity=2)],
        meals=[Meal(description="chicken and rice", protein_g=40)],
        hydration=Hydration(water_oz=80, alcohol_drinks=1),
        todays_wod=WOD(
            workout_type=WorkoutType.FOR_TIME,
            movements=["thrusters", "pull-ups"],
            raw="Fran: 21-15-9 thrusters and pull-ups",
        ),
        performance=PerformanceLog(
            total_time_seconds=522,
            rx=True,
            hr_max=182,
            hr_avg=168,
            rpe=8,
            feel="strong",
        ),
        subjective_readiness="high",
    )
    assert intake.performance.total_time_seconds == 522
    assert intake.todays_wod.workout_type == WorkoutType.FOR_TIME


def test_daily_log():
    """DailyLog wraps intake + scores."""
    intake = IntakeResult(sleep=Sleep(quality="good", hours=8))
    scores = ScoreSet(sleep=90, soreness=100, diet=70, hydration=85, readiness=82)
    log = DailyLog(
        id="2025-01-15-abc123",
        date=date(2025, 1, 15),
        created_at=datetime(2025, 1, 15, 8, 0),
        intake=intake,
        scores=scores,
    )
    assert log.scores.readiness == 82
EOF

# ─── tests/test_scorers.py ───────────────────────────────────────────
cat > tests/test_scorers.py << 'EOF'
"""Test deterministic scorers."""

from src.backend.models.intake import IntakeResult, Sleep, Soreness, Meal, Hydration, PerformanceLog
from src.backend.scorers import score_all


def _make_intake(**kwargs) -> IntakeResult:
    defaults = {"sleep": Sleep(quality="good", hours=8)}
    defaults.update(kwargs)
    return IntakeResult(**defaults)


def test_perfect_sleep():
    intake = _make_intake(sleep=Sleep(quality="great", hours=8))
    result = score_all(intake)
    assert result["sleep"]["score"] >= 85


def test_poor_sleep():
    intake = _make_intake(sleep=Sleep(quality="terrible", hours=4))
    result = score_all(intake)
    assert result["sleep"]["score"] <= 30


def test_no_soreness_is_100():
    intake = _make_intake()
    result = score_all(intake)
    assert result["soreness"]["score"] == 100


def test_severe_soreness():
    intake = _make_intake(soreness=[Soreness(body_part="back", severity=5)])
    result = score_all(intake)
    assert result["soreness"]["score"] <= 50


def test_hydration_good():
    intake = _make_intake(hydration=Hydration(water_oz=80, alcohol_drinks=0))
    result = score_all(intake)
    assert result["hydration"]["score"] >= 80


def test_hydration_with_alcohol():
    intake = _make_intake(hydration=Hydration(water_oz=60, alcohol_drinks=3))
    result = score_all(intake)
    assert result["hydration"]["score"] < 60


def test_performance_good_feel():
    intake = _make_intake(performance=PerformanceLog(feel="strong", rx=True, hr_max=175, rpe=7))
    result = score_all(intake)
    assert result["performance"]["score"] >= 75


def test_readiness_composite():
    intake = _make_intake(
        sleep=Sleep(quality="good", hours=8),
        soreness=[],
        meals=[Meal(description="chicken", protein_g=30)],
        hydration=Hydration(water_oz=80),
    )
    result = score_all(intake)
    assert 60 <= result["readiness"]["score"] <= 100
EOF

# ─── tests/test_api.py ───────────────────────────────────────────────
cat > tests/test_api.py << 'EOF'
"""Test FastAPI endpoints."""

from fastapi.testclient import TestClient

from src.backend.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_logs_empty():
    response = client.get("/api/logs?days=7")
    assert response.status_code == 200
    data = response.json()
    assert "logs" in data


def test_directive_no_data():
    response = client.get("/api/directive")
    assert response.status_code == 200
    data = response.json()
    assert data["has_data"] is False
EOF

echo "  ✓ Python backend written"

# ─── Phase 4: Makefile ───────────────────────────────────────────────
echo ""
echo "▶ Phase 4: Writing Makefile..."

cat > Makefile << 'MAKEFILE'
.PHONY: dev test backend frontend install setup ollama-check

# ─── Setup ────────────────────────────────────────────────────────────
setup: install ollama-check
	@echo "✓ Setup complete. Run 'make dev' to start."

install:
	pip install -r requirements.txt
	cd src/frontend && npm install

ollama-check:
	@which ollama > /dev/null 2>&1 || (echo "⚠ Ollama not installed. Get it at https://ollama.ai" && exit 0)
	@ollama list 2>/dev/null | grep -q "llama3.2" || echo "⚠ Run: ollama pull llama3.2"
	@ollama list 2>/dev/null | grep -q "llava" || echo "⚠ Run: ollama pull llava"

# ─── Development ──────────────────────────────────────────────────────
dev: backend frontend

backend:
	uvicorn src.backend.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd src/frontend && npm run dev

# ─── Testing ──────────────────────────────────────────────────────────
test:
	python -m pytest tests/ -v

test-quick:
	python -m pytest tests/ -q --tb=short

# ─── Data ─────────────────────────────────────────────────────────────
reset-db:
	rm -rf data/aegis.db data/chroma
	@echo "✓ Database reset"
MAKEFILE

echo "  ✓ Makefile written"

# ─── Phase 5: Next.js frontend ───────────────────────────────────────
echo ""
echo "▶ Phase 5: Initializing Next.js frontend..."

mkdir -p src/frontend

cat > src/frontend/package.json << 'PKGJSON'
{
  "name": "aegis-frontend",
  "version": "2.0.0",
  "private": true,
  "scripts": {
    "dev": "next dev --port 3000",
    "build": "next build",
    "start": "next start"
  },
  "dependencies": {
    "next": "14.2.15",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "recharts": "^2.12.7",
    "date-fns": "^3.6.0"
  },
  "devDependencies": {
    "@types/node": "^22.7.5",
    "@types/react": "^18.3.11",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.4.47",
    "tailwindcss": "^3.4.13",
    "typescript": "^5.6.3"
  }
}
PKGJSON

cat > src/frontend/next.config.js << 'NEXTCONF'
/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
NEXTCONF

cat > src/frontend/tsconfig.json << 'TSCONF'
{
  "compilerOptions": {
    "target": "es5",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx"],
  "exclude": ["node_modules"]
}
TSCONF

cat > src/frontend/tailwind.config.ts << 'TAILWIND'
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        aegis: {
          dark: "#1a1a2e",
          mid: "#16213e",
          accent: "#0f3460",
          highlight: "#e94560",
          green: "#4ade80",
          yellow: "#fbbf24",
          red: "#f87171",
        },
      },
    },
  },
  plugins: [],
};

export default config;
TAILWIND

cat > src/frontend/postcss.config.js << 'POSTCSS'
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
POSTCSS

# ─── Frontend app directory ──────────────────────────────────────────
mkdir -p src/frontend/app
mkdir -p src/frontend/components
mkdir -p src/frontend/lib

cat > src/frontend/app/globals.css << 'CSS'
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --bg-primary: #1a1a2e;
  --bg-secondary: #16213e;
  --accent: #0f3460;
  --highlight: #e94560;
}

body {
  background: var(--bg-primary);
  color: #e2e8f0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
CSS

cat > src/frontend/app/layout.tsx << 'LAYOUT'
import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "aegis",
  description: "Fitness tracking copilot for functional longevity",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  themeColor: "#1a1a2e",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <nav className="sticky top-0 z-50 bg-aegis-mid/80 backdrop-blur-md border-b border-white/10 px-4 py-3">
          <div className="max-w-5xl mx-auto flex items-center justify-between">
            <h1 className="text-xl font-bold tracking-tight">aegis</h1>
            <div className="flex gap-4 text-sm">
              <a href="/" className="hover:text-aegis-green transition-colors">Dashboard</a>
              <a href="/log" className="hover:text-aegis-green transition-colors">Log</a>
              <a href="/calendar" className="hover:text-aegis-green transition-colors">Calendar</a>
              <a href="/trends" className="hover:text-aegis-green transition-colors">Trends</a>
            </div>
          </div>
        </nav>
        <main className="max-w-5xl mx-auto px-4 py-6">
          {children}
        </main>
      </body>
    </html>
  );
}
LAYOUT

cat > src/frontend/app/page.tsx << 'DASHBOARD'
"use client";

import { useEffect, useState } from "react";
import { ScoreRing } from "@/components/ScoreRing";
import { InsightCard } from "@/components/InsightCard";

interface Scores {
  sleep: number;
  soreness: number;
  diet: number;
  hydration: number;
  performance: number | null;
  readiness: number;
}

interface DirectiveData {
  directive: string;
  readiness_score?: number;
  scores?: Scores;
  has_data: boolean;
}

export default function Dashboard() {
  const [directive, setDirective] = useState<DirectiveData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/directive")
      .then((r) => r.json())
      .then(setDirective)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="flex items-center justify-center h-64 text-gray-400">Loading...</div>;
  }

  if (!directive?.has_data) {
    return (
      <div className="text-center py-20">
        <h2 className="text-2xl font-bold mb-4">Welcome to aegis</h2>
        <p className="text-gray-400 mb-8">No data logged today yet.</p>
        <a
          href="/log"
          className="inline-block bg-aegis-green/20 text-aegis-green border border-aegis-green/30 px-6 py-3 rounded-lg hover:bg-aegis-green/30 transition-colors"
        >
          Log Today&apos;s Update
        </a>
      </div>
    );
  }

  const scores = directive.scores!;

  return (
    <div className="space-y-8">
      {/* Readiness Hero */}
      <div className="text-center py-8">
        <ScoreRing score={scores.readiness} size={140} label="Readiness" />
      </div>

      {/* Directive */}
      <div className="bg-aegis-mid/50 border border-white/10 rounded-xl p-6">
        <h3 className="text-sm uppercase tracking-wider text-gray-400 mb-2">Today&apos;s Directive</h3>
        <p className="text-lg">{directive.directive}</p>
      </div>

      {/* Score Grid */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <ScoreRing score={scores.sleep} size={80} label="Sleep" />
        <ScoreRing score={scores.soreness} size={80} label="Recovery" />
        <ScoreRing score={scores.diet} size={80} label="Diet" />
        <ScoreRing score={scores.hydration} size={80} label="Hydration" />
        {scores.performance !== null && (
          <ScoreRing score={scores.performance} size={80} label="Performance" />
        )}
      </div>

      {/* Insight */}
      <InsightCard />
    </div>
  );
}
DASHBOARD

cat > src/frontend/app/log/page.tsx << 'LOGPAGE'
"use client";

import { useState } from "react";

export default function LogPage() {
  const [text, setText] = useState("");
  const [image, setImage] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text && !image) return;

    setSubmitting(true);
    setError(null);

    const formData = new FormData();
    if (text) formData.append("text", text);
    if (image) formData.append("image", image);

    try {
      const res = await fetch("/api/intake", { method: "POST", body: formData });
      const data = await res.json();
      if (res.ok) {
        setResult(data);
        setText("");
        setImage(null);
      } else {
        setError(data.error || "Something went wrong");
      }
    } catch (err) {
      setError("Failed to connect to server");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold mb-6">Log Daily Update</h2>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Text input (with dictation support via browser) */}
        <div>
          <label className="block text-sm text-gray-400 mb-2">
            How are you feeling? (Use dictation 🎤 on your device)
          </label>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Slept about 7 hours, feeling good. Quads a little sore from yesterday..."
            className="w-full h-40 bg-aegis-mid border border-white/10 rounded-xl p-4 text-white placeholder-gray-500 resize-none focus:outline-none focus:ring-2 focus:ring-aegis-green/50"
          />
        </div>

        {/* Image upload for WOD screenshots */}
        <div>
          <label className="block text-sm text-gray-400 mb-2">
            WOD Screenshot (optional)
          </label>
          <input
            type="file"
            accept="image/*"
            onChange={(e) => setImage(e.target.files?.[0] || null)}
            className="block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:bg-aegis-accent file:text-white hover:file:bg-aegis-accent/80"
          />
        </div>

        <button
          type="submit"
          disabled={submitting || (!text && !image)}
          className="w-full py-3 bg-aegis-green/20 text-aegis-green border border-aegis-green/30 rounded-xl font-medium hover:bg-aegis-green/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {submitting ? "Processing..." : "Submit Entry"}
        </button>
      </form>

      {error && (
        <div className="mt-6 p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400">
          {error}
        </div>
      )}

      {result && (
        <div className="mt-6 p-4 bg-aegis-green/10 border border-aegis-green/30 rounded-xl">
          <h3 className="text-aegis-green font-medium mb-2">Entry Logged</h3>
          <div className="grid grid-cols-3 gap-3 text-sm">
            <div>Sleep: {result.scores?.sleep}/100</div>
            <div>Recovery: {result.scores?.soreness}/100</div>
            <div>Diet: {result.scores?.diet}/100</div>
            <div>Hydration: {result.scores?.hydration}/100</div>
            <div>Readiness: {result.scores?.readiness}/100</div>
            {result.scores?.performance && <div>Performance: {result.scores.performance}/100</div>}
          </div>
        </div>
      )}
    </div>
  );
}
LOGPAGE

mkdir -p src/frontend/app/calendar
cat > src/frontend/app/calendar/page.tsx << 'CALPAGE'
"use client";

import { useEffect, useState } from "react";
import { format, startOfMonth, endOfMonth, eachDayOfInterval, isSameDay } from "date-fns";

interface LogEntry {
  date: string;
  scores: { readiness: number; sleep: number; soreness: number } | null;
}

export default function CalendarPage() {
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [logs, setLogs] = useState<LogEntry[]>([]);

  useEffect(() => {
    const start = format(startOfMonth(currentMonth), "yyyy-MM-dd");
    const end = format(endOfMonth(currentMonth), "yyyy-MM-dd");
    fetch(`/api/logs?start=${start}&end=${end}`)
      .then((r) => r.json())
      .then((data) => setLogs(data.logs || []))
      .catch(console.error);
  }, [currentMonth]);

  const days = eachDayOfInterval({
    start: startOfMonth(currentMonth),
    end: endOfMonth(currentMonth),
  });

  const getScoreColor = (score: number | undefined) => {
    if (!score) return "bg-gray-800";
    if (score >= 80) return "bg-green-500/30 border-green-500/50";
    if (score >= 60) return "bg-yellow-500/30 border-yellow-500/50";
    if (score >= 40) return "bg-orange-500/30 border-orange-500/50";
    return "bg-red-500/30 border-red-500/50";
  };

  const prevMonth = () => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1));
  const nextMonth = () => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1));

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <button onClick={prevMonth} className="text-gray-400 hover:text-white px-3 py-1">←</button>
        <h2 className="text-xl font-bold">{format(currentMonth, "MMMM yyyy")}</h2>
        <button onClick={nextMonth} className="text-gray-400 hover:text-white px-3 py-1">→</button>
      </div>

      <div className="grid grid-cols-7 gap-1 text-center text-xs text-gray-500 mb-2">
        {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((d) => (
          <div key={d}>{d}</div>
        ))}
      </div>

      <div className="grid grid-cols-7 gap-1">
        {/* Offset for start of month */}
        {Array.from({ length: days[0].getDay() }).map((_, i) => (
          <div key={`empty-${i}`} />
        ))}
        {days.map((day) => {
          const dateStr = format(day, "yyyy-MM-dd");
          const log = logs.find((l) => l.date === dateStr);
          const readiness = log?.scores?.readiness;
          return (
            <div
              key={dateStr}
              className={`aspect-square rounded-lg border border-white/5 flex flex-col items-center justify-center text-xs cursor-pointer hover:border-white/20 transition-colors ${getScoreColor(readiness)}`}
            >
              <span className="text-gray-400">{format(day, "d")}</span>
              {readiness !== undefined && (
                <span className="text-white font-bold text-sm">{readiness}</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
CALPAGE

mkdir -p src/frontend/app/trends
cat > src/frontend/app/trends/page.tsx << 'TRENDSPAGE'
"use client";

import { useEffect, useState } from "react";
import { TrendChart } from "@/components/TrendChart";

interface ScorePoint {
  date: string;
  sleep: number;
  soreness: number;
  diet: number;
  hydration: number;
  readiness: number;
  performance: number | null;
}

export default function TrendsPage() {
  const [scores, setScores] = useState<ScorePoint[]>([]);
  const [days, setDays] = useState(30);
  const [directions, setDirections] = useState<Record<string, any>>({});

  useEffect(() => {
    fetch(`/api/trends/scores?days=${days}`)
      .then((r) => r.json())
      .then((data) => setScores(data.scores || []))
      .catch(console.error);

    fetch("/api/trends/direction")
      .then((r) => r.json())
      .then(setDirections)
      .catch(console.error);
  }, [days]);

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Trends</h2>
        <div className="flex gap-2">
          {[7, 14, 30, 90].map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`px-3 py-1 rounded-lg text-sm transition-colors ${
                days === d
                  ? "bg-aegis-green/20 text-aegis-green border border-aegis-green/30"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      {/* Trend direction indicators */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {Object.entries(directions).map(([dim, info]) => (
          <div key={dim} className="bg-aegis-mid/50 border border-white/10 rounded-lg p-3 text-center">
            <div className="text-xs text-gray-400 uppercase">{dim}</div>
            <div className={`text-lg font-bold ${
              info.direction === "up" ? "text-green-400" :
              info.direction === "down" ? "text-red-400" : "text-gray-400"
            }`}>
              {info.direction === "up" ? "↑" : info.direction === "down" ? "↓" : "→"}
              {info.change !== undefined ? ` ${Math.abs(info.change)}` : ""}
            </div>
          </div>
        ))}
      </div>

      {/* Charts */}
      <TrendChart data={scores} dataKey="readiness" label="Readiness" color="#4ade80" />
      <TrendChart data={scores} dataKey="sleep" label="Sleep" color="#60a5fa" />
      <TrendChart data={scores} dataKey="soreness" label="Recovery" color="#fbbf24" />
      <TrendChart data={scores} dataKey="diet" label="Diet" color="#f472b6" />
      <TrendChart data={scores} dataKey="hydration" label="Hydration" color="#22d3ee" />
    </div>
  );
}
TRENDSPAGE

# ─── Frontend components ─────────────────────────────────────────────
cat > src/frontend/components/ScoreRing.tsx << 'SCORERING'
"use client";

interface ScoreRingProps {
  score: number;
  size?: number;
  label?: string;
}

export function ScoreRing({ score, size = 100, label }: ScoreRingProps) {
  const radius = (size - 10) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  const color =
    score >= 80 ? "#4ade80" :
    score >= 60 ? "#fbbf24" :
    score >= 40 ? "#fb923c" : "#f87171";

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size} className="transform -rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.1)"
          strokeWidth="6"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-700"
        />
      </svg>
      <span
        className="absolute font-bold"
        style={{ color, fontSize: size > 100 ? "2rem" : "1rem", marginTop: size * 0.3 }}
      >
        {score}
      </span>
      {label && <span className="text-xs text-gray-400 mt-1">{label}</span>}
    </div>
  );
}
SCORERING

cat > src/frontend/components/TrendChart.tsx << 'TRENDCHART'
"use client";

import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

interface TrendChartProps {
  data: any[];
  dataKey: string;
  label: string;
  color: string;
}

export function TrendChart({ data, dataKey, label, color }: TrendChartProps) {
  if (!data.length) {
    return (
      <div className="bg-aegis-mid/50 border border-white/10 rounded-xl p-6 text-center text-gray-500">
        No data for {label}
      </div>
    );
  }

  return (
    <div className="bg-aegis-mid/50 border border-white/10 rounded-xl p-4">
      <h3 className="text-sm text-gray-400 mb-3">{label}</h3>
      <ResponsiveContainer width="100%" height={150}>
        <LineChart data={data}>
          <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#6b7280" }} />
          <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: "#6b7280" }} />
          <Tooltip
            contentStyle={{ background: "#16213e", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }}
            labelStyle={{ color: "#9ca3af" }}
          />
          <Line type="monotone" dataKey={dataKey} stroke={color} strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
TRENDCHART

cat > src/frontend/components/InsightCard.tsx << 'INSIGHTCARD'
"use client";

import { useEffect, useState } from "react";

export function InsightCard() {
  const [insight, setInsight] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchInsight = () => {
    setLoading(true);
    fetch("/api/patterns/insight")
      .then((r) => r.json())
      .then((data) => setInsight(data.insight || data.error || null))
      .catch(() => setInsight(null))
      .finally(() => setLoading(false));
  };

  return (
    <div className="bg-aegis-mid/50 border border-white/10 rounded-xl p-6">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm uppercase tracking-wider text-gray-400">Weekly Insight</h3>
        <button
          onClick={fetchInsight}
          disabled={loading}
          className="text-xs text-aegis-green hover:text-aegis-green/80 disabled:opacity-50"
        >
          {loading ? "Generating..." : "Generate"}
        </button>
      </div>
      {insight ? (
        <p className="text-sm text-gray-300">{insight}</p>
      ) : (
        <p className="text-sm text-gray-500 italic">Click generate for an AI-powered weekly insight</p>
      )}
    </div>
  );
}
INSIGHTCARD

cat > src/frontend/components/DayCard.tsx << 'DAYCARD'
"use client";

import { ScoreRing } from "./ScoreRing";

interface DayCardProps {
  date: string;
  scores: {
    readiness: number;
    sleep: number;
    soreness: number;
    diet: number;
    hydration: number;
    performance?: number | null;
  } | null;
  rawInput?: string;
}

export function DayCard({ date, scores, rawInput }: DayCardProps) {
  if (!scores) return null;

  return (
    <div className="bg-aegis-mid/50 border border-white/10 rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium">{date}</span>
        <ScoreRing score={scores.readiness} size={50} />
      </div>
      <div className="grid grid-cols-4 gap-2 text-xs text-center">
        <div><span className="text-gray-400">Sleep</span><br />{scores.sleep}</div>
        <div><span className="text-gray-400">Recovery</span><br />{scores.soreness}</div>
        <div><span className="text-gray-400">Diet</span><br />{scores.diet}</div>
        <div><span className="text-gray-400">Hydration</span><br />{scores.hydration}</div>
      </div>
      {rawInput && (
        <p className="mt-3 text-xs text-gray-500 line-clamp-2">{rawInput}</p>
      )}
    </div>
  );
}
DAYCARD

# ─── API client helpers ──────────────────────────────────────────────
cat > src/frontend/lib/api.ts << 'APITS'
const API_BASE = "/api";

export async function fetchJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const api = {
  getDirective: () => fetchJSON<any>("/directive"),
  getLogs: (days = 7) => fetchJSON<any>(`/logs?days=${days}`),
  getLogByDate: (date: string) => fetchJSON<any>(`/logs/${date}`),
  getTrends: (days = 30) => fetchJSON<any>(`/trends/scores?days=${days}`),
  getWeekly: (weeks = 4) => fetchJSON<any>(`/trends/weekly?weeks=${weeks}`),
  getDirections: () => fetchJSON<any>("/trends/direction"),
  searchPatterns: (query: string) => fetchJSON<any>(`/patterns/search?query=${encodeURIComponent(query)}`),
  getPerformancePredictors: () => fetchJSON<any>("/patterns/performance-predictors"),
  getInsight: () => fetchJSON<any>("/patterns/insight"),
};
APITS

echo "  ✓ Next.js frontend written"

# ─── Phase 6: README ─────────────────────────────────────────────────
echo ""
echo "▶ Phase 6: Writing README and docs..."

cat > README.md << 'README'
# aegis

Voice-first fitness tracking copilot for functional longevity.

Your dad talks about his day — how he slept, what hurts, what he ate, how the workout went — and aegis turns it into structured data, scores his readiness, stores everything for long-term pattern analysis, and gives him one actionable training directive.

## Architecture

```
iPad/Phone (Safari)  →  Next.js Dashboard  →  FastAPI Backend  →  Ollama (local LLM)
                                                    ↓
                                          SQLite + ChromaDB (on disk)
```

- **Input:** Apple dictation in browser (free, built-in) + screenshot upload for WODs
- **Extraction:** Ollama + Llama 3.2 8B (local, free) with optional Claude Haiku fallback
- **Scoring:** Deterministic rule-based scorers (sleep, soreness, diet, hydration, performance, readiness)
- **Storage:** SQLite (structured logs, time-series) + ChromaDB (semantic vector search)
- **Patterns:** SQL aggregates + vector similarity + LLM-generated insights
- **Frontend:** Next.js 14 mobile-first dashboard with calendar, trend charts, and daily entry

## Quickstart

### Prerequisites
- Python 3.11+
- Node.js 18+
- [Ollama](https://ollama.ai) installed and running

### Setup

```bash
# 1. Clone and enter
cd aegis

# 2. Run bootstrap (first time only)
chmod +x bootstrap.sh && ./bootstrap.sh

# 3. Pull Ollama models
ollama pull llama3.2
ollama pull llava

# 4. Install dependencies
pip install -r requirements.txt
cd src/frontend && npm install && cd ../..

# 5. Copy env and configure
cp .env.example .env

# 6. Run backend
make backend
# In another terminal:
make frontend
```

### Remote Access (iPad/Phone)

Option A: **Tailscale** (recommended)
```bash
# Install Tailscale on Mac and iPad
# Both devices get private IPs on your Tailnet
# Access aegis at http://[mac-tailscale-ip]:3000
```

Option B: **Cloudflare Tunnel** (public URL)
```bash
brew install cloudflare/cloudflare/cloudflared
cloudflared tunnel --url http://localhost:3000
```

## Usage

1. Open aegis on iPad/Mac
2. Tap "Log" → use dictation button to speak your update
3. Optionally upload a WOD screenshot
4. View scores, trends, and insights on the dashboard
5. Check the calendar for historical patterns

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/intake` | Submit daily entry (text + optional image) |
| GET | `/api/logs` | List logs by date range |
| GET | `/api/logs/{date}` | Get single day's log |
| GET | `/api/trends/scores` | Score time-series for charts |
| GET | `/api/trends/weekly` | Weekly averages |
| GET | `/api/trends/direction` | Trend direction (up/down/flat) |
| GET | `/api/patterns/search` | Semantic search across history |
| GET | `/api/patterns/performance-predictors` | What precedes best days? |
| GET | `/api/patterns/insight` | LLM-generated weekly insight |
| GET | `/api/directive` | Today's training recommendation |
| GET | `/health` | Server health check |

## Cost

$0/month. Everything runs locally:
- Ollama = free, local inference
- SQLite + ChromaDB = files on disk
- Apple dictation = built into Safari
- Tailscale free tier = remote access

Optional: Add `ANTHROPIC_API_KEY` for Claude Haiku extraction (~$0.001/entry).

## Data

All data lives in `./data/` (gitignored):
- `aegis.db` — SQLite database
- `chroma/` — ChromaDB vector store

Back up this directory to preserve history.
README

echo "  ✓ README written"

# ─── Final summary ───────────────────────────────────────────────────
echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║   ✓ aegis v2 bootstrap complete!                             ║"
echo "╠═══════════════════════════════════════════════════════════════╣"
echo "║                                                               ║"
echo "║  Next steps:                                                  ║"
echo "║  1. ollama pull llama3.2 && ollama pull llava                 ║"
echo "║  2. pip install -r requirements.txt                           ║"
echo "║  3. cd src/frontend && npm install                            ║"
echo "║  4. cp .env.example .env                                      ║"
echo "║  5. make test  (verify everything compiles)                   ║"
echo "║  6. make backend  (start FastAPI on :8000)                    ║"
echo "║  7. make frontend  (start Next.js on :3000)                   ║"
echo "║                                                               ║"
echo "║  Legacy hackathon code preserved in: ./legacy/                ║"
echo "║                                                               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
