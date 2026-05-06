from __future__ import annotations

from datetime import datetime, timezone

from app.baseline.baseline_service import BaselineService
from app.baseline.baseline_store import BaselineStore
from app.features.feature_builder import FeatureBuilder
from app.schemas.feature import FaceFeature, FeatureSet
from app.schemas.sensor import EnvironmentFeature
from app.schemas.session import Session, SessionMode, SessionStatus
from app.sensors.sensor_service import SensorService
from app.storage.memory_store import MemoryStore


def test_feature_builder_builds_grooming_payload(baseline_path):
    store = MemoryStore()
    sensor_service = SensorService(store)
    sensor_service.update_environment(
        EnvironmentFeature(temperature=24.5, humidity=48, illuminance=360)
    )
    baseline_service = BaselineService(BaselineStore(baseline_path))
    builder = FeatureBuilder(sensor_service, baseline_service)
    now = datetime.now(timezone.utc)
    session = Session(
        session_id="sess_test",
        user_id="default",
        mode=SessionMode.grooming,
        goal=None,
        status=SessionStatus.running,
        created_at=now,
        updated_at=now,
    )
    features = FeatureSet(face=FaceFeature(brightness=0.62, redness=0.18, beard_shadow=0.44))

    payload = builder.build_payload(session, "analysis_completed", features)

    assert payload.mode == "grooming"
    assert payload.features.face is not None
    assert payload.baseline_diff["face"]["brightness_diff"] == -0.12
    assert payload.environment is not None
    assert payload.environment.temperature == 24.5
