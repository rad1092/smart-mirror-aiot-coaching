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
EXERCISE_LABELS_KO = {
    "squat": "스쿼트",
    "jumping_jack": "점핑잭",
    "knee_raise": "무릎 들어올리기",
    "lunge": "런지",
    "pushup": "푸시업",
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
            return self._routine_fallback_response(request, "MOCK_LLM 설정으로 PC2 루틴 호출을 건너뛰고 PC3 기본 루틴을 표시합니다.")

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
            return self._routine_fallback_response(request, "PC2 응답을 받지 못해 PC3 기본 루틴을 표시합니다.")

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
        message = "측정 품질이 낮아 운동 후 AI 코칭을 건너뛰었습니다. 전신이 잘 보이게 다시 촬영해 주세요."
        return CoachingResponse(
            summary=(
                f"PC3가 {count}회를 측정했지만 영상 품질이 낮아 PC2 코칭에 보내지 않았습니다. "
                f"측정 신뢰도: {confidence:.2f}."
            ),
            priority="측정 품질",
            routine=[
                RoutineItem(
                    title="다시 촬영",
                    description="처음 잡은 사용자가 화면 중앙에 서고, 머리부터 발끝까지 보이며, 다른 사람이 들어오지 않게 해 주세요.",
                )
            ],
            exercise_plan=[
                ExercisePlanItem(
                    exercise=exercise_type,
                    sets=1,
                    reps=max(4, count if count else 6),
                    rest_sec=60,
                    focus="카메라 프레이밍",
                    reason="자세 측정 품질이 기준보다 낮아 PC3가 PC2 호출을 건너뛰었습니다.",
                )
            ],
            mirror_message=message,
            warnings=["자세 측정 품질이 낮아 PC2 운동 후 피드백을 요청하지 않았습니다."],
            pc2_payload=PC2Payload(
                message=message,
                display_lines=[
                    "머리부터 발끝까지 화면 안에 들어오게 해 주세요.",
                    "처음 잡은 사용자가 계속 화면 중앙에 있어야 합니다.",
                    "다시 운동을 측정한 뒤 코칭을 요청해 주세요.",
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
                        title=f"{day.day_label or f'{day.day_index}일차'} - {self._exercise_label(exercise.exercise)}",
                        reps=max(1, int(reps or 8)),
                        rest_sec=max(0, int(rest_sec if rest_sec is not None else 60)),
                        focus=exercise.focus or day.focus or "자세 안정",
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
            return self._routine_fallback_response(request, "PC2 응답에서 사용할 수 있는 운동 계획을 찾지 못해 PC3 기본 루틴을 표시합니다.")

        cautions = [str(item) for item in response_json.get("cautions", []) if item]
        weekly_focus = str(response_json.get("weekly_focus") or "자세를 안정적으로 유지하는 것부터 시작하세요.")
        summary = str(response_json.get("summary") or "프로필을 기준으로 만든 운동 루틴입니다.")
        return RecommendationResponse(
            source="ai",
            difficulty=difficulty,
            title="PC2 추천 루틴",
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
            day_label=str(response_json.get("day_label") or "1일차"),
            focus=str(response_json.get("focus") or "자세 안정"),
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
                    day_label=str(day.get("day_label") or f"{index}일차"),
                    focus=str(day.get("focus") or "자세 안정"),
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
                    focus=str(item.get("focus") or "자세 안정"),
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
                title=f"기본 루틴 {index + 1} - {self._exercise_label(exercise_type)}",
                reps=max(6, 12 - index * 2),
                rest_sec=60,
                focus="자세 안정",
                summary=reason if index == 0 else "PC3 기본 루틴입니다.",
            )
            for index, exercise_type in enumerate(sequence)
        ]
        return RecommendationResponse(
            source="basic",
            difficulty=difficulty,
            title="PC3 기본 루틴",
            description="PC2 루틴 응답을 받지 못해 PC3가 기본 루틴을 표시합니다.",
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

    def _exercise_label(self, exercise_type: str) -> str:
        return EXERCISE_LABELS_KO.get(exercise_type, exercise_type.replace("_", " "))

    def _mock_response(self, payload: FeaturePayload) -> CoachingResponse:
        exercise = payload.features.exercise
        count = exercise.count if exercise else 0
        exercise_type = exercise.type if exercise else "squat"
        mirror_message = "속도보다 자세를 우선하면서 움직임을 안정적으로 이어가 주세요."
        return CoachingResponse(
            summary=f"{count}회를 완료했습니다. 이 피드백은 자세 안정성과 기준 자세 차이를 바탕으로 만든 PC3 기본 코칭입니다.",
            priority="자세 안정",
            routine=[
                RoutineItem(
                    title="정렬 확인",
                    description="무릎 방향을 발끝과 맞추고 다음 세트는 조금 더 천천히 진행해 주세요.",
                )
            ],
            exercise_plan=[
                ExercisePlanItem(
                    exercise=exercise_type,
                    sets=3,
                    reps=max(4, count if count else 6),
                    rest_sec=60,
                    focus="자세 안정",
                    reason="PC3 기본 코칭이 활성화되어 안전한 기본 계획을 반환합니다.",
                )
            ],
            mirror_message=mirror_message,
            warnings=["통증이 느껴지면 즉시 운동을 멈추세요."],
            pc2_payload=PC2Payload(
                message=mirror_message,
                display_lines=["자세를 먼저 안정시키기", "일정한 속도로 반복하기"],
            ),
        )
