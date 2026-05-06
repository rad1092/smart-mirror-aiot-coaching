# PC3 Local Vision Models

This directory is for local runtime vision model files used by PC3.

PC3 does not include training datasets. It only needs runtime assets for feature extraction, baseline comparison, and rule/config driven thresholds.

When using MediaPipe Tasks API, place model files locally:

- `models/pose/pose_landmarker_lite.task`
- `models/face/face_landmarker.task`
- `models/segmentation/selfie_segmenter.tflite` or a compatible segmentation model

The current runtime integration target is only:

- `models/pose/pose_landmarker_lite.task`

Face Landmarker and segmentation models are reserved for later stages. They are not used by the current PC3 runtime.

Model files must not be committed to Git. This directory includes `.gitignore` rules for common model and weight formats.

If model files are missing, PC3 must still run in fallback/mock mode. The default MVP analyzers can calculate simple region-based face and outfit features, and pose analysis falls back safely when MediaPipe runtime or task files are unavailable.

When using the older `mediapipe.solutions` API and the installed package supports it, pose detection can use package-provided assets without a separate `.task` file.

## Local Pose Model Setup

1. Download the official MediaPipe Pose Landmarker Lite task file yourself.
2. Place it at:

   ```text
   models/pose/pose_landmarker_lite.task
   ```

3. Configure `.env`:

   ```env
   USE_MEDIAPIPE_TASKS=true
   POSE_MODEL_PATH=./models/pose/pose_landmarker_lite.task
   MOCK_LLM=true
   ```

4. Verify the path:

   ```bash
   python scripts/check_model_paths.py
   ```

5. Run the PC3 server and test `/api/analyze/exercise` with a full-body image or webcam frame.
