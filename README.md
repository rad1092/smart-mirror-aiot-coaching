# Smart Mirror AIoT Coaching System

This repository is the shared project repository for the smart mirror AIoT coaching system.

The system is split into three PC roles:

- `PC1`: smart mirror frontend app, planned as Tauri + React + TypeScript.
- `PC2`: local Coach API server, planned as vLLM + RAG + wrapper endpoint.
- `PC3`: vision and sensor gateway, implemented here with Python + FastAPI.

The current committed implementation is the PC3 Vision Gateway. PC1 and PC2 teams can use this repository as the integration contract and add their own components in separate folders or branches when their work starts.

PC3 Vision Gateway sits between the PC1 smart mirror frontend and the PC2 local Coach API.

PC3 extracts numeric and symbolic features from images and sensors, compares them with baseline values, decides whether coaching is needed, and calls PC2 only with `FeaturePayload` JSON. PC3 never sends raw images, base64 images, frame paths, saved frames, videos, or camera streams to the LLM.

PC1 and PC2 are external systems in the current codebase. This version does not implement the PC1 Tauri app or the PC2 vLLM/RAG server.

## Repository Status

Current layout is PC3-first:

```text
.
├─ app/                 # PC3 FastAPI application
├─ config/              # PC3 threshold configs
├─ data/                # PC3 baseline defaults and feature rules
├─ docs/                # PC2 prompt contract and future PC2 knowledge examples
├─ models/              # local-only PC3 runtime model placement
├─ scripts/             # PC3 validation scripts
└─ tests/               # PC3 backend tests
```

If the project moves to a full monorepo later, keep the ownership boundary explicit:

```text
smart-mirror-aiot-coaching/
├─ pc1-smart-mirror/
├─ pc2-coach-server/
└─ pc3-vision-gateway/
```

Until then, PC1 and PC2 should treat this repo as the authoritative PC3 API and JSON contract.

## MVP Scope

This MVP supports four API modes:

- `exercise`: squat counting and posture feedback with realtime WebSocket updates.
- `grooming`: face feature extraction for `brightness`, `redness`, and `beard_shadow`.
- `outfit`: top/bottom representative color, contrast, and tone feature extraction.
- `outing`: combined face, outfit, environment, and purpose payload for final outing checks.

The analysis is intentionally simple. Face analysis is not diagnosis and must not be treated as skin, disease, fatigue, or health assessment. PC3 does not definitively classify outfit style; it extracts color and tone features only.

## Runtime Assets

PC3 does not include training datasets for face, exercise, or fashion tasks. PC3 needs only runtime assets and small configuration files:

- Local vision model files under `models/` when using MediaPipe Tasks.
- `data/baseline_default.json` for default baseline feature values.
- `data/baselines.sqlite3` for user-specific baseline values created during onboarding.
- `config/*_thresholds.json` for analyzer thresholds.
- `data/color_rules.json` for RGB anchor to color-name mapping.
- `data/exercise_rules.json` for exercise landmarks and future posture rules.

Model files are local runtime assets and must not be committed to Git. `models/.gitignore` blocks common model and weight formats such as `.task`, `.tflite`, `.onnx`, `.pt`, `.pth`, `.bin`, and `.safetensors`.

If model files are missing, PC3 still runs in fallback/mock mode.

The current real MediaPipe runtime target is Pose Landmarker Lite only:

```text
models/pose/pose_landmarker_lite.task
```

Face Landmarker and segmentation model integration are later stages. This version keeps grooming and outfit analysis on safe region-based feature extraction.

## PC3 vs PC2 Knowledge Boundary

PC3 owns:

- MediaPipe runtime model paths
- default baseline feature JSON and user-specific baseline records
- threshold config
- RGB to color-name mapping
- outfit feature extraction regions
- exercise posture rule IDs and thresholds
- face feature thresholds
- test and validation scripts

PC2 owns:

- color-combination rules
- purpose-specific outfit rules
- outfit style taxonomy
- exercise routine knowledge
- posture-error correction sentences
- grooming advice sentences
- weather and purpose-specific self-management knowledge

The files under `docs/*_knowledge_example.md` are examples for a future PC2 RAG/knowledge_base. PC3 does not use them at runtime.

## Run

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 9000 --reload
```

Environment variables:

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

The default host is `127.0.0.1`, so PC3 only accepts connections from the same computer. This is the recommended development and single-machine smart mirror setting.

Use `0.0.0.0` only when PC1 runs on another machine in the same LAN:

```env
HOST=0.0.0.0
WS_PUBLIC_HOST=<PC3_LAN_IP>
```

In that mode, PC1 should call `http://<PC3_LAN_IP>:9000` and connect to `ws://<PC3_LAN_IP>:9000/ws/sessions/{session_id}`. Do not expose this MVP server through internet port forwarding; restrict access with the OS firewall or local network rules.

For a future PC1 Tauri/React development app, PC3 allows these origins by default:

- `http://localhost:1420`
- `http://127.0.0.1:1420`
- `tauri://localhost`

Adjust `CORS_ALLOW_ORIGINS` if the PC1 development origin changes. Do not use `*` for this MVP server.

