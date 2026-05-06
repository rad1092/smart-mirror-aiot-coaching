from __future__ import annotations

from typing import Any

from app.baseline.baseline_store import BaselineStore
from app.schemas.feature import ExerciseFeature, FaceFeature, FeatureSet, OutfitFeature


class BaselineService:
    def __init__(self, baseline_store: BaselineStore) -> None:
        self._baseline_store = baseline_store

    def get_baseline(self, user_id: str) -> dict[str, Any]:
        return self._baseline_store.get_baseline(user_id)

    def get_baseline_source(self, user_id: str) -> str:
        return self._baseline_store.get_source(user_id)

    def upsert_baseline(self, user_id: str, baseline_updates: dict[str, Any]) -> dict[str, Any]:
        return self._baseline_store.upsert_baseline(user_id, baseline_updates)

    def calculate_exercise_diff(
        self, user_id: str, exercise: ExerciseFeature
    ) -> dict[str, float | int]:
        baseline = self.get_baseline(user_id).get("exercise", {})
        squat_baseline = baseline.get("squat", {})
        avg_count = squat_baseline.get("avg_count", baseline.get("squat_avg_count", 0))
        avg_stability = squat_baseline.get(
            "avg_stability_score",
            baseline.get("avg_stability_score", 0.0),
        )
        return {
            "count_change": exercise.count - int(avg_count),
            "stability_change": round(
                exercise.stability_score - float(avg_stability),
                3,
            ),
        }

    def calculate_face_diff(self, user_id: str, face: FaceFeature) -> dict[str, float]:
        baseline = self.get_baseline(user_id).get("face", {})
        return {
            "brightness_diff": round(
                face.brightness - float(baseline.get("brightness", 0.0)), 3
            ),
            "redness_diff": round(face.redness - float(baseline.get("redness", 0.0)), 3),
            "beard_shadow_diff": round(
                face.beard_shadow - float(baseline.get("beard_shadow", 0.0)), 3
            ),
        }

    def calculate_outfit_diff(self, user_id: str, outfit: OutfitFeature) -> dict[str, Any]:
        baseline = self.get_baseline(user_id).get("outfit", {})
        preferred_tones = set(baseline.get("preferred_tones", []))
        preferred_colors = set(baseline.get("preferred_colors", []))
        current_names = {outfit.top_color.name, outfit.bottom_color.name, outfit.tone}
        return {
            "preferred_tone_match": bool(preferred_tones.intersection(current_names)),
            "preferred_color_match": bool(preferred_colors.intersection(current_names)),
        }

    def calculate_diff(self, user_id: str, features: FeatureSet) -> dict[str, Any]:
        diff: dict[str, Any] = {}
        if features.exercise is not None:
            diff["exercise"] = self.calculate_exercise_diff(user_id, features.exercise)
        if features.face is not None:
            diff["face"] = self.calculate_face_diff(user_id, features.face)
        if features.outfit is not None:
            diff["outfit"] = self.calculate_outfit_diff(user_id, features.outfit)
        return diff
