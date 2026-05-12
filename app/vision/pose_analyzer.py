from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any

from app.schemas.feature import ExerciseFeature
from app.utils.json_loader import load_json_file

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None


logger = logging.getLogger(__name__)


class PoseAnalyzer:
    _LANDMARK_INDEX = {
        "LEFT_SHOULDER": 11,
        "RIGHT_SHOULDER": 12,
        "LEFT_HIP": 23,
        "RIGHT_HIP": 24,
        "LEFT_KNEE": 25,
        "RIGHT_KNEE": 26,
        "LEFT_ANKLE": 27,
        "RIGHT_ANKLE": 28,
    }
    _DEFAULT_THRESHOLDS: dict[str, Any] = {
        "squat": {
            "down_knee_angle": 95,
            "up_knee_angle": 160,
            "min_landmark_visibility": 0.5,
            "stability_warning_threshold": 0.65,
            "posture_error_thresholds": {
                "knees_caving_in": 0.12,
                "back_leaning_forward_degrees": 25,
            },
        }
    }

    def __init__(
        self,
        pose_model_path: str | Path | None = None,
        exercise_thresholds_path: str | Path | None = None,
        exercise_rules_path: str | Path | None = None,
        use_mediapipe_tasks: bool = False,
    ) -> None:
        self._thresholds = load_json_file(exercise_thresholds_path, self._DEFAULT_THRESHOLDS)
        self._exercise_rules = load_json_file(exercise_rules_path, {})
        self._backend = "fallback"
        self._landmarker = None
        self._mp = None

        if not use_mediapipe_tasks:
            logger.info("USE_MEDIAPIPE_TASKS=false. Pose analysis will use fallback.")
            return
        if cv2 is None:
            logger.warning("OpenCV is unavailable. Pose analysis will use fallback.")
            return
        if pose_model_path is None:
            logger.warning("POSE_MODEL_PATH is not configured. Pose analysis will use fallback.")
            return

        self._try_initialize_tasks_pose(Path(pose_model_path))

    @property
    def backend(self) -> str:
        return self._backend

    @property
    def use_mediapipe(self) -> bool:
        return self._backend == "mediapipe_tasks" and self._landmarker is not None

    def _try_initialize_tasks_pose(self, pose_model_path: Path) -> bool:
        if not pose_model_path.exists():
            logger.warning("POSE_MODEL_PATH does not exist: %s. Pose fallback will be used.", pose_model_path)
            return False
        try:
            import mediapipe as mp
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision

            base_options = python.BaseOptions(model_asset_path=str(pose_model_path))
            options = vision.PoseLandmarkerOptions(
                base_options=base_options,
                running_mode=vision.RunningMode.IMAGE,
                num_poses=1,
                min_pose_detection_confidence=self._min_landmark_visibility(),
                min_pose_presence_confidence=self._min_landmark_visibility(),
                min_tracking_confidence=self._min_landmark_visibility(),
                output_segmentation_masks=False,
            )
            self._landmarker = vision.PoseLandmarker.create_from_options(options)
            self._mp = mp
            self._backend = "mediapipe_tasks"
            logger.info("MediaPipe Tasks PoseLandmarker initialized: %s", pose_model_path)
            return True
        except Exception:
            logger.exception("Failed to initialize MediaPipe Tasks PoseLandmarker. Falling back.")
            self._landmarker = None
            self._mp = None
            self._backend = "fallback"
            return False

    def analyze(
        self,
        frame,
        previous: ExerciseFeature | None = None,
    ) -> tuple[ExerciseFeature, str]:
        previous = previous or ExerciseFeature()
        landmarks = self._detect_landmarks(frame)
        if not landmarks:
            return self._idle_feature(
                previous,
                posture_errors=["no_person"],
                feedback="전신이 화면에 보이도록 조금 뒤로 이동해 주세요.",
            )

        if not self._landmarks_are_confident(landmarks):
            return self._idle_feature(
                previous,
                posture_errors=["low_confidence"],
                feedback="전신이 화면에 선명하게 보이도록 자세와 조명을 조정해 주세요.",
            )

        try:
            left_angle = self._knee_angle(landmarks, "LEFT")
            right_angle = self._knee_angle(landmarks, "RIGHT")
            average_angle = (left_angle + right_angle) / 2
            state = self._state_from_angle(average_angle)
            count = previous.count
            if previous.state == "down" and state == "up":
                count += 1

            posture_errors: list[str] = []
            if self._knees_caving_in(landmarks):
                posture_errors.append("knees_caving_in")
            trunk_angle = self._trunk_angle(landmarks)
            if trunk_angle > self._back_lean_threshold():
                posture_errors.append("back_leaning_forward")

            stability_score = self._stability_score(
                left_angle,
                right_angle,
                trunk_angle,
                posture_errors,
            )
            feedback = self._feedback(state, posture_errors, stability_score)
            return (
                ExerciseFeature(
                    type="squat",
                    count=count,
                    state=state,
                    stability_score=stability_score,
                    posture_errors=posture_errors,
                ),
                feedback,
            )
        except Exception:
            logger.exception("Pose analysis failed during landmark processing. Returning fallback.")
            return self._idle_feature(
                previous,
                posture_errors=["analysis_failed"],
                feedback="자세를 안정적으로 인식하지 못했습니다.",
            )

    def _idle_feature(
        self,
        previous: ExerciseFeature,
        posture_errors: list[str],
        feedback: str,
    ) -> tuple[ExerciseFeature, str]:
        return (
            ExerciseFeature(
                type="squat",
                count=previous.count,
                state="idle",
                stability_score=previous.stability_score,
                posture_errors=posture_errors,
            ),
            feedback,
        )

    def _detect_landmarks(self, frame):
        if cv2 is None or self._landmarker is None or self._mp is None:
            return None
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb_frame)
            result = self._landmarker.detect(mp_image)
            if not result.pose_landmarks:
                return None
            return result.pose_landmarks[0]
        except Exception:
            logger.exception("MediaPipe pose inference failed. Returning fallback for this request.")
            self._backend = "fallback"
            self._landmarker = None
            self._mp = None
            return None

    def _landmark(self, landmarks, side: str, part: str):
        enum_name = f"{side}_{part}"
        return landmarks[self._LANDMARK_INDEX[enum_name]]

    def _landmarks_are_confident(self, landmarks) -> bool:
        for name in self._LANDMARK_INDEX:
            landmark = landmarks[self._LANDMARK_INDEX[name]]
            confidence_values = []
            visibility = getattr(landmark, "visibility", None)
            presence = getattr(landmark, "presence", None)
            if visibility is not None:
                confidence_values.append(float(visibility))
            if presence is not None:
                confidence_values.append(float(presence))
            if confidence_values and min(confidence_values) < self._min_landmark_visibility():
                return False
        return True

    def _knee_angle(self, landmarks, side: str) -> float:
        hip = self._landmark(landmarks, side, "HIP")
        knee = self._landmark(landmarks, side, "KNEE")
        ankle = self._landmark(landmarks, side, "ANKLE")
        return self._angle(hip, knee, ankle)

    def _angle(self, point_a, point_b, point_c) -> float:
        vector_a = (point_a.x - point_b.x, point_a.y - point_b.y)
        vector_c = (point_c.x - point_b.x, point_c.y - point_b.y)
        dot = vector_a[0] * vector_c[0] + vector_a[1] * vector_c[1]
        mag_a = math.sqrt(vector_a[0] ** 2 + vector_a[1] ** 2)
        mag_c = math.sqrt(vector_c[0] ** 2 + vector_c[1] ** 2)
        if mag_a == 0 or mag_c == 0:
            return 180.0
        cosine = max(-1.0, min(1.0, dot / (mag_a * mag_c)))
        return math.degrees(math.acos(cosine))

    def _state_from_angle(self, angle: float) -> str:
        state_thresholds = self._exercise_rules.get("exercises", {}).get("squat", {}).get(
            "state_thresholds", {}
        )
        squat = self._thresholds.get("squat", {})
        down_angle = float(
            state_thresholds.get("down_knee_angle", squat.get("down_knee_angle", 95))
        )
        up_angle = float(state_thresholds.get("up_knee_angle", squat.get("up_knee_angle", 160)))
        if angle <= down_angle:
            return "down"
        if angle >= up_angle:
            return "up"
        return "idle"

    def _knees_caving_in(self, landmarks) -> bool:
        left_knee = self._landmark(landmarks, "LEFT", "KNEE")
        right_knee = self._landmark(landmarks, "RIGHT", "KNEE")
        left_ankle = self._landmark(landmarks, "LEFT", "ANKLE")
        right_ankle = self._landmark(landmarks, "RIGHT", "ANKLE")
        knee_width = abs(right_knee.x - left_knee.x)
        ankle_width = abs(right_ankle.x - left_ankle.x)
        return ankle_width > 0.02 and (ankle_width - knee_width) > self._knees_caving_threshold()

    def _trunk_angle(self, landmarks) -> float:
        left_shoulder = self._landmark(landmarks, "LEFT", "SHOULDER")
        right_shoulder = self._landmark(landmarks, "RIGHT", "SHOULDER")
        left_hip = self._landmark(landmarks, "LEFT", "HIP")
        right_hip = self._landmark(landmarks, "RIGHT", "HIP")
        shoulder_mid_x = (left_shoulder.x + right_shoulder.x) / 2
        shoulder_mid_y = (left_shoulder.y + right_shoulder.y) / 2
        hip_mid_x = (left_hip.x + right_hip.x) / 2
        hip_mid_y = (left_hip.y + right_hip.y) / 2
        dx = shoulder_mid_x - hip_mid_x
        dy = shoulder_mid_y - hip_mid_y
        if dx == 0 and dy == 0:
            return 0.0
        return abs(math.degrees(math.atan2(abs(dx), abs(dy))))

    def _stability_score(
        self,
        left_angle: float,
        right_angle: float,
        trunk_angle: float,
        posture_errors: list[str],
    ) -> float:
        asymmetry_penalty = min(abs(left_angle - right_angle) / 120, 0.3)
        trunk_penalty = min(trunk_angle / 120, 0.25)
        error_penalty = min(len(posture_errors) * 0.18, 0.36)
        return round(max(0.0, min(1.0, 0.95 - asymmetry_penalty - trunk_penalty - error_penalty)), 3)

    def _feedback(self, state: str, posture_errors: list[str], stability_score: float) -> str:
        if "knees_caving_in" in posture_errors:
            return "무릎이 안쪽으로 모이지 않게 해주세요."
        if "back_leaning_forward" in posture_errors:
            return "상체를 조금 더 안정적으로 유지해 주세요."
        if stability_score < self._stability_warning_threshold():
            return "좋습니다. 속도를 줄이고 현재 자세를 안정적으로 유지해 주세요."
        if state == "down":
            return "좋습니다. 천천히 올라오세요."
        if state == "up":
            return "좋습니다. 현재 자세를 유지해 주세요."
        return "전신이 화면에 보이도록 조금 뒤로 이동해 주세요."

    def _squat_thresholds(self) -> dict[str, Any]:
        return self._thresholds.get("squat", {})

    def _posture_thresholds(self) -> dict[str, Any]:
        return self._squat_thresholds().get("posture_error_thresholds", {})

    def _min_landmark_visibility(self) -> float:
        squat = self._squat_thresholds()
        return float(squat.get("min_landmark_visibility", squat.get("min_landmark_confidence", 0.5)))

    def _stability_warning_threshold(self) -> float:
        return float(self._squat_thresholds().get("stability_warning_threshold", 0.65))

    def _knees_caving_threshold(self) -> float:
        return float(
            self._posture_thresholds().get(
                "knees_caving_in",
                self._squat_thresholds().get("knees_caving_in", 0.12),
            )
        )

    def _back_lean_threshold(self) -> float:
        return float(self._posture_thresholds().get("back_leaning_forward_degrees", 25))

    def extract_body_proportions(self, frame) -> dict[str, float] | None:
        landmarks = self._detect_landmarks(frame)
        if landmarks is None:
            return None
        if not self._landmarks_are_confident(landmarks):
            return None

        try:
            left_shoulder = self._landmark(landmarks, "LEFT", "SHOULDER")
            right_shoulder = self._landmark(landmarks, "RIGHT", "SHOULDER")
            left_hip = self._landmark(landmarks, "LEFT", "HIP")
            right_hip = self._landmark(landmarks, "RIGHT", "HIP")
            left_ankle = self._landmark(landmarks, "LEFT", "ANKLE")
            right_ankle = self._landmark(landmarks, "RIGHT", "ANKLE")

            shoulder_width = round(abs(right_shoulder.x - left_shoulder.x), 4)
            hip_width = round(abs(right_hip.x - left_hip.x), 4)
            shoulder_mid_y = (left_shoulder.y + right_shoulder.y) / 2
            ankle_mid_y = (left_ankle.y + right_ankle.y) / 2
            body_height = round(abs(ankle_mid_y - shoulder_mid_y), 4)
            return {
                "shoulder_width": shoulder_width,
                "hip_width": hip_width,
                "body_height": body_height,
            }
        except Exception:
            logger.exception("Failed to extract body proportions from landmarks.")
            return None
