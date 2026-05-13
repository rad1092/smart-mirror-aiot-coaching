# PC3 Exercise Pose Model

PC3 is exercise-only. The runtime uses the MediaPipe Pose Landmarker Lite model below for pose landmark detection:

```text
models/pose/pose_landmarker_lite.task
models/pose/pose_landmarker_full.task
```

These pose models are committed to the repository because PC3 needs them to run real exercise analysis after a fresh clone. Lite is the default runtime model. Full is available for accuracy comparison and low-confidence webcam cases.

Other model and weight formats remain ignored by `models/.gitignore` unless they are explicitly allowed. The removed face and segmentation features do not require model files.

## Runtime Settings

```env
USE_MEDIAPIPE_TASKS=true
POSE_MODEL_VARIANT=lite
MAX_POSES=3
```

Check the local model path with:

```bash
python scripts/check_model_paths.py
```
