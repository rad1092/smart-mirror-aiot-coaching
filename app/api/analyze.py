from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.dependencies import (
    get_coach_client,
    get_face_analyzer,
    get_feature_builder,
    get_outfit_analyzer,
    get_pose_analyzer,
    get_store,
    get_trigger_engine,
)
from app.exercise_types import normalize_exercise_type
from app.features.feature_builder import FeatureBuilder
from app.llm_client.coach_client import CoachClient
from app.schemas.feature import (
    AnalysisCoachingResponse,
    ExerciseAnalyzeResponse,
    FeatureSet,
)
from app.schemas.session import Session, SessionResultResponse, SessionStatus
from app.storage.memory_store import MemoryStore
from app.triggers.trigger_engine import TriggerEngine
from app.vision.face_analyzer import FaceAnalyzer
from app.vision.frame_utils import decode_image_bytes
from app.vision.outfit_color_analyzer import OutfitColorAnalyzer
from app.vision.pose_analyzer import PoseAnalyzer
from app.websocket.manager import manager


router = APIRouter(prefix="/api/analyze", tags=["analyze"])


def _session_for_mode(
    session_id: str,
    expected_mode: str,
    store: MemoryStore,
) -> Session:
    session = store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.mode.value != expected_mode:
        raise HTTPException(
            status_code=400,
            detail=f"Session mode is '{session.mode.value}', but endpoint requires '{expected_mode}'.",
        )
    return session


