from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_docs_and_model_asset_placeholders_exist():
    expected = [
        Path("models/README.md"),
        Path("models/.gitignore"),
        Path("models/pose/.gitkeep"),
        Path("docs/exercise_knowledge_example.md"),
    ]

    for path in expected:
        assert path.exists(), f"missing {path}"


def test_model_gitignore_blocks_common_weight_formats():
    content = Path("models/.gitignore").read_text(encoding="utf-8")

    for pattern in ["*.task", "*.tflite", "*.onnx", "*.pt", "*.pth", "*.bin", "*.safetensors"]:
        assert pattern in content


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
