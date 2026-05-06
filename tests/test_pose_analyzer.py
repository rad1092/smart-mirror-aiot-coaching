from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.schemas.feature import ExerciseFeature
from app.vision.pose_analyzer import PoseAnalyzer


@dataclass
class Landmark:
    x: float
    y: float
    visibility: float = 1.0
    presence: float = 1.0


def _blank_frame():
    return np.zeros((240, 240, 3), dtype=np.uint8)


def _landmarks_for_state(state: str) -> list[Landmark]:
    landmarks = [Landmark(0.5, 0.5) for _ in range(33)]
    landmarks[11] = Landmark(0.42, 0.25)  # left shoulder
    landmarks[12] = Landmark(0.58, 0.25)  # right shoulder
    landmarks[23] = Landmark(0.42, 0.50)  # left hip
    landmarks[24] = Landmark(0.58, 0.50)  # right hip
    landmarks[25] = Landmark(0.42, 0.70)  # left knee
    landmarks[26] = Landmark(0.58, 0.70)  # right knee
    if state == "down":
        landmarks[27] = Landmark(0.58, 0.70)  # left ankle, acute knee angle
        landmarks[28] = Landmark(0.42, 0.70)  # right ankle
    else:
        landmarks[27] = Landmark(0.42, 0.90)  # left ankle, straight leg
        landmarks[28] = Landmark(0.58, 0.90)  # right ankle
    return landmarks


def test_pose_analyzer_uses_fallback_when_tasks_disabled():
    analyzer = PoseAnalyzer(use_mediapipe_tasks=False)

    feature, feedback = analyzer.analyze(_blank_frame())

    assert analyzer.backend == "fallback"
    assert feature.state == "idle"
    assert "전신이 화면에 보이도록" in feedback
    assert _has_no_mojibake(feedback)


def test_pose_analyzer_falls_back_when_tasks_enabled_but_model_missing(tmp_path):
    analyzer = PoseAnalyzer(
        pose_model_path=tmp_path / "missing.task",
        use_mediapipe_tasks=True,
    )

    assert analyzer.backend == "fallback"


def test_pose_analyzer_counts_down_to_up_transition(monkeypatch):
    analyzer = PoseAnalyzer(
        exercise_thresholds_path=Path("config/exercise_thresholds.json"),
        exercise_rules_path=Path("data/exercise_rules.json"),
        use_mediapipe_tasks=False,
    )
    monkeypatch.setattr(analyzer, "_detect_landmarks", lambda frame: _landmarks_for_state("down"))
    down_feature, down_feedback = analyzer.analyze(_blank_frame(), ExerciseFeature(count=0, state="up"))
    assert down_feature.state == "down"
    assert down_feature.count == 0
    assert "좋습니다" in down_feedback
    assert _has_no_mojibake(down_feedback)

    monkeypatch.setattr(analyzer, "_detect_landmarks", lambda frame: _landmarks_for_state("up"))
    up_feature, up_feedback = analyzer.analyze(_blank_frame(), down_feature)

    assert up_feature.state == "up"
    assert up_feature.count == 1
    assert "좋습니다" in up_feedback
    assert _has_no_mojibake(up_feedback)


def test_pose_analyzer_feedback_for_posture_errors_has_no_mojibake():
    analyzer = PoseAnalyzer(use_mediapipe_tasks=False)

    knees_feedback = analyzer._feedback("idle", ["knees_caving_in"], 0.8)
    back_feedback = analyzer._feedback("idle", ["back_leaning_forward"], 0.8)

    assert knees_feedback == "무릎이 안쪽으로 모이지 않게 해주세요."
    assert back_feedback == "상체를 조금 더 안정적으로 유지해 주세요."
    assert _has_no_mojibake(knees_feedback)
    assert _has_no_mojibake(back_feedback)


def _has_no_mojibake(text: str) -> bool:
    return not any(marker in text for marker in ["�", "占", "醫", "臾", "?꾩", "덈떎"])
