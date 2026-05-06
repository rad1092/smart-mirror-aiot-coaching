from __future__ import annotations

from app.baseline.baseline_service import BaselineService
from app.baseline.baseline_store import BaselineStore
from app.schemas.feature import ExerciseFeature, FaceFeature


def test_baseline_service_calculates_exercise_diff(baseline_path):
    service = BaselineService(BaselineStore(baseline_path))
    feature = ExerciseFeature(count=12, state="up", stability_score=0.74)

    diff = service.calculate_exercise_diff("default", feature)

    assert diff["count_change"] == -3
    assert diff["stability_change"] == -0.08


def test_baseline_service_supports_new_squat_baseline_structure(baseline_path):
    service = BaselineService(BaselineStore(baseline_path))
    feature = ExerciseFeature(count=18, state="up", stability_score=0.9)

    diff = service.calculate_exercise_diff("default", feature)

    assert diff["count_change"] == 3
    assert diff["stability_change"] == 0.08


def test_baseline_service_calculates_face_diff(baseline_path):
    service = BaselineService(BaselineStore(baseline_path))
    feature = FaceFeature(brightness=0.62, redness=0.18, beard_shadow=0.44)

    diff = service.calculate_face_diff("default", feature)

    assert diff["brightness_diff"] == -0.12
    assert diff["redness_diff"] == 0.05
    assert diff["beard_shadow_diff"] == 0.16


def test_baseline_service_uses_user_specific_sqlite_baseline(tmp_path, baseline_path):
    service = BaselineService(BaselineStore(baseline_path, tmp_path / "baselines.sqlite3"))
    service.upsert_baseline(
        "user_1",
        {
            "exercise": {
                "squat": {
                    "avg_count": 3,
                    "avg_stability_score": 0.5,
                }
            },
            "face": {
                "brightness": 0.5,
                "redness": 0.2,
                "beard_shadow": 0.4,
            },
        },
    )

    exercise_diff = service.calculate_exercise_diff(
        "user_1",
        ExerciseFeature(count=5, stability_score=0.7),
    )
    face_diff = service.calculate_face_diff(
        "user_1",
        FaceFeature(brightness=0.6, redness=0.1, beard_shadow=0.45),
    )

    assert service.get_baseline_source("user_1") == "user"
    assert service.get_baseline_source("unknown_user") == "default"
    assert exercise_diff == {"count_change": 2, "stability_change": 0.2}
    assert face_diff == {
        "brightness_diff": 0.1,
        "redness_diff": -0.1,
        "beard_shadow_diff": 0.05,
    }
