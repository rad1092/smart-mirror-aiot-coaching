from __future__ import annotations

import argparse
from io import BytesIO

import cv2
import httpx
import numpy as np


def make_image_bytes() -> bytes:
    image = np.zeros((240, 240, 3), dtype=np.uint8)
    image[:] = (120, 120, 120)
    image[40:132, 72:168] = (120, 105, 150)
    image[84:132, 72:168] = (80, 48, 35)
    image[132:204, 72:168] = (20, 20, 20)
    ok, encoded = cv2.imencode(".jpg", image)
    if not ok:
        raise RuntimeError("Failed to encode in-memory smoke-test image")
    return encoded.tobytes()


def start_session(
    client: httpx.Client,
    base_url: str,
    mode: str,
    goal: str | None = None,
    user_id: str = "default",
) -> str:
    payload: dict[str, str] = {"user_id": user_id, "mode": mode}
    if goal:
        payload["goal"] = goal
    response = client.post(f"{base_url}/api/sessions/start", json=payload)
    response.raise_for_status()
    session_id = response.json()["session_id"]
    print(f"[OK] session start {mode}: {session_id}")
    return session_id


def upload_image(
    client: httpx.Client,
    base_url: str,
    endpoint: str,
    session_id: str,
    image_bytes: bytes,
    extra_data: dict[str, str] | None = None,
) -> httpx.Response:
    data = {"session_id": session_id}
    if extra_data:
        data.update(extra_data)
    files = {"file": ("smoke.jpg", BytesIO(image_bytes), "image/jpeg")}
    response = client.post(f"{base_url}{endpoint}", data=data, files=files)
    response.raise_for_status()
    return response


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Smoke test an already running PC3 server. "
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
        default_baseline = client.get(f"{base_url}/api/baselines/users/{baseline_user_id}")
        default_baseline.raise_for_status()
        print(f"[OK] baseline default source: {default_baseline.json()['source']}")

        saved_baseline = client.post(
            f"{base_url}/api/baselines/users/{baseline_user_id}",
            json={
                "exercise": {
                    "squat": {
                        "avg_count": 4,
                        "avg_stability_score": 0.7,
                    }
                },
                "face": {
                    "brightness": 0.55,
                    "redness": 0.2,
                    "beard_shadow": 0.35,
                },
                "outfit": {
                    "preferred_tones": ["navy"],
                    "preferred_colors": ["navy", "white"],
                },
            },
        )
        saved_baseline.raise_for_status()
        if saved_baseline.json()["source"] != "user":
            raise RuntimeError("user baseline should be stored with source=user")
        print("[OK] baseline upsert source: user")

        exercise_session = start_session(client, base_url, "exercise", "squat", baseline_user_id)
        exercise = upload_image(
            client,
            base_url,
            "/api/analyze/exercise",
            exercise_session,
            image_bytes,
        )
        exercise_body = exercise.json()
        if "coaching" in exercise_body:
            raise RuntimeError("exercise frame_update must not return coaching")
        print(f"[OK] analyze/exercise frame_update: {exercise_body['exercise']}")

        stop = client.post(f"{base_url}/api/sessions/{exercise_session}/stop")
        stop.raise_for_status()
        stop_body = stop.json()
        if not stop_body.get("coaching"):
            raise RuntimeError("exercise session stop should return coaching in mock mode")
        print("[OK] exercise session stop returns coaching")

        for mode, endpoint in [
            ("grooming", "/api/analyze/grooming"),
            ("outfit", "/api/analyze/outfit"),
            ("outing", "/api/analyze/outing"),
        ]:
            session_id = start_session(client, base_url, mode)
            extra = {"purpose": "daily"} if mode in {"outfit", "outing"} else None
            response = upload_image(client, base_url, endpoint, session_id, image_bytes, extra)
            body = response.json()
            print(
                f"[OK] {endpoint}: "
                f"features={bool(body.get('features'))}, "
                f"environment={bool(body.get('environment'))}, "
                f"coaching={bool(body.get('coaching'))}"
            )

        mismatch = client.post(
            f"{base_url}/api/analyze/grooming",
            data={"session_id": exercise_session},
            files={"file": ("smoke.jpg", BytesIO(image_bytes), "image/jpeg")},
        )
        if mismatch.status_code != 400:
            raise RuntimeError(f"Expected mode mismatch 400, got {mismatch.status_code}")
        print("[OK] mode mismatch returns 400")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
