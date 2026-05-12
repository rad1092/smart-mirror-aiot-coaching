from __future__ import annotations

import argparse
from io import BytesIO

import cv2
import httpx
import numpy as np


def make_image_bytes() -> bytes:
    image = np.zeros((240, 240, 3), dtype=np.uint8)
    image[:] = (130, 120, 110)
    image[84:132, 72:168] = (80, 48, 35)
    image[132:204, 72:168] = (20, 20, 20)
    ok, encoded = cv2.imencode(".jpg", image)
    if not ok:
        raise RuntimeError("Failed to encode in-memory smoke-test image")
    return encoded.tobytes()


def start_exercise_session(
    client: httpx.Client,
    base_url: str,
    goal: str = "squat",
    user_id: str = "smoke_user",
) -> str:
    response = client.post(
        f"{base_url}/api/sessions/start",
        json={"user_id": user_id, "mode": "exercise", "goal": goal},
    )
    response.raise_for_status()
    session_id = response.json()["session_id"]
    print(f"[OK] exercise session start: {session_id}")
    return session_id


def upload_image(
    client: httpx.Client,
    base_url: str,
    endpoint: str,
    session_id: str,
    image_bytes: bytes,
) -> httpx.Response:
    files = {"file": ("smoke.jpg", BytesIO(image_bytes), "image/jpeg")}
    response = client.post(f"{base_url}{endpoint}", data={"session_id": session_id}, files=files)
    response.raise_for_status()
    return response


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Smoke test an already running exercise-only PC3 server. "
            "This script does not start the server and does not write image files."
        )
    )
    parser.add_argument("--base-url", default="http://localhost:9000")
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")
    image_bytes = make_image_bytes()

    with httpx.Client(timeout=10.0) as client:
        health = client.get(f"{base_url}/health")
        health.raise_for_status()
        print(f"[OK] health: {health.json()}")

        sensor = client.post(
            f"{base_url}/api/sensors/update",
            json={"temperature": 24.5, "humidity": 48, "illuminance": 360},
        )
        sensor.raise_for_status()
        print(f"[OK] sensors/update: {sensor.json()['environment']}")

        baseline_user_id = "smoke_user"
        saved_baseline = client.post(
            f"{base_url}/api/baselines/users/{baseline_user_id}/capture",
            data={"slot_type": "face_front"},
            files={"file": ("smoke.jpg", BytesIO(image_bytes), "image/jpeg")},
        )
        saved_baseline.raise_for_status()
        if not saved_baseline.json()["valid"]:
            raise RuntimeError("face_front baseline capture should be valid for the smoke image")
        print("[OK] baseline capture face_front")

        exercise_session = start_exercise_session(client, base_url, "squat", baseline_user_id)
        exercise = upload_image(
            client,
            base_url,
            "/api/analyze/exercise",
            exercise_session,
            image_bytes,
        )
        exercise_body = exercise.json()
        if "coaching" in exercise_body:
            raise RuntimeError("exercise frame update must not return coaching")
        print(f"[OK] analyze/exercise frame update: {exercise_body['exercise']}")

        stop = client.post(f"{base_url}/api/sessions/{exercise_session}/stop")
        stop.raise_for_status()
        stop_body = stop.json()
        if not stop_body.get("coaching"):
            raise RuntimeError("exercise session stop should return coaching in mock mode")
        print("[OK] exercise session stop returns coaching")

        removed = client.post(
            f"{base_url}/api/analyze/grooming",
            data={"session_id": exercise_session},
            files={"file": ("smoke.jpg", BytesIO(image_bytes), "image/jpeg")},
        )
        if removed.status_code != 404:
            raise RuntimeError(f"Expected removed grooming endpoint 404, got {removed.status_code}")
        print("[OK] removed non-exercise analyze endpoints are unavailable")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
