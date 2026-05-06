from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.coaching import CoachingResponse
from app.schemas.sensor import EnvironmentFeature


ExerciseState = Literal["up", "down", "idle"]
SessionModeLiteral = Literal["exercise", "grooming", "outfit", "outing"]


class ExerciseFeature(BaseModel):
    type: str = "squat"
    count: int = 0
    state: ExerciseState = "idle"
    stability_score: float = Field(default=0.0, ge=0.0, le=1.0)
    posture_errors: list[str] = Field(default_factory=list)


class FaceFeature(BaseModel):
    brightness: float = Field(ge=0.0, le=1.0)
    redness: float = Field(ge=0.0, le=1.0)
    beard_shadow: float = Field(ge=0.0, le=1.0)


class ColorInfo(BaseModel):
    name: str
    rgb: list[int]


class OutfitFeature(BaseModel):
    top_color: ColorInfo
    bottom_color: ColorInfo
    contrast_score: float = Field(ge=0.0, le=1.0)
    tone: Literal["dark", "neutral", "bright"]


class FeatureSet(BaseModel):
    exercise: ExerciseFeature | None = None
    face: FaceFeature | None = None
    outfit: OutfitFeature | None = None


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


class AnalysisCoachingResponse(BaseModel):
    session_id: str
    mode: SessionModeLiteral
    event: str
    features: FeatureSet
    baseline_diff: dict[str, Any] = Field(default_factory=dict)
    environment: EnvironmentFeature | None = None
    coaching: CoachingResponse | None
    purpose: str | None = None
