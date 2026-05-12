from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.sensor import EnvironmentFeature


ExerciseState = Literal["up", "down", "idle"]
SessionModeLiteral = Literal["exercise"]


class ExerciseFeature(BaseModel):
    type: str = "squat"
    count: int = 0
    state: ExerciseState = "idle"
    stability_score: float = Field(default=0.0, ge=0.0, le=1.0)
    posture_errors: list[str] = Field(default_factory=list)


class FeatureSet(BaseModel):
    exercise: ExerciseFeature | None = None


class FeaturePayload(BaseModel):
    user_id: str
    session_id: str
    mode: SessionModeLiteral
    event: str
    features: FeatureSet
    baseline_diff: dict[str, Any] = Field(default_factory=dict)
    environment: EnvironmentFeature | None = None
    purpose: str | None = None


class ExerciseAnalyzeResponse(BaseModel):
    session_id: str
    type: Literal["exercise_update"] = "exercise_update"
    exercise: ExerciseFeature
    feedback: str
