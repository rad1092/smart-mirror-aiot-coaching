from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.baseline.baseline_service import BaselineService
from app.dependencies import get_baseline_service, get_pose_analyzer
from app.schemas.baseline import (
    BaselineCaptureResponse,
    BaselineResponse,
    BaselineUpsertRequest,
    BaselineUpsertResponse,
)
from app.vision.frame_utils import decode_image_bytes
from app.vision.pose_analyzer import PoseAnalyzer


router = APIRouter(prefix="/api/baselines", tags=["baselines"])


@router.get("/users/{user_id}", response_model=BaselineResponse)
def get_user_baseline(
    user_id: str,
    baseline_service: BaselineService = Depends(get_baseline_service),
) -> BaselineResponse:
    return BaselineResponse(
        user_id=user_id,
        source=baseline_service.get_baseline_source(user_id),
        baseline=baseline_service.get_baseline(user_id),
    )


@router.post("/users/{user_id}", response_model=BaselineUpsertResponse)
def upsert_user_baseline(
    user_id: str,
    request: BaselineUpsertRequest,
    baseline_service: BaselineService = Depends(get_baseline_service),
) -> BaselineUpsertResponse:
    baseline = baseline_service.upsert_baseline(user_id, request.to_updates())
    return BaselineUpsertResponse(
        user_id=user_id,
        source="user",
        baseline=baseline,
    )


@router.post("/users/{user_id}/capture", response_model=BaselineCaptureResponse)
async def capture_baseline_slot(
    user_id: str,
    slot_type: str = Form(...),
    file: UploadFile = File(...),
    pose_analyzer: PoseAnalyzer = Depends(get_pose_analyzer),
    baseline_service: BaselineService = Depends(get_baseline_service),
) -> BaselineCaptureResponse:
    valid_slot_types = {"face_front", "body_front_full", "body_right_full", "body_left_full"}
    if slot_type not in valid_slot_types:
        raise HTTPException(status_code=400, detail=f"Unknown slot_type: {slot_type!r}")

    image_bytes = await file.read()
    try:
        frame = decode_image_bytes(image_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    mean_brightness = float(frame.mean()) / 255.0
    if slot_type == "face_front":
        valid = mean_brightness > 0.15
        if valid:
            baseline_service.upsert_baseline(
                user_id,
                {"face": {"face_front": {"captured": True, "brightness": round(mean_brightness, 3)}}},
            )
        return BaselineCaptureResponse(
            valid=valid,
            slot_type=slot_type,
            reason=None if valid else "Frame is too dark. Check the room lighting.",
        )

    if pose_analyzer.use_mediapipe:
        validation = pose_analyzer.validate_body_baseline(frame)
        valid = bool(validation["valid"])
        if valid:
            body_update: dict = {"captured": True}
            proportions = validation.get("proportions")
            if proportions is not None:
                body_update.update(proportions)
            baseline_service.upsert_baseline(user_id, {"body": {slot_type: body_update}})
        return BaselineCaptureResponse(
            valid=valid,
            slot_type=slot_type,
            reason=None if valid else str(validation["reason"]),
        )

    valid = mean_brightness > 0.10
    if valid:
        baseline_service.upsert_baseline(user_id, {"body": {slot_type: {"captured": True}}})
    return BaselineCaptureResponse(
        valid=valid,
        slot_type=slot_type,
        reason=None if valid else "Frame is too dark. Check the room lighting.",
    )
