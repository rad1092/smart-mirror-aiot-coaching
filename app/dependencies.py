from __future__ import annotations

from app.baseline.baseline_service import BaselineService
from app.baseline.baseline_store import BaselineStore
from app.config import get_settings
from app.features.feature_builder import FeatureBuilder
from app.llm_client.coach_client import CoachClient
from app.sensors.sensor_service import SensorService
from app.storage.memory_store import MemoryStore
from app.triggers.trigger_engine import TriggerEngine
from app.vision.face_analyzer import FaceAnalyzer
from app.vision.outfit_color_analyzer import OutfitColorAnalyzer
from app.vision.pose_analyzer import PoseAnalyzer


settings = get_settings()
store = MemoryStore()
sensor_service = SensorService(store)
baseline_service = BaselineService(
    BaselineStore(
        settings.resolve_path(settings.baseline_path),
        settings.resolve_path(settings.baseline_db_path),
    )
)
trigger_engine = TriggerEngine()
coach_client = CoachClient(settings)
feature_builder = FeatureBuilder(sensor_service, baseline_service)
pose_analyzer = PoseAnalyzer(
    pose_model_path=settings.resolve_path(settings.pose_model_path),
    exercise_thresholds_path=settings.resolve_path(settings.config_exercise_thresholds),
    exercise_rules_path=settings.resolve_path(settings.exercise_rules_path),
    use_mediapipe_tasks=settings.use_mediapipe_tasks,
)
face_analyzer = FaceAnalyzer(settings.resolve_path(settings.config_face_thresholds))
outfit_analyzer = OutfitColorAnalyzer(
    thresholds_path=settings.resolve_path(settings.config_outfit_thresholds),
    color_rules_path=settings.resolve_path(settings.color_rules_path),
)


def get_store() -> MemoryStore:
    return store


def get_sensor_service() -> SensorService:
    return sensor_service


def get_baseline_service() -> BaselineService:
    return baseline_service


def get_trigger_engine() -> TriggerEngine:
    return trigger_engine


def get_coach_client() -> CoachClient:
    return coach_client


def get_feature_builder() -> FeatureBuilder:
    return feature_builder


def get_pose_analyzer() -> PoseAnalyzer:
    return pose_analyzer


def get_face_analyzer() -> FaceAnalyzer:
    return face_analyzer


def get_outfit_analyzer() -> OutfitColorAnalyzer:
    return outfit_analyzer
