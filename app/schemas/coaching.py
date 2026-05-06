from __future__ import annotations

from pydantic import BaseModel, Field


class RoutineItem(BaseModel):
    title: str
    description: str


class CoachingResponse(BaseModel):
    summary: str
    priority: str
    routine: list[RoutineItem] = Field(default_factory=list)
    mirror_message: str
    warnings: list[str] = Field(default_factory=list)
