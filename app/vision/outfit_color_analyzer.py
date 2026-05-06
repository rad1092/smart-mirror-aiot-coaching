from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from app.schemas.feature import ColorInfo, OutfitFeature
from app.utils.json_loader import load_json_file
from app.vision.frame_utils import clamp01, normalized_region

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None


class OutfitColorAnalyzer:
    _DEFAULT_THRESHOLDS: dict[str, Any] = {
        "regions": {
            "top": {
                "x_min_ratio": 0.30,
                "x_max_ratio": 0.70,
                "y_min_ratio": 0.35,
                "y_max_ratio": 0.55,
            },
            "bottom": {
                "x_min_ratio": 0.30,
                "x_max_ratio": 0.70,
                "y_min_ratio": 0.55,
                "y_max_ratio": 0.85,
            },
        },
        "tone": {
            "dark_luminance_threshold": 0.35,
            "bright_luminance_threshold": 0.70,
        },
    }
    _DEFAULT_COLOR_RULES: dict[str, Any] = {
        "colors": [
            {"name": "black", "rgb": [20, 20, 20]},
            {"name": "white", "rgb": [240, 240, 240]},
            {"name": "gray", "rgb": [130, 130, 130]},
            {"name": "navy", "rgb": [30, 45, 90]},
            {"name": "blue", "rgb": [50, 100, 200]},
            {"name": "brown", "rgb": [120, 80, 50]},
            {"name": "beige", "rgb": [210, 190, 150]},
            {"name": "red", "rgb": [190, 50, 50]},
            {"name": "green", "rgb": [60, 140, 80]},
        ]
    }

    def __init__(
        self,
        thresholds_path: str | Path | None = None,
        color_rules_path: str | Path | None = None,
    ) -> None:
        self._thresholds = load_json_file(thresholds_path, self._DEFAULT_THRESHOLDS)
        self._color_rules = load_json_file(color_rules_path, self._DEFAULT_COLOR_RULES)

    def analyze(self, frame) -> OutfitFeature:
        if np is None:
            top = ColorInfo(name="gray", rgb=[128, 128, 128])
            bottom = ColorInfo(name="gray", rgb=[128, 128, 128])
            return OutfitFeature(
                top_color=top,
                bottom_color=bottom,
                contrast_score=0.0,
                tone="neutral",
            )

        top_region = self._region(frame, "top")
        bottom_region = self._region(frame, "bottom")
        top_rgb = self._representative_rgb(top_region)
        bottom_rgb = self._representative_rgb(bottom_region)
        top = ColorInfo(name=self._color_name(top_rgb), rgb=top_rgb)
        bottom = ColorInfo(name=self._color_name(bottom_rgb), rgb=bottom_rgb)
        return OutfitFeature(
            top_color=top,
            bottom_color=bottom,
            contrast_score=self._contrast_score(top_rgb, bottom_rgb),
            tone=self._tone(top_rgb, bottom_rgb),
        )

    def _region(self, frame, name: str):
        region = self._thresholds.get("regions", {}).get(
            name,
            self._DEFAULT_THRESHOLDS["regions"][name],
        )
        default = self._DEFAULT_THRESHOLDS["regions"][name]
        return normalized_region(
            frame,
            float(region.get("x_min_ratio", default["x_min_ratio"])),
            float(region.get("y_min_ratio", default["y_min_ratio"])),
            float(region.get("x_max_ratio", default["x_max_ratio"])),
            float(region.get("y_max_ratio", default["y_max_ratio"])),
        )

    def _representative_rgb(self, region) -> list[int]:
        if region.size == 0:
            return [128, 128, 128]
        rgb = region[..., ::-1].reshape(-1, 3)
        median = np.median(rgb, axis=0)
        return [int(max(0, min(255, value))) for value in median]

    def _color_name(self, rgb: list[int]) -> str:
        nearest = self._nearest_anchor_color(rgb)
        if nearest is not None:
            return nearest
        return self._fallback_color_name(rgb)

    def _nearest_anchor_color(self, rgb: list[int]) -> str | None:
        colors = self._color_rules.get("colors", [])
        if not isinstance(colors, list) or not colors:
            return None
        best_name = None
        best_distance = float("inf")
        for color in colors:
            try:
                name = str(color["name"])
                anchor = [int(value) for value in color["rgb"]]
            except (KeyError, TypeError, ValueError):
                continue
            distance = sum((a - b) ** 2 for a, b in zip(rgb, anchor))
            if distance < best_distance:
                best_name = name
                best_distance = distance
        return best_name

    def _fallback_color_name(self, rgb: list[int]) -> str:
        red, green, blue = rgb
        max_value = max(rgb)
        min_value = min(rgb)
        if max_value < 45:
            return "black"
        if min_value > 220:
            return "white"
        if max_value - min_value < 25:
            return "gray"
        if blue >= red and blue >= green:
            return "navy" if max_value < 110 else "blue"
        if red >= green and red >= blue:
            if green > 120 and blue > 85:
                return "beige"
            if green > 45 and blue < 95 and red < 170:
                return "brown"
            return "red"
        if green >= red and green >= blue:
            return "green"
        if red > 160 and green > 130 and blue > 90:
            return "beige"
        return "brown"

    def _contrast_score(self, first: list[int], second: list[int]) -> float:
        distance = math.sqrt(sum((a - b) ** 2 for a, b in zip(first, second)))
        maximum = math.sqrt(3 * (255**2))
        return round(clamp01(distance / maximum), 3)

    def _tone(self, top_rgb: list[int], bottom_rgb: list[int]) -> str:
        brightness = (sum(top_rgb) + sum(bottom_rgb)) / (6 * 255)
        tone = self._thresholds.get("tone", {})
        dark_threshold = float(tone.get("dark_luminance_threshold", 0.35))
        bright_threshold = float(tone.get("bright_luminance_threshold", 0.70))
        if brightness < dark_threshold:
            return "dark"
        if brightness > bright_threshold:
            return "bright"
        return "neutral"
