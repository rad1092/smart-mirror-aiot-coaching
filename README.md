# 스마트미러 PC3 Vision Gateway

이 저장소는 스마트미러 운동 코칭 프로젝트의 PC3 비전/센서 게이트웨이입니다.

PC1 프론트엔드와 PC2 운동 코칭 서버 코드는 이 저장소에 포함하지 않습니다. PC3는 카메라 프레임과 센서값을 받아 feature만 만들고, 운동 세션이 끝났을 때 PC2에 운동 feature JSON을 전달합니다.

## 역할 분리

| 구분 | 저장소 | 역할 |
| --- | --- | --- |
| PC1 | `dpgns9983-dot/smart-mirror-exercise-only` | Tauri/React 운동 전용 스마트미러 화면 |
| PC2 | `tmdwn0196-osj/smart-mirror-aiot-coaching` | 운동 결과 기반 LLM 코칭/운동 계획 API |
| PC3 | 이 저장소 | FastAPI 비전/센서 분석, baseline, session, WebSocket 중계 |

PC3는 원본 이미지, base64 이미지, 영상, 전체 landmark, segmentation mask를 PC2로 보내지 않습니다. PC2에는 `FeaturePayload` JSON만 보냅니다.

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

`.env.example`을 `.env`로 복사해서 사용합니다.

```env
PC2_COACH_API_URL=http://localhost:7000/api/coach/generate
MOCK_LLM=true
HOST=127.0.0.1
PORT=9000
CORS_ALLOW_ORIGINS=http://localhost:1420,http://127.0.0.1:1420,tauri://localhost

USE_MEDIAPIPE_TASKS=false
POSE_MODEL_PATH=./models/pose/pose_landmarker_lite.task
FACE_MODEL_PATH=
SEGMENTER_MODEL_PATH=

CONFIG_EXERCISE_THRESHOLDS=./config/exercise_thresholds.json
CONFIG_FACE_THRESHOLDS=./config/face_thresholds.json
CONFIG_OUTFIT_THRESHOLDS=./config/outfit_thresholds.json
COLOR_RULES_PATH=./data/color_rules.json
EXERCISE_RULES_PATH=./data/exercise_rules.json
BASELINE_DB_PATH=./data/baselines.sqlite3
```

실제 PC2 서버와 연결할 때만 `MOCK_LLM=false`로 바꿉니다. 비운동 모드는 PC2로 보내지 않고 PC3 로컬 mock 응답을 유지합니다.

## PC1 연동 API

### Baseline capture

```http
POST /api/baselines/users/{user_id}/capture
Content-Type: multipart/form-data
```

form field:

- `slot_type`: `face_front`, `body_front_full`, `body_right_full`, `body_left_full`
- `file`: 캡처 이미지 파일

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

PC1은 session 시작 시 `goal`에 운동 타입을 넣습니다. 지원 타입은 `squat`, `jumping_jack`, `knee_raise`, `lunge`, `pushup`입니다.

WebSocket `exercise_update` 예시:

```json
{
  "type": "exercise_update",
  "session_id": "sess_abc",
  "count": 3,
  "state": "up",
  "feedback": "Keep the movement steady.",
  "posture_errors": [],
  "stability_score": 0.82
}
```

## PC2 연동 계약

PC3는 운동 세션 종료 시점에만 PC2를 호출합니다.

```http
POST http://localhost:7000/api/coach/generate
Content-Type: application/json
```

PC2 요청은 `exercise/session_completed` 전용입니다. `features`에는 `exercise`만 포함하고, `face`, `outfit`, 원본 이미지, null field는 보내지 않습니다.

PC2 응답의 `summary`, `priority`, `exercise_plan`, `mirror_message`, `warnings`, `pc2_payload`는 PC3의 session stop 응답에 그대로 보존됩니다.

## 테스트

```bash
uv run --with-requirements requirements.txt python -m pytest -q
```

서버 실행 후 smoke test:

```bash
uv run --with-requirements requirements.txt python scripts/smoke_test.py --base-url http://127.0.0.1:9000
```

## 커밋하지 않는 파일

- `.env`
- `data/baselines.sqlite3`
- `models/**/*.task`
- 원본 얼굴 이미지, 웹캠 프레임, 운동 영상
- `node_modules`, build output, cache
