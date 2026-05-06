from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np

from app.vision.face_analyzer import FaceAnalyzer
from app.vision.outfit_color_analyzer import OutfitColorAnalyzer


def test_docs_and_model_asset_placeholders_exist():
    expected = [
        Path("models/README.md"),
        Path("models/.gitignore"),
        Path("models/pose/.gitkeep"),
        Path("models/face/.gitkeep"),
        Path("models/segmentation/.gitkeep"),
        Path("docs/outfit_knowledge_example.md"),
        Path("docs/exercise_knowledge_example.md"),
        Path("docs/grooming_knowledge_example.md"),
    ]

    for path in expected:
        assert path.exists(), f"missing {path}"


def test_model_gitignore_blocks_common_weight_formats():
    content = Path("models/.gitignore").read_text(encoding="utf-8")

    for pattern in ["*.task", "*.tflite", "*.onnx", "*.pt", "*.pth", "*.bin", "*.safetensors"]:
        assert pattern in content


def test_face_analyzer_falls_back_when_config_is_missing(tmp_path):
    image = np.full((120, 120, 3), 128, dtype=np.uint8)
    analyzer = FaceAnalyzer(tmp_path / "missing_face_thresholds.json")

    feature = analyzer.analyze(image)

    assert 0 <= feature.brightness <= 1
    assert 0 <= feature.redness <= 1
    assert 0 <= feature.beard_shadow <= 1


def test_outfit_analyzer_uses_color_rules_for_nearest_color():
    image = np.zeros((240, 240, 3), dtype=np.uint8)
    image[:] = (130, 130, 130)
    image[84:132, 72:168] = (90, 45, 30)  # BGR close to navy RGB anchor.
    image[132:204, 72:168] = (20, 20, 20)
    analyzer = OutfitColorAnalyzer(
        thresholds_path=Path("config/outfit_thresholds.json"),
        color_rules_path=Path("data/color_rules.json"),
    )

    feature = analyzer.analyze(image)

    assert feature.top_color.name == "navy"
    assert feature.bottom_color.name == "black"


def test_outfit_analyzer_falls_back_when_color_rules_missing(tmp_path):
    image = np.zeros((240, 240, 3), dtype=np.uint8)
    image[:] = (130, 130, 130)
    image[84:132, 72:168] = (0, 0, 255)  # BGR red.
    image[132:204, 72:168] = (20, 20, 20)
    analyzer = OutfitColorAnalyzer(
        thresholds_path=tmp_path / "missing_outfit_thresholds.json",
        color_rules_path=tmp_path / "missing_color_rules.json",
    )

    feature = analyzer.analyze(image)

    assert feature.top_color.name == "red"
    assert feature.bottom_color.name == "black"


def test_check_model_paths_script_succeeds_without_models():
    result = subprocess.run(
        [sys.executable, "scripts/check_model_paths.py"],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "fallback/mock mode" in result.stdout
