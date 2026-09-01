# app/schemas/verdict.py
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Verdict(BaseModel):
    """Schema returned by the Gemini structured output judge."""
    fit: Literal["high", "medium", "low", "unknown"]
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score strictly between 0.0 and 1.0 reflecting evidence completeness",
    )
    reasoning: str = Field(
        ...,
        min_length=10,
        description="Grounded explanation strictly referencing provided signals without fabrication",
    )
    follow_up_question: str = Field(
        ...,
        min_length=5,
        description="Key open question to resolve uncertainty",
    )


class VerdictCreate(Verdict):
    company_id: int
    model: str = Field(..., max_length=100)


class VerdictRead(Verdict):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    model: str
    created_at: datetime
