"""Typed intake schema (SC-ANTH-01).

These pydantic models are the contract for what Claude extracts from a spoken
daily update. The same models double as the JSON Schema handed to Claude as a
tool definition (see `extractor.py`), so the structure the model is asked to
fill and the structure we validate against are guaranteed to match.
"""

from pydantic import BaseModel, Field


class Soreness(BaseModel):
    """A single sore/affected area the athlete mentioned."""

    area: str = Field(..., description="Body area, e.g. 'forearms', 'lower back'.")
    severity: str | None = Field(
        None, description="Relative severity, e.g. 'mild', 'moderate', 'severe'."
    )
    note: str | None = Field(
        None, description="Any extra context, e.g. 'still cooked from Tuesday'."
    )


class Sleep(BaseModel):
    """Last night's sleep."""

    quality: str | None = Field(
        None, description="Subjective quality, e.g. 'good', 'poor', 'broken'."
    )
    hours: float | None = Field(None, description="Hours slept, if stated.")
    note: str | None = Field(None, description="Any extra context about sleep.")


class Meal(BaseModel):
    """A single meal or food item mentioned."""

    description: str = Field(..., description="What was eaten, e.g. 'chicken and rice'.")
    protein: str | None = Field(
        None, description="Protein source/amount, if identifiable."
    )
    note: str | None = Field(None, description="Any extra context, e.g. timing.")


class WOD(BaseModel):
    """Today's workout of the day."""

    movements: list[str] = Field(
        default_factory=list,
        description="Distinct movements in today's WOD, e.g. ['cleans', 'pull-ups'].",
    )
    note: str | None = Field(None, description="Any extra context about the WOD.")


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
