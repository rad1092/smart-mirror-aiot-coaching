from __future__ import annotations

from datetime import date
import logging
from urllib.parse import quote

import httpx

from app.config import Settings
from app.schemas.coaching import CoachingResponse, ExercisePlanItem, PC2Payload, RoutineItem
from app.schemas.feature import FeaturePayload
from app.schemas.routine import (
    RecommendationRequest,
    RecommendationResponse,
    RoutineDayResponse,
    RoutineItemPayload,
    WeeklyRoutineDayPayload,
    WeeklyRoutineExercisePayload,
)


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
SUPPORTED_ROUTINE_EXERCISES = {"squat", "jumping_jack", "knee_raise", "lunge", "pushup"}
ROUTINE_EXERCISE_ALIASES = {
    "squat": "squat",
    "jumping_jack": "jumping_jack",
    "jumping jack": "jumping_jack",
    "jumping-jack": "jumping_jack",
    "knee_raise": "knee_raise",
    "knee raise": "knee_raise",
    "knee-raise": "knee_raise",
    "lunge": "lunge",
    "pushup": "pushup",
    "push up": "pushup",
    "push-up": "pushup",
    "push_up": "pushup",
}
GOAL_LABELS = {
    "build_stamina": "체력 올리기",
    "posture_correction": "자세 교정",
    "lower_body_strength": "하체 강화",
    "build_habit": "운동 습관 만들기",
    "weight_management": "체중 관리",
}
EXPERIENCE_LABELS = {
    "beginner": "초보",
    "casual": "가벼운 운동",
    "consistent": "꾸준한 운동",
}
LIMITATION_LABELS = {
    "knee": "무릎",
    "back": "허리",
    "shoulder": "어깨",
    "ankle": "발목",
}
WEEKLY_FREQUENCY_TO_DAYS = {
    "once_twice": 2,
    "three_four": 4,
    "five_plus": 5,
}
GOAL_TO_EXERCISE = {
    "build_stamina": "jumping_jack",
    "posture_correction": "squat",
    "lower_body_strength": "squat",
    "build_habit": "knee_raise",
    "weight_management": "jumping_jack",
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

    async def generate_routine(self, request: RecommendationRequest) -> RecommendationResponse:
        if self._settings.mock_llm:
            return self._routine_fallback_response(request, "PC2 routine generation is disabled by MOCK_LLM.")

        try:
            async with httpx.AsyncClient(timeout=self._settings.pc2_timeout_seconds) as client:
                response = await client.post(
                    self._settings.pc2_routine_api_url,
                    json=self.build_pc2_routine_request_json(request),
                )
                response.raise_for_status()
            return self.pc2_routine_response_to_recommendation(request, response.json())
        except Exception:
            logger.exception("PC2 routine API call failed. Falling back to local basic routine.")
            return self._routine_fallback_response(request, "PC2 unavailable. Using a local basic routine.")

    async def get_routine_day(self, user_id: str, target_date: date) -> RoutineDayResponse:
        url = self._routine_day_url(user_id, target_date)
        params = None if "{target_date}" in self._settings.pc2_routine_day_api_url else {
            "target_date": target_date.isoformat()
        }
        async with httpx.AsyncClient(timeout=self._settings.pc2_timeout_seconds) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
        return self.pc2_routine_day_response_to_pc1(response.json())

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

    def build_pc2_routine_request_json(self, request: RecommendationRequest) -> dict:
        profile = request.profile
        self._validate_routine_profile(profile)
        payload: dict = {
            "user_id": request.user_id,
            "user_goal": request.pc2_user_goal or GOAL_LABELS[profile.goal],
            "exercise_experience": request.pc2_exercise_experience or EXPERIENCE_LABELS[profile.experience_level],
            "available_days_per_week": (
                request.pc2_available_days_per_week
                or WEEKLY_FREQUENCY_TO_DAYS[profile.weekly_frequency]
            ),
            "restricted_body_parts": (
                list(request.pc2_restricted_body_parts)
                if request.pc2_restricted_body_parts
                else [LIMITATION_LABELS[item] for item in profile.limitations]
            ),
            "purpose": request.purpose or "pre_exercise_routine",
        }
        if profile.name:
            payload["profile_name"] = profile.name
        if profile.weight_kg is not None:
            payload["weight_kg"] = profile.weight_kg
        if request.start_date is not None:
            payload["start_date"] = request.start_date.isoformat()
        return payload

    def pc2_routine_response_to_recommendation(
        self,
        request: RecommendationRequest,
        response_json: dict,
    ) -> RecommendationResponse:
        difficulty = self._difficulty_from_profile(request)
        items: list[RoutineItemPayload] = []
        pc3_payload = response_json.get("pc3_payload") if isinstance(response_json.get("pc3_payload"), dict) else {}
        weekly_routine = self._normalize_weekly_routine(
            response_json.get("weekly_routine") or pc3_payload.get("weekly_routine")
        )
        for day in weekly_routine:
            for exercise in day.exercises:
                reps = exercise.reps or self._duration_to_reps(exercise.duration_sec)
                rest_sec = exercise.rest_sec
                items.append(
                    RoutineItemPayload(
                        exercise_type=exercise.exercise,
                        title=f"{day.day_label or 'Routine'} - {exercise.exercise.replace('_', ' ')}",
                        reps=max(1, int(reps or 8)),
                        rest_sec=max(0, int(rest_sec if rest_sec is not None else 60)),
                        focus=exercise.focus or day.focus or "controlled posture",
                        summary=exercise.reason or day.focus or response_json.get("weekly_focus") or "",
                        sets=exercise.sets,
                        duration_sec=exercise.duration_sec,
                        reason=exercise.reason,
                        how_to=exercise.how_to,
                        tips=exercise.tips,
                    )
                )
                if len(items) >= 3:
                    break
            if len(items) >= 3:
                break

        if not items:
            return self._routine_fallback_response(request, "PC2 returned no usable exercise plan.")

        cautions = [str(item) for item in response_json.get("cautions", []) if item]
        weekly_focus = str(response_json.get("weekly_focus") or "Start with controlled posture.")
        summary = str(response_json.get("summary") or "AI routine generated from your profile.")
        return RecommendationResponse(
            source="ai",
            difficulty=difficulty,
            title="AI routine from PC2",
            description=summary,
            reason_lines=[weekly_focus, *cautions],
            estimated_minutes=self._estimate_minutes(items),
            start_exercise_type=items[0].exercise_type,
            items=items,
            routine_id=pc3_payload.get("routine_id") or response_json.get("routine_id"),
            start_date=pc3_payload.get("start_date") or response_json.get("start_date"),
            scheduled_dates=list(pc3_payload.get("scheduled_dates") or response_json.get("scheduled_dates") or []),
            weekly_routine=weekly_routine,
        )

    def pc2_routine_day_response_to_pc1(self, response_json: dict) -> RoutineDayResponse:
        exercises = self._normalize_weekly_exercises(response_json.get("exercises"))
        return RoutineDayResponse(
            routine_id=str(response_json.get("routine_id") or ""),
            user_id=str(response_json.get("user_id") or ""),
            scheduled_date=str(response_json.get("scheduled_date") or ""),
            day_index=int(response_json.get("day_index") or 1),
            day_label=str(response_json.get("day_label") or "Day 1"),
            focus=str(response_json.get("focus") or "controlled posture"),
            exercises=exercises,
            summary=str(response_json.get("summary") or ""),
            weekly_focus=str(response_json.get("weekly_focus") or ""),
            message=str(response_json.get("message") or ""),
            created_at=response_json.get("created_at"),
        )

    def _dump_pc2_exercise(self, exercise) -> dict:
        raw = exercise.model_dump(mode="json", exclude_none=True)
        return {key: value for key, value in raw.items() if key in PC2_EXERCISE_FIELDS}

    def _dump_pc2_baseline_diff(self, exercise_diff: dict) -> dict:
        return {
            key: value
            for key, value in exercise_diff.items()
            if key in PC2_BASELINE_DIFF_FIELDS and value is not None
        }

    def _routine_day_url(self, user_id: str, target_date: date) -> str:
        return self._settings.pc2_routine_day_api_url.format(
            user_id=quote(user_id, safe=""),
            target_date=target_date.isoformat(),
        )

    def _normalize_weekly_routine(self, value) -> list[WeeklyRoutineDayPayload]:
        if not isinstance(value, list):
            return []

        days: list[WeeklyRoutineDayPayload] = []
        for index, day in enumerate(value, start=1):
            if not isinstance(day, dict):
                continue
            exercises = self._normalize_weekly_exercises(day.get("exercises"))
            if not exercises:
                continue
            days.append(
                WeeklyRoutineDayPayload(
                    day_index=int(day.get("day_index") or index),
                    day_label=str(day.get("day_label") or f"Day {index}"),
                    focus=str(day.get("focus") or "controlled posture"),
                    exercises=exercises,
                )
            )
        return days

    def _normalize_weekly_exercises(self, value) -> list[WeeklyRoutineExercisePayload]:
        if not isinstance(value, list):
            return []

        exercises: list[WeeklyRoutineExercisePayload] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            exercise_type = self._normalize_routine_exercise(item.get("exercise"))
            if exercise_type is None:
                continue
            exercises.append(
                WeeklyRoutineExercisePayload(
                    exercise=exercise_type,
                    sets=self._optional_int(item.get("sets")),
                    reps=self._optional_int(item.get("reps")),
                    duration_sec=self._optional_int(item.get("duration_sec")),
                    rest_sec=self._optional_int(item.get("rest_sec")),
                    focus=str(item.get("focus") or "controlled posture"),
                    reason=str(item.get("reason") or ""),
                    how_to=str(item.get("how_to") or ""),
                    tips=str(item.get("tips") or ""),
                )
            )
        return exercises

    def _validate_routine_profile(self, profile) -> None:
        missing = []
        if profile.goal is None:
            missing.append("profile.goal")
        if profile.experience_level is None:
            missing.append("profile.experience_level")
        if profile.weekly_frequency is None:
            missing.append("profile.weekly_frequency")
        if missing:
            raise ValueError("Missing routine profile fields: " + ", ".join(missing))

    def _difficulty_from_profile(self, request: RecommendationRequest) -> str:
        profile = request.profile
        if profile.experience_level == "consistent" or profile.weekly_frequency == "five_plus":
            return "challenge"
        if profile.experience_level == "beginner" or profile.weekly_frequency == "once_twice":
            return "easy"
        return "normal"

    def _routine_fallback_response(self, request: RecommendationRequest, reason: str) -> RecommendationResponse:
        difficulty = self._difficulty_from_profile(request)
        primary = GOAL_TO_EXERCISE.get(request.profile.goal or "", "squat")
        sequence = [primary, "knee_raise", "pushup"]
        items = [
            RoutineItemPayload(
                exercise_type=exercise_type,
                title=f"Basic routine {index + 1}",
                reps=max(6, 12 - index * 2),
                rest_sec=60,
                focus="controlled posture",
                summary=reason if index == 0 else "Local fallback plan.",
            )
            for index, exercise_type in enumerate(sequence)
        ]
        return RecommendationResponse(
            source="basic",
            difficulty=difficulty,
            title="Basic fallback routine",
            description="PC3 returned a local routine because PC2 routine planning was unavailable.",
            reason_lines=[reason],
            estimated_minutes=self._estimate_minutes(items),
            start_exercise_type=items[0].exercise_type,
            items=items,
        )

    def _normalize_routine_exercise(self, value) -> str | None:
        raw_label = str(value or "").strip().lower()
        if raw_label in ROUTINE_EXERCISE_ALIASES:
            return ROUTINE_EXERCISE_ALIASES[raw_label]
        raw = raw_label.replace("-", "_").replace(" ", "_")
        if raw in ROUTINE_EXERCISE_ALIASES:
            return ROUTINE_EXERCISE_ALIASES[raw]
        for exercise_type in SUPPORTED_ROUTINE_EXERCISES:
            if exercise_type in raw:
                return exercise_type
        return None

    def _duration_to_reps(self, duration_sec) -> int | None:
        if duration_sec is None:
            return None
        return max(1, int(float(duration_sec) / 3))

    def _optional_int(self, value) -> int | None:
        if value is None:
            return None
        return int(value)

    def _estimate_minutes(self, items: list[RoutineItemPayload]) -> int:
        total_reps = sum(item.reps for item in items)
        total_rest = sum(item.rest_sec for item in items)
        return max(8, round((total_reps * 3 + total_rest) / 60))

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
