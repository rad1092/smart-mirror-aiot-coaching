# Smart Mirror PC3 Vision Gateway

PC3 is the exercise vision gateway for the smart mirror project. It owns baseline
capture, pose analysis, exercise sessions, realtime WebSocket updates, and the
safe bridge to PC2 coaching/routine APIs.

PC3 does not vendor PC1 or PC2 code. PC1 remains the frontend. PC2 remains the
LLM coaching server. PC3 validates and normalizes the data that moves between
them.

## Runtime Roles

| PC | Role |
| --- | --- |
| PC1 | Exercise-only smart mirror frontend |
| PC2 | LLM routine planning and post-exercise coaching server |
| PC3 | Baseline, pose analysis, target tracking, session, API bridge |

PC3 never sends raw images, base64 frames, videos, full landmarks, segmentation
masks, or PC1 display-only fields to PC2. PC2 receives only whitelisted exercise
or routine payloads.

## PC1 UI Contract

PC1 UI/UX 작업자는 [PC1_UI_CONTRACT.md](PC1_UI_CONTRACT.md)를 우선 계약 문서로 사용합니다. 이 문서는 baseline, 루틴 추천, 날짜별 루틴, 운동 화면, WebSocket, 운동 결과 화면에서 PC1이 PC3와 맞춰야 하는 API/필드/표시 기준을 화면 흐름 기준으로 정리합니다.

## Run

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 9000 --reload
```

Recommended Windows/uv path:

```bash
uv run --with-requirements requirements.txt python -m uvicorn app.main:app --host 127.0.0.1 --port 9000 --reload
```

## Environment

```env
PC2_COACH_API_URL=http://localhost:7000/api/coach/generate
PC2_ROUTINE_API_URL=http://localhost:7000/api/routine/profile
PC2_ROUTINE_DAY_API_URL=http://localhost:7000/api/routine/profile/{user_id}/day
MOCK_LLM=true
HOST=127.0.0.1
PORT=9000
CORS_ALLOW_ORIGINS=http://localhost:1420,http://127.0.0.1:1420,tauri://localhost

USE_MEDIAPIPE_TASKS=true
POSE_PIPELINE_MODE=dual
POSE_MODEL_VARIANT=full
POSE_FAST_MODEL_VARIANT=lite
POSE_ACCURATE_MODEL_VARIANT=full
POSE_ACCURATE_INTERVAL=1
MAX_POSES=3
MIN_VALID_FRAME_RATIO=0.55
MAX_MODEL_DISAGREEMENT_RATIO=0.30

CONFIG_EXERCISE_THRESHOLDS=./config/exercise_thresholds.json
EXERCISE_RULES_PATH=./data/exercise_rules.json
EXERCISE_CLASSIFIER_PATH=./models/exercise_classifier/exercise_classifier.json
BASELINE_DB_PATH=./data/baselines.sqlite3
```

Set `MOCK_LLM=false` only when PC2 is running.

## PC1 APIs

### Baseline Capture

```http
POST /api/baselines/users/{user_id}/capture
Content-Type: multipart/form-data
```

Form fields:

- `slot_type`: `face_front`, `body_front_full`
- `file`: captured image file

Response:

```json
{
  "valid": true,
  "slot_type": "body_front_full",
  "reason": null
}
```

PC3 stores validated baseline measurements and slot checkpoints, not the raw
source images.

`face_front` is only a simple profile-photo checkpoint. PC3 checks that a
front-facing face is visible in a decodable, non-dark frame; it does not run
identity recognition or send face features to PC2.

### Pre-Exercise Routine

```http
POST /api/routines/profile
Content-Type: application/json
```

PC1 sends its existing `RecommendationRequestPayload`. PC3 checks that the
profile is complete and confirms the saved PC3 baseline has all required
user-source slots:

- `face_front`
- `body_front_full`

The baseline contract is intentionally small: a front profile face checkpoint
and a front full-body checkpoint are enough before routine planning.

PC3 also accepts the newer flat routine request documented by PC2, including
optional `start_date`. PC3 then calls PC2 `POST /api/routine/profile` with a
sanitized request, preserves PC2 schedule metadata (`routine_id`, `start_date`,
`scheduled_dates`) and detailed routine instructions (`how_to`, `tips`), and
still returns the existing PC1 `items` preview. If PC2 is unavailable, PC3
returns a PC1-renderable basic fallback response with `source="basic"` and a
reason that PC2 was unavailable.

```http
GET /api/routines/profile/{user_id}/day?target_date=YYYY-MM-DD
```

PC3 proxies this to PC2 for date-based routine lookup and preserves the selected
day's `message`, `exercises`, `how_to`, and `tips`.

### Exercise Session

```http
POST /api/sessions/start
POST /api/analyze/exercise
POST /api/sessions/{session_id}/stop
WS   /ws/sessions/{session_id}
```

Supported exercise goals:

- `squat`
- `jumping_jack`
- `knee_raise`
- `lunge`
- `pushup`

Realtime updates include PC1 display fields such as `posture_errors`,
`stability_score`, target tracking state, detected exercise type, and measurement
quality. These fields are kept out of PC2 requests unless they are explicitly
allowed by the PC2 payload contract.

PC1 must keep uploading exercise frames while the session is running and keep
using the `ws_url` returned from `POST /api/sessions/start` for realtime updates.
Recommended frame upload cadence:

- `squat`, `pushup`, `lunge`: every 300 ms.
- `knee_raise`, `jumping_jack`: every 200 ms.

Recommended exercise frame resolution:

- Preferred: `1280x720` JPEG frames.
- Minimum practical fallback: `960x540`.
- Avoid going above `1920x1080` during dual MediaPipe mode unless the PC3 CPU
  budget has been checked.

PC1 should not send overlapping frame uploads. If a previous
`POST /api/analyze/exercise` request is still in flight, skip the next scheduled
frame. The preferred implementation is an adaptive loop: upload a frame, wait for
the response, then schedule the next upload after 150-300 ms depending on the
selected exercise. A slower cadence, such as 1500 ms, can miss the down/up
transition and prevent the exercise count from increasing.

PC3 freezes count updates while `target_status` is `target_recovering` or
`target_lost`, or while blocking posture errors such as `person_too_far`,
`partial_body`, `low_confidence`, or `model_disagreement` are present.

## PC2 APIs

PC3 uses these PC2 endpoints:

- `POST /api/routine/profile` before exercise, for routine planning.
- `GET /api/routine/profile/{user_id}/day` for date-based routine lookup.
- `POST /api/coach/generate` after exercise, for session result coaching.

Post-exercise PC2 requests are `exercise/session_completed` only. Routine
requests are sanitized profile-only requests. Raw images, baseline raw data,
null values, and PC1 UI-only fields are not sent to PC2.

## Test

```bash
uv run --with-requirements requirements.txt python -m pytest -q
```

Optional smoke test after starting the server:

```bash
uv run --with-requirements requirements.txt python scripts/smoke_test.py --base-url http://127.0.0.1:9000
```
