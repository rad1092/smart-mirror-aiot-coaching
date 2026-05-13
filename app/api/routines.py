from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.baseline.baseline_service import BaselineService
from app.dependencies import get_baseline_service, get_coach_client
from app.llm_client.coach_client import CoachClient
from app.schemas.routine import RecommendationRequest, RecommendationResponse


router = APIRouter(prefix="/api/routines", tags=["routines"])


@router.post("/profile", response_model=RecommendationResponse)
async def generate_profile_routine(
    request: RecommendationRequest,
    baseline_service: BaselineService = Depends(get_baseline_service),
    coach_client: CoachClient = Depends(get_coach_client),
) -> RecommendationResponse:
    _validate_profile(request)
    _validate_saved_baseline(request.user_id, baseline_service)
    try:
        return await coach_client.generate_routine(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _validate_profile(request: RecommendationRequest) -> None:
    profile = request.profile
    missing = []
    if profile.goal is None:
        missing.append("profile.goal")
    if profile.experience_level is None:
        missing.append("profile.experience_level")
    if profile.weekly_frequency is None:
        missing.append("profile.weekly_frequency")
    if profile.weight_kg is None:
        missing.append("profile.weight_kg")
    if profile.height_cm is None:
        missing.append("profile.height_cm")
    if missing:
        raise HTTPException(
            status_code=422,
            detail={
                "reason": "missing_profile_fields",
                "fields": missing,
            },
        )


def _validate_saved_baseline(user_id: str, baseline_service: BaselineService) -> None:
    source = baseline_service.get_baseline_source(user_id)
    baseline = baseline_service.get_baseline(user_id)
    body = baseline.get("body", {})
    face = baseline.get("face", {})
    missing = []
    if not face.get("face_front"):
        missing.append("face_front")
    for slot in ("body_front_full", "body_right_full", "body_left_full"):
        if not body.get(slot):
            missing.append(slot)
    if source != "user" or missing:
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "baseline_incomplete",
                "missing_slots": missing,
            },
        )
