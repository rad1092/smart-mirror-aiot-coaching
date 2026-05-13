from __future__ import annotations

import logging

import httpx

from app.config import Settings
from app.schemas.coaching import CoachingResponse, ExercisePlanItem, PC2Payload, RoutineItem
from app.schemas.feature import FeaturePayload


logger = logging.getLogger(__name__)


PC2_EXERCISE_FIELDS = {
    "type",
    "count",
    "rep_count",
    "state",
    "stability_score",
    "posture_errors",
    "squat_depth",
    "knee_angle",
    "back_angle",
    "duration_sec",
    "duration_seconds",
    "tempo",
}
PC2_BASELINE_DIFF_FIELDS = {
    "count_change",
    "stability_change",
    "knee_angle_change",
    "squat_depth_change",
    "duration_change",
}


class CoachClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def generate(self, payload: FeaturePayload) -> CoachingResponse:
        if self._settings.mock_llm:
            return self._mock_response(payload)

        try:
            async with httpx.AsyncClient(timeout=self._settings.pc2_timeout_seconds) as client:
                response = await client.post(
                    self._settings.pc2_coach_api_url,
                    json=self.build_pc2_request_json(payload),
                )
                response.raise_for_status()
            return CoachingResponse.model_validate(response.json())
        except Exception:
            logger.exception("PC2 Coach API call failed. Falling back to mock coaching.")
            return self._mock_response(payload)

    def measurement_quality_response(self, payload: FeaturePayload, quality: dict) -> CoachingResponse:
        exercise = payload.features.exercise
        count = exercise.count if exercise else 0
        exercise_type = exercise.type if exercise else "squat"
        confidence = float(quality.get("measurement_confidence", 0.0))
        message = "Measurement quality is low. Re-run the set with the full body clearly in frame."
        return CoachingResponse(
            summary=(
                f"PC3 measured {count} reps, but the frame quality was not reliable enough "
                f"for PC2 coaching. Measurement confidence: {confidence:.2f}."
            ),
            priority="measurement quality",
            routine=[
                RoutineItem(
                    title="Retake the set",
                    description="Keep the locked user centered, visible from head to feet, and avoid other people entering.",
                )
            ],
            exercise_plan=[
                ExercisePlanItem(
                    exercise=exercise_type,
                    sets=1,
                    reps=max(4, count if count else 6),
                    rest_sec=60,
                    focus="clear camera framing",
                    reason="PC3 skipped PC2 because the pose measurement quality was below the configured threshold.",
                )
            ],
            mirror_message=message,
            warnings=["PC2 feedback was skipped because pose measurement quality was low."],
            pc2_payload=PC2Payload(
                message=message,
                display_lines=[
                    "Keep your whole body visible",
                    "Stay as the locked target user",
                    "Repeat the set before requesting coaching",
                ],
            ),
        )

    def build_pc2_request_json(self, payload: FeaturePayload) -> dict:
        exercise = payload.features.exercise
        if payload.mode != "exercise" or payload.event != "session_completed" or exercise is None:
            raise ValueError("PC2 coach requests are only supported for completed exercise sessions.")

        request: dict = {
            "user_id": payload.user_id,
            "session_id": payload.session_id,
            "mode": "exercise",
            "event": "session_completed",
            "features": {
                "exercise": self._dump_pc2_exercise(exercise),
            },
        }

        exercise_diff = payload.baseline_diff.get("exercise") if payload.baseline_diff else None
        request["baseline_diff"] = (
            {"exercise": self._dump_pc2_baseline_diff(exercise_diff)}
            if exercise_diff is not None
            else {}
        )

        if payload.environment is not None:
            environment = payload.environment.model_dump(mode="json", exclude_none=True)
            if environment:
                request["environment"] = environment
        if payload.purpose:
            request["purpose"] = payload.purpose
        return request

    def _dump_pc2_exercise(self, exercise) -> dict:
        raw = exercise.model_dump(mode="json", exclude_none=True)
        return {key: value for key, value in raw.items() if key in PC2_EXERCISE_FIELDS}

    def _dump_pc2_baseline_diff(self, exercise_diff: dict) -> dict:
        return {
            key: value
            for key, value in exercise_diff.items()
            if key in PC2_BASELINE_DIFF_FIELDS and value is not None
        }

    def _mock_response(self, payload: FeaturePayload) -> CoachingResponse:
        exercise = payload.features.exercise
        count = exercise.count if exercise else 0
        exercise_type = exercise.type if exercise else "squat"
        mirror_message = "Keep the movement steady and prioritize posture over speed."
        return CoachingResponse(
            summary=f"Completed {count} reps. This feedback is based on posture stability and baseline diff.",
            priority="posture stability",
            routine=[
                RoutineItem(
                    title="Check alignment",
                    description="Match your knees with your feet and slow down the next set.",
                )
            ],
            exercise_plan=[
                ExercisePlanItem(
                    exercise=exercise_type,
                    sets=3,
                    reps=max(4, count if count else 6),
                    rest_sec=60,
                    focus="controlled posture",
                    reason="Local mock coaching is active, so PC3 returns a safe default plan.",
                )
            ],
            mirror_message=mirror_message,
            warnings=["Stop exercising if you feel pain."],
            pc2_payload=PC2Payload(
                message=mirror_message,
                display_lines=["posture first", "steady tempo"],
            ),
        )
