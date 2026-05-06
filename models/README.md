# PC3 로컬 비전 모델

이 디렉터리는 PC3가 로컬 런타임에서 사용할 비전 모델 파일을 두는 위치입니다.

PC3에는 학습용 데이터셋을 포함하지 않습니다. PC3에 필요한 것은 feature 추출, baseline 비교, threshold 기반 분석을 위한 실행용 모델과 설정 파일입니다.

MediaPipe Tasks API를 사용할 경우 모델 파일을 로컬에 직접 배치합니다.

- `models/pose/pose_landmarker_lite.task`
- `models/face/face_landmarker.task`
- `models/segmentation/selfie_segmenter.tflite` 또는 호환 segmentation model

현재 실제 runtime 연결 대상은 다음 하나입니다.

- `models/pose/pose_landmarker_lite.task`

Face Landmarker와 segmentation model은 이후 단계입니다. 현재 PC3 runtime에서는 사용하지 않습니다.

모델 파일은 Git에 커밋하지 않습니다. 이 디렉터리의 `.gitignore`는 `.task`, `.tflite`, `.onnx`, `.pt`, `.pth`, `.bin`, `.safetensors` 같은 모델/가중치 형식을 차단합니다.

모델 파일이 없어도 PC3는 fallback/mock mode로 실행되어야 합니다. 기본 MVP analyzer는 단순 region 기반 face/outfit feature를 계산하고, pose 분석은 MediaPipe runtime 또는 task 파일이 없을 때 안전하게 fallback됩니다.

`mediapipe.solutions` 방식과 설치된 패키지 내장 asset을 사용하는 경우에는 별도 `.task` 파일 없이 pose detection을 사용할 수 있습니다. 다만 현재 권장 runtime 연결 대상은 MediaPipe Pose Landmarker Lite task 파일입니다.

## 로컬 Pose 모델 설정

1. 공식 MediaPipe Pose Landmarker Lite task 파일을 사용자가 직접 다운로드합니다.
2. 아래 경로에 둡니다.

   ```text
   models/pose/pose_landmarker_lite.task
   ```

3. `.env`를 설정합니다.

   ```env
   USE_MEDIAPIPE_TASKS=true
   POSE_MODEL_PATH=./models/pose/pose_landmarker_lite.task
   MOCK_LLM=true
   ```

4. 모델 경로를 확인합니다.

   ```bash
   python scripts/check_model_paths.py
   ```

5. PC3 서버를 실행하고 실제 전신 이미지 또는 웹캠 frame으로 `/api/analyze/exercise`를 테스트합니다.
