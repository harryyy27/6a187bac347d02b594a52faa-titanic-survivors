"""Request/response models for the API endpoints (Pydantic v2)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PassengerFeatures(BaseModel):
    """Raw passenger fields accepted by the /predict endpoint."""

    Pclass: int = Field(default=3, ge=1, le=3, description="Ticket class (1, 2, or 3)")
    Sex: Literal["male", "female"] = Field(default="male")
    Age: float = Field(default=30.0, ge=0, le=120)
    SibSp: int = Field(default=0, ge=0, description="Siblings/spouses aboard")
    Parch: int = Field(default=0, ge=0, description="Parents/children aboard")
    Fare: float = Field(default=32.2, ge=0)
    Embarked: Literal["C", "Q", "S"] = Field(default="S")


class PredictRequest(PassengerFeatures):
    """Single-passenger prediction request."""


class PredictResponse(BaseModel):
    """Prediction result for a single passenger."""

    prediction: int
    probability: float
    label: str


class HealthResponse(BaseModel):
    status: str = "ok"


class ReadyResponse(BaseModel):
    status: str = "ready"
