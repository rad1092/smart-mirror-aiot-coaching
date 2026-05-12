# PC3 Exercise Pose Model

PC3 is exercise-only. The runtime uses the MediaPipe Pose Landmarker Lite model below for pose landmark detection:

```text
models/pose/pose_landmarker_lite.task
```

This pose model is committed to the repository because PC3 needs it to run real exercise analysis after a fresh clone.

Other model and weight formats remain ignored by `models/.gitignore` unless they are explicitly allowed. The removed face and segmentation features do not require model files.

## Runtime Settings

```env
USE_MEDIAPIPE_TASKS=true
POSE_MODEL_PATH=./models/pose/pose_landmarker_lite.task
```

Check the local model path with:

```bash
python scripts/check_model_paths.py
```
