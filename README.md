# 스마트미러 PC3 Vision Gateway

이 저장소는 스마트미러 운동 코칭 프로젝트의 PC3 운동 분석 게이트웨이입니다.

PC3는 이제 exercise-only 범위만 유지합니다. 얼굴 분석, 옷 분석, 외출 분석 API와 관련 설정/모델 placeholder는 제거했습니다. PC1 화면 흐름 때문에 `face_front` baseline 슬롯 이름은 남아 있지만, 얼굴 feature 분석이 아니라 단순 캡처 checkpoint로만 사용합니다.

## 역할

| 구분 | 역할 |
| --- | --- |
| PC1 | 운동 전용 스마트미러 화면 |
| PC2 | 운동 결과 기반 LLM 코칭/운동 계획 API |
| PC3 | 운동 baseline, pose 분석, session, WebSocket 중계 |

PC3는 원본 이미지, base64 이미지, 영상, 전체 landmark, segmentation mask를 PC2로 보내지 않습니다. PC2에는 운동 feature JSON만 보냅니다.

## 실행

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 9000 --reload
```

Windows 로컬 환경에서 `python` 런처가 잡히지 않으면 다음 방식으로 실행합니다.

```bash
uv run --with-requirements requirements.txt python -m uvicorn app.main:app --host 127.0.0.1 --port 9000 --reload
```

## 환경 변수

```env
PC2_COACH_API_URL=http://localhost:7000/api/coach/generate
MOCK_LLM=true
HOST=127.0.0.1
PORT=9000
CORS_ALLOW_ORIGINS=http://localhost:1420,http://127.0.0.1:1420,tauri://localhost

USE_MEDIAPIPE_TASKS=true
POSE_MODEL_VARIANT=lite
MAX_POSES=3
# Optional explicit override. If unset, POSE_MODEL_VARIANT selects the model.
# POSE_MODEL_PATH=./models/pose/pose_landmarker_lite.task

CONFIG_EXERCISE_THRESHOLDS=./config/exercise_thresholds.json
EXERCISE_RULES_PATH=./data/exercise_rules.json
EXERCISE_CLASSIFIER_PATH=./models/exercise_classifier/exercise_classifier.json
BASELINE_DB_PATH=./data/baselines.sqlite3
```

실제 PC2 서버와 연결할 때만 `MOCK_LLM=false`로 바꿉니다.

## PC1 연동 API

### Baseline capture

```http
POST /api/baselines/users/{user_id}/capture
Content-Type: multipart/form-data
```

form field:

- `slot_type`: `face_front`, `body_front_full`, `body_right_full`, `body_left_full`
- `file`: 캡처 이미지 파일

`face_front`는 얼굴 분석이 아니라 PC1 baseline 흐름을 위한 밝기 기반 checkpoint입니다.

응답:

```json
{
  "valid": true,
  "slot_type": "body_front_full",
  "reason": null
}
```

### Exercise session

```http
POST /api/sessions/start
POST /api/analyze/exercise
POST /api/sessions/{session_id}/stop
WS   /ws/sessions/{session_id}
```

지원 운동 타입:

- `squat`
- `jumping_jack`
- `knee_raise`
- `lunge`
- `pushup`

WebSocket `exercise_update` 예시:

```json
{
  "type": "exercise_update",
  "session_id": "sess_abc",
  "count": 3,
  "state": "up",
  "feedback": "Keep the movement steady.",
  "posture_errors": [],
  "stability_score": 0.82,
  "person_count": 1,
  "target_status": "tracking",
  "target_confidence": 0.91,
  "detected_type": "squat",
  "exercise_confidence": 0.88,
  "goal_mismatch": false
}
```

## PC2 연동 계약

PC3는 운동 세션 종료 시점에만 PC2를 호출합니다.

```http
POST http://localhost:7000/api/coach/generate
Content-Type: application/json
```

PC2 요청은 `exercise/session_completed` 전용입니다. `features`에는 `exercise`만 포함하고, 원본 이미지, 얼굴/옷 feature, null field는 보내지 않습니다.

PC2 응답의 `summary`, `priority`, `exercise_plan`, `mirror_message`, `warnings`, `pc2_payload`는 PC3의 session stop 응답에 보존됩니다.

## 테스트

```bash
uv run --with-requirements requirements.txt python -m pytest -q
```

서버 실행 후 smoke test:

```bash
uv run --with-requirements requirements.txt python scripts/smoke_test.py --base-url http://127.0.0.1:9000
```
