# PC3 운동 자세 모델

PC3는 exercise-only 범위의 pose 분석만 유지합니다.

현재 지원하는 로컬 모델 위치:

```text
models/pose/pose_landmarker_lite.task
```

모델 파일은 Git에 커밋하지 않습니다. `models/.gitignore`가 `.task`, `.tflite`, `.onnx`, `.pt`, `.pth`, `.bin`, `.safetensors` 같은 모델/가중치 형식을 차단합니다.

모델 파일이 없어도 PC3는 fallback/mock mode로 실행되어야 합니다.

## 설정

```env
USE_MEDIAPIPE_TASKS=true
POSE_MODEL_PATH=./models/pose/pose_landmarker_lite.task
```

모델 경로 확인:

```bash
python scripts/check_model_paths.py
```