async def _decode_upload(file: UploadFile):
    image_bytes = await file.read()
    try:
        return decode_image_bytes(image_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


async def _coaching_response(
    session: Session,
    event: str,
    features: FeatureSet,
    feature_builder: FeatureBuilder,
    trigger_engine: TriggerEngine,
    coach_client: CoachClient,
    purpose: str | None = None,
):
    payload = feature_builder.build_payload(
        session=session,
        event=event,
        features=features,
        purpose=purpose,
    )
    coaching = None
    if trigger_engine.should_call_llm(
        session.mode.value,
        payload.event,
        payload.features,
        payload.baseline_diff,
    ):
        coaching = await coach_client.generate(payload)
    return payload, coaching


@router.post("/exercise", response_model=ExerciseAnalyzeResponse)
async def analyze_exercise(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    store: MemoryStore = Depends(get_store),
    pose_analyzer: PoseAnalyzer = Depends(get_pose_analyzer),
) -> ExerciseAnalyzeResponse:
    session = _session_for_mode(session_id, "exercise", store)
    frame = await _decode_upload(file)
    previous = store.get_features(session_id).exercise
    exercise, feedback = pose_analyzer.analyze(frame, previous)
    exercise = exercise.model_copy(update={"type": normalize_exercise_type(session.goal)})
    store.set_exercise_feature(session_id, exercise)
    message = {
        "type": "exercise_update",
        "session_id": session_id,
        "count": exercise.count,
        "state": exercise.state,
        "feedback": feedback,
        "posture_errors": exercise.posture_errors,
        "stability_score": exercise.stability_score,
    }
    await manager.broadcast(session_id, message)
    return ExerciseAnalyzeResponse(
        session_id=session_id,
        exercise=exercise,
        feedback=feedback,
    )


@router.post("/grooming", response_model=AnalysisCoachingResponse)
async def analyze_grooming(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    store: MemoryStore = Depends(get_store),
    face_analyzer: FaceAnalyzer = Depends(get_face_analyzer),
    feature_builder: FeatureBuilder = Depends(get_feature_builder),
    trigger_engine: TriggerEngine = Depends(get_trigger_engine),
    coach_client: CoachClient = Depends(get_coach_client),
) -> AnalysisCoachingResponse:
    session = _session_for_mode(session_id, "grooming", store)
    frame = await _decode_upload(file)
    face = face_analyzer.analyze(frame)
    features = store.set_face_feature(session_id, face)
    payload, coaching = await _coaching_response(
        session,
        "analysis_completed",
        features,
        feature_builder,
        trigger_engine,
        coach_client,
    )
    completed = store.set_status(session_id, SessionStatus.completed) or session
    store.set_result(
        SessionResultResponse(
            session_id=session_id,
            status=completed.status,
            features=payload.features,
            baseline_diff=payload.baseline_diff,
            environment=payload.environment,
            coaching=coaching,
        )
    )
    return AnalysisCoachingResponse(
        session_id=session_id,
        mode=session.mode.value,
        event=payload.event,
        features=payload.features,
        baseline_diff=payload.baseline_diff,
        environment=payload.environment,
        coaching=coaching,
    )


@router.post("/outfit", response_model=AnalysisCoachingResponse)
async def analyze_outfit(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    purpose: str | None = Form(None),
    store: MemoryStore = Depends(get_store),
    outfit_analyzer: OutfitColorAnalyzer = Depends(get_outfit_analyzer),
    feature_builder: FeatureBuilder = Depends(get_feature_builder),
    trigger_engine: TriggerEngine = Depends(get_trigger_engine),
    coach_client: CoachClient = Depends(get_coach_client),
) -> AnalysisCoachingResponse:
    session = _session_for_mode(session_id, "outfit", store)
    frame = await _decode_upload(file)
    outfit = outfit_analyzer.analyze(frame)
    features = store.set_outfit_feature(session_id, outfit)
    payload, coaching = await _coaching_response(
        session,
        "analysis_completed",
        features,
        feature_builder,
        trigger_engine,
        coach_client,
        purpose=purpose,
    )
    completed = store.set_status(session_id, SessionStatus.completed) or session
    store.set_result(
        SessionResultResponse(
            session_id=session_id,
            status=completed.status,
            features=payload.features,
            baseline_diff=payload.baseline_diff,
            environment=payload.environment,
            coaching=coaching,
        )
    )
    return AnalysisCoachingResponse(
        session_id=session_id,
        mode=session.mode.value,
        event=payload.event,
        purpose=purpose,
        features=payload.features,
        baseline_diff=payload.baseline_diff,
        environment=payload.environment,
        coaching=coaching,
    )


@router.post("/outing", response_model=AnalysisCoachingResponse)
async def analyze_outing(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    purpose: str = Form(...),
    store: MemoryStore = Depends(get_store),
    face_analyzer: FaceAnalyzer = Depends(get_face_analyzer),
    outfit_analyzer: OutfitColorAnalyzer = Depends(get_outfit_analyzer),
    feature_builder: FeatureBuilder = Depends(get_feature_builder),
    trigger_engine: TriggerEngine = Depends(get_trigger_engine),
    coach_client: CoachClient = Depends(get_coach_client),
) -> AnalysisCoachingResponse:
    session = _session_for_mode(session_id, "outing", store)
    frame = await _decode_upload(file)
    face = face_analyzer.analyze(frame)
    outfit = outfit_analyzer.analyze(frame)
    store.set_face_feature(session_id, face)
    features = store.set_outfit_feature(session_id, outfit)
    payload, coaching = await _coaching_response(
        session,
        "analysis_completed",
        features,
        feature_builder,
        trigger_engine,
        coach_client,
        purpose=purpose,
    )
    completed = store.set_status(session_id, SessionStatus.completed) or session
    store.set_result(
        SessionResultResponse(
            session_id=session_id,
            status=completed.status,
            features=payload.features,
            baseline_diff=payload.baseline_diff,
            environment=payload.environment,
            coaching=coaching,
        )
    )
    return AnalysisCoachingResponse(
        session_id=session_id,
        mode=session.mode.value,
        event=payload.event,
        purpose=purpose,
        features=payload.features,
        baseline_diff=payload.baseline_diff,
        environment=payload.environment,
        coaching=coaching,
    )
