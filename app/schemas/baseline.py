from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class FaceBaseline(BaseModel):
    brightness: float = Field(ge=0.0, le=1.0)
    redness: float = Field(ge=0.0, le=1.0)
    beard_shadow: float = Field(ge=0.0, le=1.0)


class OutfitBaseline(BaseModel):
    preferred_tones: list[str] = Field(default_factory=list)
    preferred_colors: list[str] = Field(default_factory=list)


class EnvironmentBaseline(BaseModel):
    baseline_illuminance: float | None = None


class BaselineUpsertRequest(BaseModel):
    exercise: dict[str, Any] | None = None
    face: FaceBaseline | None = None
    outfit: OutfitBaseline | None = None
    environment: EnvironmentBaseline | None = None

    def to_updates(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)


class BaselineResponse(BaseModel):
    user_id: str
    source: Literal["user", "default"]
    baseline: dict[str, Any]


class BaselineUpsertResponse(BaselineResponse):
    status: Literal["saved"] = "saved"
