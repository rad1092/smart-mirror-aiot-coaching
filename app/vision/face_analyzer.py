from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.schemas.feature import FaceFeature
from app.utils.json_loader import load_json_file
from app.vision.frame_utils import clamp01, normalized_region

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None


logger = logging.getLogger(__name__)


class FaceAnalyzer:
    _DEFAULT_CONFIG: dict[str, Any] = {
        "fallback_face_region": {
            "x_min_ratio": 0.30,
            "x_max_ratio": 0.70,
            "y_min_ratio": 0.15,
            "y_max_ratio": 0.55,
        },
        "fallback_beard_region": {
            "x_min_ratio": 0.35,
            "x_max_ratio": 0.65,
            "y_min_ratio": 0.45,
            "y_max_ratio": 0.65,
        },
        "beard_shadow_dark_threshold": 0.35,
        "fallback_feature": {
            "brightness": 0.5,
            "redness": 0.33,
            "beard_shadow": 0.0,
        },
    }

    def __init__(self, thresholds_path: str | Path | None = None) -> None:
        self._config = load_json_file(thresholds_path, self._DEFAULT_CONFIG)

    def analyze(self, frame) -> FaceFeature:
        if np is None:
            logger.warning("numpy is unavailable. Returning neutral face feature fallback.")
            return self._fallback_feature()

        face_region = self._region(frame, "fallback_face_region")
        lower_face_region = self._region(frame, "fallback_beard_region")
        try:
            brightness = self._brightness(face_region)
            redness = self._redness(face_region)
            beard_shadow = self._beard_shadow(lower_face_region)
            return FaceFeature(
                brightness=round(clamp01(brightness), 3),
                redness=round(clamp01(redness), 3),
                beard_shadow=round(clamp01(beard_shadow), 3),
            )
        except Exception:
            logger.exception("Face analysis failed. Returning neutral feature fallback.")
            return self._fallback_feature()

    def _region(self, frame, key: str):
        region = self._config.get(key, self._DEFAULT_CONFIG[key])
        default = self._DEFAULT_CONFIG[key]
        return normalized_region(
            frame,
            float(region.get("x_min_ratio", default["x_min_ratio"])),
            float(region.get("y_min_ratio", default["y_min_ratio"])),
            float(region.get("x_max_ratio", default["x_max_ratio"])),
            float(region.get("y_max_ratio", default["y_max_ratio"])),
        )

    def _fallback_feature(self) -> FaceFeature:
        fallback = self._config.get("fallback_feature", self._DEFAULT_CONFIG["fallback_feature"])
        return FaceFeature(
            brightness=round(clamp01(float(fallback.get("brightness", 0.5))), 3),
            redness=round(clamp01(float(fallback.get("redness", 0.33))), 3),
            beard_shadow=round(clamp01(float(fallback.get("beard_shadow", 0.0))), 3),
        )

    def _to_rgb_float(self, region):
        return region[..., ::-1].astype("float32")

    def _brightness(self, region) -> float:
        rgb = self._to_rgb_float(region)
        gray = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
        return float(gray.mean() / 255.0)

    def _redness(self, region) -> float:
        rgb = self._to_rgb_float(region)
        total = rgb.sum(axis=2) + 1e-6
        red_ratio = rgb[..., 0] / total
        return float(red_ratio.mean())

    def _beard_shadow(self, region) -> float:
        rgb = self._to_rgb_float(region)
        gray = (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]) / 255.0
        threshold = float(self._config.get("beard_shadow_dark_threshold", 0.35))
        return float((gray < threshold).mean())
