from __future__ import annotations

import asyncio

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
