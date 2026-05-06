from __future__ import annotations

import argparse
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULTS = {
    "USE_MEDIAPIPE_TASKS": "false",
    "POSE_MODEL_PATH": "./models/pose/pose_landmarker_lite.task",
    "FACE_MODEL_PATH": "",
    "SEGMENTER_MODEL_PATH": "",
}


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_settings(env_file: Path) -> dict[str, str]:
    settings = DEFAULTS.copy()
    example = PROJECT_ROOT / ".env.example"
    settings.update({key: value for key, value in read_env_file(example).items() if key in settings})
    settings.update({key: value for key, value in read_env_file(env_file).items() if key in settings})
    return settings


def resolve_model_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def check_path(label: str, value: str, optional: bool = False) -> bool:
    if not value:
        level = "WARN" if optional else "INFO"
        print(f"[{level}] {label} model path not set; skipped")
        return False
    resolved = resolve_model_path(value)
    if resolved.exists():
        print(f"[OK] {label} model found: {resolved}")
        return True
    print(f"[WARN] {label} model missing: {resolved}")
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Check local PC3 vision model paths.")
    parser.add_argument("--env-file", default=".env", help="Path to .env file relative to project root.")
    args = parser.parse_args()

    env_path = Path(args.env_file)
    if not env_path.is_absolute():
        env_path = PROJECT_ROOT / env_path

    settings = load_settings(env_path)
    use_tasks = truthy(settings["USE_MEDIAPIPE_TASKS"])
    print(f"Checking model paths using env file: {env_path}")
    print(f"USE_MEDIAPIPE_TASKS={str(use_tasks).lower()}")

    pose_ok = check_path("pose", settings["POSE_MODEL_PATH"], optional=False)
    check_path("face", settings["FACE_MODEL_PATH"], optional=True)
    check_path("segmenter", settings["SEGMENTER_MODEL_PATH"], optional=True)

    if use_tasks and not pose_ok:
        print("[WARN] USE_MEDIAPIPE_TASKS=true but pose model is missing.")
    print("[INFO] fallback/mock mode remains available")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
