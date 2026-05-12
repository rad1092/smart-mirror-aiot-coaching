from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock

from app.schemas.coaching import CoachingResponse
from app.schemas.feature import ExerciseFeature, FeatureSet
from app.schemas.sensor import EnvironmentFeature
from app.schemas.session import Session, SessionResultResponse, SessionStatus


class MemoryStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._sessions: dict[str, Session] = {}
        self._features: dict[str, FeatureSet] = {}
        self._results: dict[str, SessionResultResponse] = {}
        self._environment = EnvironmentFeature()

    def reset(self) -> None:
        with self._lock:
            self._sessions.clear()
            self._features.clear()
            self._results.clear()
            self._environment = EnvironmentFeature()

    def create_session(self, session: Session) -> Session:
        with self._lock:
            self._sessions[session.session_id] = session
            self._features[session.session_id] = FeatureSet()
            return session

    def get_session(self, session_id: str) -> Session | None:
        with self._lock:
            return self._sessions.get(session_id)

    def set_status(self, session_id: str, status: SessionStatus) -> Session | None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            updated = session.model_copy(
                update={"status": status, "updated_at": datetime.now(timezone.utc)}
            )
            self._sessions[session_id] = updated
            return updated

    def touch_session(self, session_id: str) -> None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is not None:
                self._sessions[session_id] = session.model_copy(
                    update={"updated_at": datetime.now(timezone.utc)}
                )

    def get_features(self, session_id: str) -> FeatureSet:
        with self._lock:
            return self._features.get(session_id, FeatureSet())

    def set_exercise_feature(self, session_id: str, feature: ExerciseFeature) -> FeatureSet:
        with self._lock:
            features = self._features.get(session_id, FeatureSet())
            features.exercise = feature
            self._features[session_id] = features
            self.touch_session(session_id)
            return features

    def set_result(self, result: SessionResultResponse) -> SessionResultResponse:
        with self._lock:
            self._results[result.session_id] = result
            return result

    def get_result(self, session_id: str) -> SessionResultResponse | None:
        with self._lock:
            return self._results.get(session_id)

    def update_environment(self, environment: EnvironmentFeature) -> EnvironmentFeature:
        with self._lock:
            current = self._environment.model_dump()
            incoming = environment.model_dump(exclude_none=True)
            current.update(incoming)
            self._environment = EnvironmentFeature(**current)
            return self._environment

    def get_environment(self) -> EnvironmentFeature:
        with self._lock:
            return self._environment
