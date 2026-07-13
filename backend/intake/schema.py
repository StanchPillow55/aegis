"""Frozen intake data contract (SC-ANTH-01 / both build waves).

These pydantic models are the AUTHORITATIVE shapes the whole system builds
against. They double as the JSON Schema handed to Claude as a tool definition
(see `extractor.py`), so the structure the model is asked to fill and the
structure we validate against are guaranteed to match.

Do not change field names/types without updating every consumer (extractor,
scorers, Redis store) — this is the shared contract across build waves.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Soreness(BaseModel):
    """A single sore/affected area."""

    body_part: str = Field(..., description="Body part, e.g. 'forearms', 'lower back'.")
    severity: int = Field(
        ...,
        ge=1,
        le=5,
        description="Soreness severity on a 1 (barely sore) to 5 (severe) scale.",
    )


class Sleep(BaseModel):
    """Last night's sleep."""

    quality: str = Field(
        ..., description="Subjective quality, e.g. 'good', 'poor', 'broken'."
    )
    hours: float | None = Field(None, description="Hours slept, if stated.")


class Meal(BaseModel):
    """A single meal or food item."""

    description: str = Field(
        ..., description="What was eaten, e.g. 'chicken and rice'."
    )
    protein_g: int | None = Field(
        None, description="Protein in grams, if stated or confidently estimable."
    )


class WOD(BaseModel):
    """Today's workout of the day."""

    movements: list[str] = Field(
        default_factory=list,
        description="Distinct movements in today's WOD, e.g. ['cleans', 'pull-ups'].",
    )
    raw: str | None = Field(
        None, description="The raw WOD text as spoken/imported, if available."
    )


class IntakeResult(BaseModel):
    """The full structured result of parsing one daily update."""

    soreness: list[Soreness] = Field(
        default_factory=list, description="All sore/affected areas mentioned."
    )
    sleep: Sleep = Field(..., description="Last night's sleep.")
    meals: list[Meal] = Field(
        default_factory=list, description="All meals/food items mentioned."
    )
    todays_wod: WOD = Field(..., description="Today's planned workout.")
    subjective_readiness: str = Field(
        ...,
        description=(
            "The athlete's overall readiness to train today, expressed as a short "
            "label such as 'low', 'moderate', or 'high'. Infer it from the update."
        ),
    )


class StoredLog(BaseModel):
    """A persisted daily log (the Redis record shape).

    `body_parts` and `movements` are denormalized out of `intake` for fast
    filtering/retrieval; `embedding` is the vector for similarity search.
    `ts` is epoch seconds.
    """

    id: str
    ts: float
    intake: IntakeResult
    body_parts: list[str] = Field(default_factory=list)
    movements: list[str] = Field(default_factory=list)
    embedding: list[float] = Field(default_factory=list)

    @classmethod
    def from_intake(
        cls,
        intake: IntakeResult,
        *,
        id: str,
        ts: float,
        embedding: list[float] | None = None,
    ) -> "StoredLog":
        """Build a StoredLog, denormalizing body_parts/movements from the intake."""
        return cls(
            id=id,
            ts=ts,
            intake=intake,
            body_parts=[s.body_part for s in intake.soreness],
            movements=list(intake.todays_wod.movements),
            embedding=embedding or [],
        )
