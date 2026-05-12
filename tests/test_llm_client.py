from __future__ import annotations

import asyncio

import httpx
import pytest

from app.config import Settings
from app.llm_client.coach_client import CoachClient
from app.schemas.coaching import CoachingResponse
from app.schemas.feature import (
    ColorInfo,
    ExerciseFeature,
    FaceFeature,
    FeaturePayload,
    FeatureSet,
    OutfitFeature,
)
from app.schemas.sensor import EnvironmentFeature


def _payload_for_mode(mode: str) -> FeaturePayload:
    features = FeatureSet()
    if mode == "exercise":
        features.exercise = ExerciseFeature(count=3, state="up", stability_score=0.8)
    if mode in {"grooming", "outing"}:
        features.face = FaceFeature(brightness=0.6, redness=0.2, beard_shadow=0.3)
    if mode in {"outfit", "outing"}:
        features.outfit = OutfitFeature(
            top_color=ColorInfo(name="navy", rgb=[35, 48, 80]),
            bottom_color=ColorInfo(name="black", rgb=[20, 20, 20]),
            contrast_score=0.42,
            tone="dark",
        )
    return FeaturePayload(
        user_id="default",
        session_id="sess_test",
        mode=mode,
        event="analysis_completed" if mode != "exercise" else "session_completed",
        features=features,
        baseline_diff={},
        environment=None,
        purpose="daily",
    )


@pytest.mark.parametrize("mode", ["exercise", "grooming", "outfit", "outing"])
def test_coach_client_mock_response_satisfies_schema(mode):
    client = CoachClient(Settings(mock_llm=True))

    response = asyncio.run(client.generate(_payload_for_mode(mode)))

    assert isinstance(response, CoachingResponse)
    assert response.summary
    assert response.mirror_message


def test_pc2_request_json_contains_only_exercise_contract_fields():
    client = CoachClient(Settings(mock_llm=False))
    payload = FeaturePayload(
        user_id="default",
        session_id="sess_test",
        mode="exercise",
        event="session_completed",
        features=FeatureSet(
            exercise=ExerciseFeature(type="pushup", count=5, state="up", stability_score=0.72),
            face=FaceFeature(brightness=0.6, redness=0.2, beard_shadow=0.3),
            outfit=OutfitFeature(
                top_color=ColorInfo(name="navy", rgb=[35, 48, 80]),
                bottom_color=ColorInfo(name="black", rgb=[20, 20, 20]),
                contrast_score=0.42,
                tone="dark",
            ),
        ),
        baseline_diff={
            "exercise": {"count_change": -2, "stability_change": -0.1},
            "face": {"brightness_diff": 0.1},
        },
        environment=EnvironmentFeature(temperature=24.5),
        purpose=None,
    )

    request_json = client.build_pc2_request_json(payload)

    assert request_json["mode"] == "exercise"
    assert request_json["event"] == "session_completed"
    assert set(request_json["features"]) == {"exercise"}
    assert request_json["features"]["exercise"]["type"] == "pushup"
    assert "face" not in request_json["features"]
    assert "outfit" not in request_json["features"]
    assert set(request_json["baseline_diff"]) == {"exercise"}
    assert request_json["environment"] == {"temperature": 24.5}
    assert "purpose" not in request_json
    assert _contains_none(request_json) is False


def test_pc2_response_fields_are_preserved(monkeypatch):
    captured: dict = {}

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
                json={
                    "summary": "Plan generated.",
                    "priority": "posture stability",
                    "exercise_plan": [
                        {
                            "exercise": "pushup",
                            "sets": 3,
                            "reps": 6,
                            "duration_sec": None,
                            "rest_sec": 60,
                            "focus": "slow tempo",
                            "reason": "Keep form stable.",
                        }
                    ],
                    "mirror_message": "Slow down and keep posture stable.",
                    "warnings": [],
                    "pc2_payload": {
                        "message": "Slow pushups first.",
                        "display_lines": ["slow tempo", "stable posture"],
                    },
                },
                request=httpx.Request("POST", url),
            )

    monkeypatch.setattr(httpx, "AsyncClient", DummyAsyncClient)
    client = CoachClient(
        Settings(
            mock_llm=False,
            pc2_coach_api_url="http://pc2.local:7000/api/coach/generate",
        )
    )
    payload = FeaturePayload(
        user_id="default",
        session_id="sess_test",
        mode="exercise",
        event="session_completed",
        features=FeatureSet(exercise=ExerciseFeature(type="pushup", count=5)),
        baseline_diff={},
    )

    response = asyncio.run(client.generate(payload))

    assert captured["url"] == "http://pc2.local:7000/api/coach/generate"
    assert captured["json"]["features"]["exercise"]["type"] == "pushup"
    assert response.exercise_plan[0].exercise == "pushup"
    assert response.pc2_payload is not None
    assert response.pc2_payload.display_lines == ["slow tempo", "stable posture"]


def test_non_exercise_real_mode_uses_local_mock_without_pc2_call(monkeypatch):
    async def fail_if_called(*args, **kwargs):
        raise AssertionError("non-exercise modes must not call PC2")

    class DummyAsyncClient:
        def __init__(self, timeout: float) -> None:
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        post = fail_if_called

    monkeypatch.setattr(httpx, "AsyncClient", DummyAsyncClient)
    client = CoachClient(Settings(mock_llm=False))

    response = asyncio.run(client.generate(_payload_for_mode("grooming")))

    assert response.summary
    assert response.priority == "lighting balance"


def _contains_none(value) -> bool:
    if value is None:
        return True
    if isinstance(value, dict):
        return any(_contains_none(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_none(item) for item in value)
    return False
