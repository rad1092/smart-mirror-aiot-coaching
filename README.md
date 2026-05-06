# 스마트미러형 자기관리 AIoT 코칭 시스템

이 저장소는 스마트미러형 자기관리 AIoT 코칭 시스템의 공용 프로젝트 저장소입니다.

현재 커밋된 실제 구현 범위는 `PC3 Vision Gateway`입니다. PC1 스마트미러 프론트 앱과 PC2 로컬 LLM Coach API 서버는 아직 이 저장소에 구현되어 있지 않지만, PC1/PC2 담당자가 이 저장소의 API 계약과 문서를 기준으로 각자 기능을 붙일 수 있도록 정리되어 있습니다.

## 시스템 역할

| 구분 | 역할 | 현재 상태 |
| --- | --- | --- |
| PC1 | 스마트미러 프론트 앱. Tauri + React + TypeScript 예정 | 외부 시스템. 아직 구현하지 않음 |
| PC2 | 로컬 LLM Coach API. vLLM + RAG + wrapper API 예정 | 외부 시스템. 아직 구현하지 않음 |
| PC3 | 비전/센서 게이트웨이. FastAPI + OpenCV + MediaPipe | 이 저장소에 구현됨 |

PC3는 PC1과 PC2 사이의 중앙 오케스트레이터입니다. 이미지와 센서값을 직접 받아 Pose/Face/Outfit/Sensor feature를 만들고, baseline과 비교한 뒤, 필요한 이벤트에서만 PC2를 호출합니다.

PC2에는 원본 이미지, base64 이미지, 프레임 경로, 영상, 전체 landmark, segmentation mask를 보내지 않습니다. PC2에는 항상 `FeaturePayload` JSON만 보냅니다.

## 현재 저장소 구조

현재는 PC3 우선 구조입니다.

```text
.
├─ app/                 # PC3 FastAPI 애플리케이션
├─ config/              # 운동/얼굴/옷 분석 threshold 설정
├─ data/                # 기본 baseline, color rules, exercise rules
├─ docs/                # PC1/PC2 연결 가이드와 PC2 계약 문서
├─ models/              # 로컬 실행용 비전 모델 배치 위치
├─ scripts/             # 모델 경로 확인, smoke test
└─ tests/               # PC3 backend 테스트
```

나중에 PC1/PC2 코드까지 한 저장소에 합치면 아래처럼 monorepo 구조로 재정리하는 것을 권장합니다.

```text
smart-mirror-aiot-coaching/
├─ pc1-smart-mirror/
├─ pc2-coach-server/
└─ pc3-vision-gateway/
```

그 전까지는 PC1/PC2 담당자가 이 저장소를 PC3 API/JSON 계약의 기준 문서로 사용하면 됩니다.

## MVP 범위

PC3는 4개 모드 API를 제공합니다.

| mode | 설명 | 구현 수준 |
| --- | --- | --- |
| `exercise` | 스쿼트 카운트, 자세 상태, WebSocket 실시간 feedback | 실제 동작 가능 MVP |
| `grooming` | 얼굴 영역 brightness/redness/beard_shadow 수치 feature 추출 | 단순 region 기반 MVP |
| `outfit` | 상의/하의 대표색, 대비, tone feature 추출 | 단순 region 기반 MVP |
| `outing` | face + outfit + environment + purpose 통합 분석 | 단발 분석 MVP |

얼굴 분석은 의학적 진단이 아닙니다. 피부 질환, 염증, 피로, 건강 상태를 추정하지 않습니다. 옷 분석도 스타일을 확정 분류하지 않고 색상과 tone feature만 만듭니다.

## PC1 연결 문서

PC1 담당자는 먼저 [docs/pc1_integration_guide.md](docs/pc1_integration_guide.md)를 보면 됩니다.

핵심 흐름은 다음과 같습니다.

1. `POST /api/sessions/start`로 session 생성
2. 응답의 `ws_url`로 WebSocket 연결
3. 운동 모드에서는 `/api/analyze/exercise`로 frame 업로드
4. WebSocket으로 `count`, `state`, `feedback` 수신
5. 운동 종료 시 `POST /api/sessions/{session_id}/stop`
6. 최종 `coaching` JSON을 PC1 카드에 표시

grooming/outfit/outing은 WebSocket이 아니라 REST 응답으로 최종 feature와 coaching을 받습니다.

## PC2 연결 문서

PC2 담당자는 먼저 [docs/pc2_integration_guide.md](docs/pc2_integration_guide.md)와 [docs/pc2_prompt_contract.md](docs/pc2_prompt_contract.md)를 보면 됩니다.

PC3가 호출하는 PC2 endpoint 기본값은 다음입니다.

```text
POST http://localhost:8100/api/coach/generate
```

PC2는 `FeaturePayload` JSON을 입력으로 받고 `CoachingResponse` JSON만 반환해야 합니다.

PC3의 mock mode가 켜져 있으면 PC2가 없어도 PC3는 mode별 mock coaching을 반환합니다.

```env
MOCK_LLM=true
```

실제 PC2와 연결하려면 다음처럼 설정합니다.

```env
MOCK_LLM=false
PC2_COACH_API_URL=http://<PC2_HOST>:8100/api/coach/generate
```

## 실행 방법