## Model Path Check

```bash
python scripts/check_model_paths.py
```

This script reports whether local pose, face, and segmentation model files exist. Missing files do not fail the script because fallback mode is valid for the MVP.

To enable the real Pose Landmarker Lite runtime:

1. Download the official MediaPipe Pose Landmarker Lite task file locally.
2. Put it at `models/pose/pose_landmarker_lite.task`.
3. Create `.env` from `.env.example` and set:

   ```env
   USE_MEDIAPIPE_TASKS=true
   POSE_MODEL_PATH=./models/pose/pose_landmarker_lite.task
   MOCK_LLM=true
   ```

4. Run `python scripts/check_model_paths.py`.
5. Start the server.
6. Send a full-body image or webcam frame to `/api/analyze/exercise`.

## Smoke Test

Start the server separately, then run:

```bash
python scripts/smoke_test.py --base-url http://localhost:9000
```

The smoke test does not start the server. It calls an already running PC3 server, creates an in-memory dummy image, exercises the four analyze flows, and checks that mode mismatch returns `400`.

## API

### Health

`GET /health`

```json
{
  "status": "ok",
  "service": "pc3-vision-gateway"
}
```

### Sessions

`POST /api/sessions/start`

```json
{
  "user_id": "default",
  "mode": "exercise",
  "goal": "squat"
}
```

Response includes:

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

`POST /api/sessions/{session_id}/stop`

Stops the session and, for exercise sessions, calls PC2 or mock coaching on `session_completed`.

`GET /api/sessions/{session_id}/result`

Returns the latest stored session result.

### Baselines

User-specific baselines are stored in SQLite at `BASELINE_DB_PATH`. Unknown users fall back to `data/baseline_default.json`.

`GET /api/baselines/users/{user_id}`

Returns the saved user baseline when one exists, otherwise returns the default baseline with `source="default"`.

`POST /api/baselines/users/{user_id}`

Creates or replaces a user's baseline. This endpoint stores only numeric/symbolic baseline values, not original images or frames.

```json
{
  "exercise": {
    "squat": {
      "avg_count": 12,
      "avg_stability_score": 0.78
    }
  },
  "face": {
    "brightness": 0.71,
    "redness": 0.14,
    "beard_shadow": 0.31
  },
  "outfit": {
    "preferred_tones": ["navy", "gray", "black"],
    "preferred_colors": ["navy", "gray", "white"]
  }
}
```

For first-run onboarding, PC1 can ask the user to create a profile such as `user_1` or `user_2`, collect simple baseline measurements, then call this endpoint before starting analysis sessions with the same `user_id`.

### Sensors

`POST /api/sensors/update`

```json
{
  "temperature": 24.5,
  "humidity": 48,
  "illuminance": 360
}
```

### Analyze

Each analyze endpoint must be called with a session created for the same `mode`. For example, a session started with `mode=exercise` cannot call `/api/analyze/grooming`; PC3 returns `400 Bad Request`.

`POST /api/analyze/exercise`

Multipart fields:

- `session_id`
- `file`

Returns an exercise update and broadcasts the same realtime state to WebSocket subscribers.

`POST /api/analyze/grooming`

Multipart fields:

- `session_id`
- `file`

Returns face features, face baseline diff, environment, and coaching.

`POST /api/analyze/outfit`

Multipart fields:

- `session_id`
- `file`
- `purpose` optional: `interview`, `date`, `daily`, `casual`

Returns outfit features, environment, and coaching.

`POST /api/analyze/outing`

Multipart fields:

- `session_id`
- `file`
- `purpose`: `interview`, `date`, or `daily`

Runs face and outfit analyzers on the same image, adds the latest sensor environment, and returns coaching.

## PC1 Exercise Flow

PC1 is not implemented in this repository. The backend is prepared so a future PC1 app can use this flow:

1. Call `POST /api/sessions/start`.
2. Connect to the returned `ws_url`.
3. Upload frames to `POST /api/analyze/exercise`.
4. Receive realtime `count`, `state`, and `feedback` over WebSocket.
5. Call `POST /api/sessions/{session_id}/stop`.
6. Display the final coaching JSON.

WebSocket is used for exercise realtime updates only. `grooming`, `outfit`, and `outing` return final coaching through REST responses.

## PC2 Coach Contract

PC2 is an external system. PC3 calls `POST /api/coach/generate` through the configured `PC2_COACH_API_URL`.

The full prompt and JSON contract is documented in [docs/pc2_prompt_contract.md](docs/pc2_prompt_contract.md).

PC2 receives only `FeaturePayload`:

- Extracted exercise, face, and outfit features
- Baseline diff
- Sensor environment
- Mode, event, purpose

PC2 must return only `CoachingResponse` JSON.

## Mock Mode

Set `MOCK_LLM=true` to skip PC2 and return deterministic mode-specific mock coaching. This is the default so the server can run without PC1, PC2, camera hardware, or sensors.

## Tests

```bash
pytest
```

The default tests do not require a real camera, local model files, or a running PC2 server.
