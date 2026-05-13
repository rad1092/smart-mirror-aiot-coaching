from __future__ import annotations

import httpx

from app.config import Settings
from app.dependencies import get_coach_client
from app.llm_client.coach_client import CoachClient
from app.main import app


def _save_complete_baseline(client, user_id: str = "routine_user") -> None:
    response = client.post(
        f"/api/baselines/users/{user_id}",
        json={
            "face": {"face_front": {"captured": True}},
            "body": {
                "body_front_full": {"captured": True},
                "body_right_full": {"captured": True},
                "body_left_full": {"captured": True},
            },
        },
    )
    assert response.status_code == 200


def _routine_request(user_id: str = "routine_user") -> dict:
    return {
        "user_id": user_id,
        "profile": {
            "name": "Mirror User",
            "weight_kg": 70,
            "height_cm": 172,
            "goal": "lower_body_strength",
            "experience_level": "beginner",
            "weekly_frequency": "three_four",
            "limitations": ["knee"],
        },
        "baseline": {
            "ready": True,
            "completed_slots": [
                "face_front",
                "body_front_full",
                "body_right_full",
                "body_left_full",
            ],
        },
    }


def _pc2_routine_response() -> dict:
    return {
        "summary": "Weekly lower-body routine generated.",
        "weekly_focus": "Build stable squat mechanics.",
        "weekly_routine": [
            {
                "day_index": 1,
                "day_label": "Day 1",
                "focus": "Lower body",
                "exercises": [
                    {
                        "exercise": "squat",
                        "sets": 3,
                        "reps": 10,
                        "rest_sec": 75,
                        "focus": "knee alignment",
                        "reason": "Start with a controlled squat.",
                    },
                    {
                        "exercise": "knee_raise",
                        "sets": 2,
                        "reps": 12,
                        "rest_sec": 45,
                        "focus": "left right balance",
                        "reason": "Improve balance before intensity.",
                    },
                ],
            },
            {
                "day_index": 2,
                "day_label": "Day 2",
                "focus": "Support",
                "exercises": [
                    {
                        "exercise": "pushup",
                        "sets": 2,
                        "reps": 8,
                        "rest_sec": 60,
                        "focus": "upper support",
                        "reason": "Add support work.",
                    }
                ],
            },
        ],
        "cautions": ["Stop if knee pain appears."],
        "pc3_payload": {},
    }


def test_profile_routine_calls_pc2_with_sanitized_payload(client, monkeypatch):
    captured: dict = {}
    _save_complete_baseline(client)

    class DummyAsyncClient:
        def __init__(self, timeout: float) -> None:
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, json: dict):
            captured["url"] = url
            captured["json"] = json
            return httpx.Response(
                200,
                json=_pc2_routine_response(),
                request=httpx.Request("POST", url),
            )

    monkeypatch.setattr(httpx, "AsyncClient", DummyAsyncClient)
    app.dependency_overrides[get_coach_client] = lambda: CoachClient(
        Settings(
            _env_file=None,
            mock_llm=False,
            pc2_routine_api_url="http://pc2.local:7000/api/routine/profile",
        )
    )
    try:
        response = client.post("/api/routines/profile", json=_routine_request())
    finally:
        app.dependency_overrides.pop(get_coach_client, None)

    assert response.status_code == 200
    assert captured["url"] == "http://pc2.local:7000/api/routine/profile"
    assert captured["json"] == {
        "user_id": "routine_user",
        "user_goal": "lower body strength",
        "exercise_experience": "beginner",
        "available_days_per_week": 4,
        "restricted_body_parts": ["knee"],
        "purpose": "pre_exercise_routine",
        "profile_name": "Mirror User",
        "weight_kg": 70.0,
    }
    body = response.json()
    assert body["source"] == "ai"
    assert body["difficulty"] == "easy"
    assert body["start_exercise_type"] == "squat"
    assert [item["exercise_type"] for item in body["items"]] == ["squat", "knee_raise", "pushup"]
    assert "Build stable squat mechanics." in body["reason_lines"]


def test_profile_routine_rejects_missing_profile_fields_before_pc2(client):
    _save_complete_baseline(client)
    payload = _routine_request()
    payload["profile"]["goal"] = None

    response = client.post("/api/routines/profile", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"]["reason"] == "missing_profile_fields"
    assert "profile.goal" in response.json()["detail"]["fields"]


def test_profile_routine_rejects_incomplete_saved_baseline(client):
    response = client.post("/api/routines/profile", json=_routine_request("missing_baseline_user"))

    assert response.status_code == 409
    assert response.json()["detail"]["reason"] == "baseline_incomplete"
    assert "face_front" in response.json()["detail"]["missing_slots"]


def test_profile_routine_rejects_invalid_limitation(client):
    _save_complete_baseline(client)
    payload = _routine_request()
    payload["profile"]["limitations"] = ["neck"]

    response = client.post("/api/routines/profile", json=payload)

    assert response.status_code == 422


def test_profile_routine_returns_pc1_renderable_fallback_when_pc2_fails(client, monkeypatch):
    _save_complete_baseline(client)

    class FailingAsyncClient:
        def __init__(self, timeout: float) -> None:
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, json: dict):
            raise httpx.ConnectError("pc2 down", request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "AsyncClient", FailingAsyncClient)
    app.dependency_overrides[get_coach_client] = lambda: CoachClient(
        Settings(_env_file=None, mock_llm=False)
    )
    try:
        response = client.post("/api/routines/profile", json=_routine_request())
    finally:
        app.dependency_overrides.pop(get_coach_client, None)

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "basic"
    assert body["items"]
    assert body["start_exercise_type"] == body["items"][0]["exercise_type"]
    assert "PC2 unavailable" in body["reason_lines"][0]