Python 3.10+ 기준입니다.

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 9000 --reload
```

기본 host는 `127.0.0.1`입니다. 같은 컴퓨터에서 PC1/PC3를 개발할 때 권장됩니다.

PC1이 다른 PC에서 PC3에 붙어야 할 때만 LAN IP로 열어야 합니다.

```env
HOST=0.0.0.0
WS_PUBLIC_HOST=<PC3_LAN_IP>
```

이 경우 PC1은 다음 주소를 사용합니다.

```text
REST: http://<PC3_LAN_IP>:9000
WS:   ws://<PC3_LAN_IP>:9000/ws/sessions/{session_id}
```

이 MVP 서버를 인터넷 포트포워딩으로 노출하지 마세요. 같은 LAN 안에서만 사용하고, OS 방화벽으로 접근 범위를 제한하는 것이 안전합니다.

## 환경 변수

`.env.example`을 복사해서 `.env`로 사용합니다.

```env
PC2_COACH_API_URL=http://localhost:8100/api/coach/generate
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

PC1 개발 origin 기본 허용값은 다음입니다.

- `http://localhost:1420`
- `http://127.0.0.1:1420`
- `tauri://localhost`

`CORS_ALLOW_ORIGINS=*`로 열지 마세요.

## API 요약

### Health

```text
GET /health
```

응답:

```json
{
  "status": "ok",
  "service": "pc3-vision-gateway"
}
```

### Session 시작

```text
POST /api/sessions/start
```

요청:

```json
{
  "user_id": "default",
  "mode": "exercise",
  "goal": "squat"
}
```

응답:

```json
{
  "session_id": "sess_xxx",
  "user_id": "default",
  "mode": "exercise",
  "goal": "squat",
  "status": "running",
  "ws_url": "ws://127.0.0.1:9000/ws/sessions/sess_xxx"
}
```

### Session 종료

```text
POST /api/sessions/{session_id}/stop
```

운동 세션에서는 이 시점에만 PC2 또는 mock coaching을 호출합니다. 매 frame마다 LLM을 호출하지 않습니다.

### Session 결과 조회

```text
GET /api/sessions/{session_id}/result
```

### Baseline 조회/저장

```text
GET  /api/baselines/users/{user_id}
POST /api/baselines/users/{user_id}
```

사용자별 baseline은 `BASELINE_DB_PATH`의 SQLite DB에 저장합니다. 원본 이미지나 프레임은 저장하지 않습니다.

처음 사용하는 PC1은 사용자를 `user_1`, `user_2`처럼 생성하고 간단한 baseline 값을 저장한 뒤, 이후 session에서 같은 `user_id`를 쓰면 됩니다.

### Sensor update

```text
POST /api/sensors/update
```

요청:

```json
{
  "temperature": 24.5,
  "humidity": 48,
  "illuminance": 360
}
```

### Analyze

각 analyze endpoint는 같은 mode로 생성된 session에서만 호출해야 합니다.

예를 들어 `mode=exercise` session으로 `/api/analyze/grooming`을 호출하면 `400 Bad Request`를 반환합니다.

```text
POST /api/analyze/exercise
POST /api/analyze/grooming
POST /api/analyze/outfit
POST /api/analyze/outing
```

모든 analyze 요청은 `multipart/form-data`를 사용합니다.

## WebSocket

운동 실시간 업데이트 전용입니다.

```text
WS /ws/sessions/{session_id}
```

예시 메시지:

```json
{
  "type": "exercise_update",
  "session_id": "sess_xxx",
  "count": 8,
  "state": "down",
  "feedback": "무릎이 안쪽으로 모이지 않게 해주세요."
}
```

## 실행용 모델

PC3에는 학습용 얼굴/운동/패션 데이터셋을 넣지 않습니다. 필요한 것은 실행용 모델 파일, baseline JSON, threshold 설정, color rules 정도입니다.

현재 실제 MediaPipe runtime 연결 대상은 Pose Landmarker Lite입니다.

```text
models/pose/pose_landmarker_lite.task
```

모델 파일은 Git에 커밋하지 않습니다. `models/.gitignore`가 `.task`, `.tflite`, `.onnx`, `.pt`, `.pth`, `.bin`, `.safetensors` 등을 차단합니다.

모델 경로 확인:

```bash
python scripts/check_model_paths.py
```

모델이 없어도 fallback/mock mode로 서버가 실행됩니다.

## Smoke test

서버를 먼저 실행한 뒤 smoke test를 실행합니다.

```bash
python scripts/smoke_test.py --base-url http://localhost:9000
```

이 스크립트는 서버를 직접 실행하지 않습니다. 이미 실행 중인 PC3 서버에 요청을 보내 기본 API 흐름을 확인합니다.

## 테스트

```bash
pytest
```

기본 테스트는 실제 카메라, 실제 PC2 서버, face/segmentation 모델 없이 통과해야 합니다.

## Git 관리 원칙

커밋하지 않는 파일:

- `.env`
- `data/baselines.sqlite3`
- `models/**/*.task`
- `models/**/*.tflite`
- LLM/RAG 모델 파일
- 원본 얼굴 이미지
- 웹캠 프레임
- 운동 영상
- `node_modules`, build output, cache

문서와 소스 파일은 UTF-8 기준으로 관리합니다. `.editorconfig`와 `.gitattributes`를 함께 사용합니다.
