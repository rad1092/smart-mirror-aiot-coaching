from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


BaselineSlotType = Literal["face_front", "body_front_full", "body_right_full", "body_left_full"]
DifficultyLevel = Literal["easy", "normal", "challenge"]
ExerciseExperience = Literal["beginner", "casual", "consistent"]
ExerciseGoal = Literal[
    "build_stamina",
    "posture_correction",
    "lower_body_strength",
    "build_habit",
    "weight_management",
]
ExerciseLimitation = Literal["knee", "back", "shoulder", "ankle"]
ExerciseType = Literal["squat", "jumping_jack", "knee_raise", "lunge", "pushup"]
RoutineSource = Literal["ai", "basic"]
WeeklyExerciseFrequency = Literal["once_twice", "three_four", "five_plus"]


class RecommendationProfile(BaseModel):
    name: str | None = None
    weight_kg: float | None = Field(default=None, gt=0)
    height_cm: float | None = Field(default=None, gt=0)
    goal: ExerciseGoal | None = None
    experience_level: ExerciseExperience | None = None
    weekly_frequency: WeeklyExerciseFrequency | None = None
    limitations: list[ExerciseLimitation] = Field(default_factory=list)


class RecommendationBaseline(BaseModel):
    ready: bool = False
    completed_slots: list[BaselineSlotType] = Field(default_factory=list)


class RecommendationRequest(BaseModel):
    user_id: str = Field(min_length=1)
    profile: RecommendationProfile
    baseline: RecommendationBaseline = Field(default_factory=RecommendationBaseline)


class RoutineItemPayload(BaseModel):
    exercise_type: ExerciseType
    title: str
    reps: int = Field(ge=1)
    rest_sec: int = Field(ge=0)
    focus: str
    summary: str | None = None


class RecommendationResponse(BaseModel):
    source: RoutineSource
    difficulty: DifficultyLevel
    title: str
    description: str
    reason_lines: list[str] = Field(default_factory=list)
    estimated_minutes: int = Field(ge=1)
    start_exercise_type: ExerciseType
    items: list[RoutineItemPayload] = Field(default_factory=list)
