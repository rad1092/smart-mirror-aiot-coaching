from __future__ import annotations

import logging

import httpx

from app.config import Settings
from app.schemas.coaching import CoachingResponse, ExercisePlanItem, PC2Payload, RoutineItem
from app.schemas.feature import FeaturePayload


logger = logging.getLogger(__name__)


class CoachClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def generate(self, payload: FeaturePayload) -> CoachingResponse:
        if self._settings.mock_llm or payload.mode != "exercise" or payload.event != "session_completed":
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
                "exercise": exercise.model_dump(mode="json", exclude_none=True),
            },
        }

        exercise_diff = payload.baseline_diff.get("exercise") if payload.baseline_diff else None
        request["baseline_diff"] = {"exercise": exercise_diff} if exercise_diff is not None else {}

        if payload.environment is not None:
            environment = payload.environment.model_dump(mode="json", exclude_none=True)
            if environment:
                request["environment"] = environment
        if payload.purpose:
            request["purpose"] = payload.purpose
        return request

    def _mock_response(self, payload: FeaturePayload) -> CoachingResponse:
        if payload.mode == "exercise":
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

        if payload.mode == "grooming":
            return CoachingResponse(
                summary="Grooming check completed from face brightness and tone features.",
                priority="lighting balance",
                routine=[
                    RoutineItem(
                        title="Check lighting",
                        description="Use even front lighting before making grooming decisions.",
                    )
                ],
                mirror_message="This is a visual check, not a medical diagnosis.",
                warnings=["Adjust products or shaving only if irritation is visible to you."],
            )

        if payload.mode == "outfit":
            return CoachingResponse(
                summary="Outfit color and contrast check completed.",
                priority="color balance",
                routine=[
                    RoutineItem(
                        title="Balance contrast",
                        description="If the top and bottom contrast is too strong, add a neutral layer.",
                    )
                ],
                mirror_message="Confirm the outfit once more under the actual destination lighting.",
                warnings=["Color analysis can change under different lighting."],
            )

        return CoachingResponse(
            summary="Outing check completed from face, outfit, and room environment features.",
            priority="final purpose fit",
            routine=[
                RoutineItem(
                    title="Final check",
                    description="Review color balance and lighting before leaving.",
                )
            ],
            mirror_message="The result only uses extracted features, not raw images.",
            warnings=["PC3 does not infer details that are not visible in the input frame."],
        )
