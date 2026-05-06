from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def default_baseline_path() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "baseline_default.json"


def default_baseline_db_path() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "baselines.sqlite3"


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def default_pose_model_path() -> Path:
    return project_root() / "models" / "pose" / "pose_landmarker_lite.task"


def default_face_model_path() -> Path:
    return project_root() / "models" / "face" / "face_landmarker.task"


def default_segmenter_model_path() -> Path:
    return project_root() / "models" / "segmentation" / "selfie_segmenter.tflite"


def default_exercise_thresholds_path() -> Path:
    return project_root() / "config" / "exercise_thresholds.json"


def default_face_thresholds_path() -> Path:
    return project_root() / "config" / "face_thresholds.json"


def default_outfit_thresholds_path() -> Path:
    return project_root() / "config" / "outfit_thresholds.json"


def default_color_rules_path() -> Path:
    return project_root() / "data" / "color_rules.json"


def default_exercise_rules_path() -> Path:
    return project_root() / "data" / "exercise_rules.json"


class Settings(BaseSettings):
    service_name: str = "pc3-vision-gateway"
    pc2_coach_api_url: str = "http://localhost:8100/api/coach/generate"
    mock_llm: bool = True
    host: str = "127.0.0.1"
    port: int = 9000
    ws_public_host: str | None = None
    pc2_timeout_seconds: float = 5.0
    cors_allow_origins: str = (
        "http://localhost:1420,http://127.0.0.1:1420,tauri://localhost"
    )
    use_mediapipe_tasks: bool = False
    pose_model_path: Path = Field(default_factory=default_pose_model_path)
    face_model_path: Path = Field(default_factory=default_face_model_path)
    segmenter_model_path: Path = Field(default_factory=default_segmenter_model_path)
    config_exercise_thresholds: Path = Field(default_factory=default_exercise_thresholds_path)
    config_face_thresholds: Path = Field(default_factory=default_face_thresholds_path)
    config_outfit_thresholds: Path = Field(default_factory=default_outfit_thresholds_path)
    color_rules_path: Path = Field(default_factory=default_color_rules_path)
    exercise_rules_path: Path = Field(default_factory=default_exercise_rules_path)
    baseline_path: Path = Field(default_factory=default_baseline_path)
    baseline_db_path: Path = Field(default_factory=default_baseline_db_path)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def ws_host(self) -> str:
        if self.ws_public_host:
            return self.ws_public_host
        if self.host in {"0.0.0.0", "::"}:
            return "localhost"
        return self.host

    def ws_url_for_session(self, session_id: str) -> str:
        return f"ws://{self.ws_host}:{self.port}/ws/sessions/{session_id}"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]

    def resolve_path(self, value: Path) -> Path:
        if value.is_absolute():
            return value
        return project_root() / value


@lru_cache
def get_settings() -> Settings:
    return Settings()
