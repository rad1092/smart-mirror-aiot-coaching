from __future__ import annotations

from datetime import date

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import ValidationError

from app.baseline.baseline_service import BaselineService
from app.dependencies import get_baseline_service, get_coach_client
from app.llm_client.coach_client import CoachClient
from app.schemas.routine import RecommendationRequest, RecommendationResponse, RoutineDayResponse


router = APIRouter(prefix="/api/routines", tags=["routines"])


@router.post("/profile", response_model=RecommendationResponse)
async def generate_profile_routine(
    payload: dict = Body(...),
    baseline_service: BaselineService = Depends(get_baseline_service),
    coach_client: CoachClient = Depends(get_coach_client),
) -> RecommendationResponse:
    request = _normalize_routine_request(payload)
    _validate_profile(request)
    _validate_saved_baseline(request.user_id, baseline_service)
    try:
        return await coach_client.generate_routine(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/profile/{user_id}/day", response_model=RoutineDayResponse)
async def get_profile_routine_day(
    user_id: str,
    target_date: date = Query(...),
    coach_client: CoachClient = Depends(get_coach_client),
) -> RoutineDayResponse:
    try:
        return await coach_client.get_routine_day(user_id, target_date)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail={"reason": "routine_day_not_found"},
            ) from exc
        raise HTTPException(
            status_code=502,
            detail={
                "reason": "pc2_routine_day_failed",
                "status_code": exc.response.status_code,
            },
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=503,
            detail={"reason": "pc2_routine_day_unavailable"},
        ) from exc
    except (TypeError, ValueError, ValidationError) as exc:
        raise HTTPException(
            status_code=502,
            detail={"reason": "invalid_pc2_routine_day_response"},
        ) from exc


def _normalize_routine_request(payload: dict) -> RecommendationRequest:
    try:
        if isinstance(payload.get("profile"), dict):
            return RecommendationRequest.model_validate(payload)
        return _flat_payload_to_recommendation_request(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _flat_payload_to_recommendation_request(payload: dict) -> RecommendationRequest:
    missing = [
        field
        for field in ("user_id", "user_goal", "exercise_experience", "available_days_per_week")
        if payload.get(field) in (None, "")
    ]
    if missing:
        raise HTTPException(
            status_code=422,
            detail={"reason": "missing_profile_fields", "fields": missing},
        )

    days = int(payload["available_days_per_week"])
    limitations, pc2_restricted_body_parts = _normalize_restricted_body_parts(
        payload.get("restricted_body_parts") or []
    )
    request_payload = {
        "user_id": str(payload["user_id"]),
        "profile": {
            "name": payload.get("profile_name"),
            "weight_kg": payload.get("weight_kg"),
            "height_cm": None,
            "goal": _goal_from_user_goal(payload.get("user_goal")),
            "experience_level": _experience_from_label(payload.get("exercise_experience")),
            "weekly_frequency": _frequency_from_days(days),
            "limitations": limitations,
        },
        "start_date": payload.get("start_date"),
        "purpose": payload.get("purpose"),
        "pc2_user_goal": str(payload["user_goal"]).strip(),
        "pc2_exercise_experience": str(payload["exercise_experience"]).strip(),
        "pc2_available_days_per_week": days,
        "pc2_restricted_body_parts": pc2_restricted_body_parts,
    }
    return RecommendationRequest.model_validate(request_payload)


def _validate_profile(request: RecommendationRequest) -> None:
    profile = request.profile
    missing = []
    if profile.goal is None:
        missing.append("profile.goal")
    if profile.experience_level is None:
        missing.append("profile.experience_level")
    if profile.weekly_frequency is None:
        missing.append("profile.weekly_frequency")
    if missing:
        raise HTTPException(
            status_code=422,
            detail={
                "reason": "missing_profile_fields",
                "fields": missing,
            },
        )


def _goal_from_user_goal(value) -> str:
    raw = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    mapping = {
        "build_stamina": "build_stamina",
        "체력_올리기": "build_stamina",
        "posture_correction": "posture_correction",
        "자세_교정": "posture_correction",
        "lower_body_strength": "lower_body_strength",
        "하체_강화": "lower_body_strength",
        "build_habit": "build_habit",
        "운동_습관_만들기": "build_habit",
        "weight_management": "weight_management",
        "체중_관리": "weight_management",
    }
    return mapping.get(raw, "build_habit")


def _experience_from_label(value) -> str:
    raw = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if raw in {"beginner", "초보", "처음_시작"}:
        return "beginner"
    if raw in {"consistent", "꾸준한_운동", "꾸준히_운동"}:
        return "consistent"
    return "casual"


def _frequency_from_days(days: int) -> str:
    if days <= 2:
        return "once_twice"
    if days <= 4:
        return "three_four"
    return "five_plus"


def _normalize_restricted_body_parts(values) -> tuple[list[str], list[str]]:
    if not isinstance(values, list):
        raise ValueError("restricted_body_parts must be a list.")
    mapping = {
        "knee": ("knee", "무릎"),
        "무릎": ("knee", "무릎"),
        "back": ("back", "허리"),
        "허리": ("back", "허리"),
        "shoulder": ("shoulder", "어깨"),
        "어깨": ("shoulder", "어깨"),
        "ankle": ("ankle", "발목"),
        "발목": ("ankle", "발목"),
    }
    limitations: list[str] = []
    pc2_parts: list[str] = []
    for value in values:
        key = str(value or "").strip().lower()
        if not key:
            continue
        if key not in mapping:
            raise ValueError(f"Unsupported restricted body part: {value}")
        limitation, label = mapping[key]
        if limitation not in limitations:
            limitations.append(limitation)
        if label not in pc2_parts:
            pc2_parts.append(label)
    return limitations, pc2_parts


def _validate_saved_baseline(user_id: str, baseline_service: BaselineService) -> None:
    source = baseline_service.get_baseline_source(user_id)
    baseline = baseline_service.get_baseline(user_id)
    body = baseline.get("body", {})
    face = baseline.get("face", {})
    missing = []
    if not face.get("face_front"):
        missing.append("face_front")
    for slot in ("body_front_full",):
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
