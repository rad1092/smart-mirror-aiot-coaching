from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.config import Settings, get_settings
from app.dependencies import (
    get_coach_client,
    get_feature_builder,
    get_store,
    get_trigger_engine,
)
from app.features.feature_builder import FeatureBuilder
from app.llm_client.coach_client import CoachClient
from app.schemas.session import (
    Session,
    SessionResultResponse,
    SessionStartRequest,
    SessionStartResponse,
    SessionStatus,
    SessionStopResponse,
)
from app.storage.memory_store import MemoryStore
from app.triggers.trigger_engine import TriggerEngine


router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("/start", response_model=SessionStartResponse)
def start_session(
    request: SessionStartRequest,
    settings: Settings = Depends(get_settings),
    store: MemoryStore = Depends(get_store),
) -> SessionStartResponse:
    session_id = f"sess_{uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    session = Session(
        session_id=session_id,
        user_id=request.user_id,
        mode=request.mode,
        goal=request.goal,
        status=SessionStatus.running,
        created_at=now,
        updated_at=now,
    )
    store.create_session(session)
    return SessionStartResponse(
        **session.model_dump(),
        ws_url=settings.ws_url_for_session(session_id),
    )


@router.post("/{session_id}/stop", response_model=SessionStopResponse)
async def stop_session(
    session_id: str,
    store: MemoryStore = Depends(get_store),
    feature_builder: FeatureBuilder = Depends(get_feature_builder),
    trigger_engine: TriggerEngine = Depends(get_trigger_engine),
    coach_client: CoachClient = Depends(get_coach_client),
) -> SessionStopResponse:
    session = store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    stopped_session = store.set_status(session_id, SessionStatus.stopped)
    if stopped_session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    features = store.get_features(session_id)
    payload = feature_builder.build_payload(
        stopped_session,
        event="session_completed",
        features=features,
    )
    coaching = None
    if trigger_engine.should_call_llm(
        stopped_session.mode.value,
        payload.event,
        payload.features,
        payload.baseline_diff,
    ):
        coaching = await coach_client.generate(payload)

    result = SessionStopResponse(
        session_id=session_id,
        status=stopped_session.status,
        features=payload.features,
        baseline_diff=payload.baseline_diff,
        environment=payload.environment,
        coaching=coaching,
    )
    store.set_result(result)
    return result


@router.get("/{session_id}/result", response_model=SessionResultResponse)
def get_session_result(
    session_id: str,
    store: MemoryStore = Depends(get_store),
    feature_builder: FeatureBuilder = Depends(get_feature_builder),
) -> SessionResultResponse:
    result = store.get_result(session_id)
    if result is not None:
        return result

    session = store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    features = store.get_features(session_id)
    payload = feature_builder.build_payload(
        session,
        event="current_state",
        features=features,
    )
    return SessionResultResponse(
        session_id=session_id,
        status=session.status,
        features=payload.features,
        baseline_diff=payload.baseline_diff,
        environment=payload.environment,
        coaching=None,
    )
