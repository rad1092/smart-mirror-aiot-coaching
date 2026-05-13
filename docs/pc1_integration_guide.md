# PC1 Integration Guide

PC1 is the exercise-only frontend. PC3 provides baseline validation, pre-exercise
routine planning, pose analysis, realtime feedback, and post-exercise coaching
bridging.

## Base URL

Local development:

```text
http://127.0.0.1:9000
```

When PC1 runs on another computer, start PC3 on all interfaces and expose the
WebSocket host:

```env
HOST=0.0.0.0
WS_PUBLIC_HOST=<PC3_LAN_IP>
```

PC1 should call PC3, not PC2, for the routine recommendation flow.

## 1. Baseline Capture

```http
POST /api/baselines/users/{user_id}/capture
Content-Type: multipart/form-data
```

Form fields:

- `slot_type`: `face_front`, `body_front_full`, `body_right_full`, `body_left_full`
- `file`: captured image file

Response:

```json
{
  "valid": true,
  "slot_type": "face_front",
  "reason": null
}
```

PC3 does not store the original image. It stores validated baseline measurements
and slot checkpoints.

Baseline status:

```http
GET /api/baselines/users/{user_id}
```

PC1 may display completion when the response has `source === "user"` and the
required face/body slots are present. PC3 still verifies the saved baseline again
before routine planning.

## 2. Pre-Exercise Routine Recommendation

```http
POST /api/routines/profile
Content-Type: application/json
```

PC1 sends its existing `RecommendationRequestPayload` shape:

```json
{
  "user_id": "profile_1",
  "profile": {
    "name": "Mirror User",
    "weight_kg": 70,
    "height_cm": 172,
    "goal": "lower_body_strength",
    "experience_level": "beginner",
    "weekly_frequency": "three_four",
    "limitations": ["knee"]
  },
  "baseline": {
    "ready": true,
    "completed_slots": [
      "face_front",
      "body_front_full",
      "body_right_full",
      "body_left_full"
    ]
  }
}
```

PC3 validates required profile fields and confirms the saved PC3 baseline has
all required user-source slots. PC3 then calls PC2 `/api/routine/profile` with a
sanitized payload.

PC3 response shape is PC1 `RecommendationResponsePayload`:

```json
{
  "source": "ai",
  "difficulty": "easy",
  "title": "AI routine from PC2",
  "description": "Routine generated from your profile.",
  "reason_lines": ["Lower body control first."],
  "estimated_minutes": 10,
  "start_exercise_type": "squat",
  "items": [
    {
      "exercise_type": "squat",
      "title": "Day 1 - squat",
      "reps": 8,
      "rest_sec": 60,
      "focus": "controlled posture",
      "summary": "Build stable lower-body movement."
    }
  ]
}
```

If PC2 fails, PC3 returns `source="basic"` with a local fallback routine that PC1
can still render and start.

## 3. Exercise Session

Start:

```http
POST /api/sessions/start
Content-Type: application/json
```

Request:

```json
{
  "user_id": "profile_1",
  "mode": "exercise",
  "goal": "pushup"
}
```

Supported `goal` values:

- `squat`
- `jumping_jack`
- `knee_raise`
- `lunge`
- `pushup`

Response includes a `ws_url` for realtime updates.

## 4. Realtime and Frame Analysis

WebSocket:

```text
WS /ws/sessions/{session_id}
```

Frame upload:

```http
POST /api/analyze/exercise
Content-Type: multipart/form-data
```

Form fields:

- `session_id`
- `file`

PC3 handles realtime feedback locally. PC2 is not called for every frame.

Example WebSocket update:

```json
{
  "type": "exercise_update",
  "session_id": "sess_abc",
  "count": 5,
  "state": "up",
  "feedback": "Keep the movement steady.",
  "posture_errors": ["knees_caving_in"],
  "stability_score": 0.74,
  "person_count": 2,
  "target_status": "multi_person_detected",
  "target_confidence": 0.91,
  "detected_type": "squat",
  "exercise_confidence": 0.88,
  "goal_mismatch": false,
  "measurement_quality": "dual_verified",
  "measurement_confidence": 0.86
}
```

## 5. Stop Session

```http
POST /api/sessions/{session_id}/stop
```

At stop time, PC3 finalizes the exercise feature. If measurement quality is good
and `MOCK_LLM=false`, PC3 calls PC2 `/api/coach/generate`. If quality is too low,
PC3 skips PC2 and returns local guidance asking the user to retake the set.

Important response fields:

- `features.exercise.type`
- `features.exercise.count`
- `features.exercise.stability_score`
- `features.exercise.posture_errors`
- `features.exercise.measurement_quality`
- `features.exercise.measurement_confidence`
- `coaching.summary`
- `coaching.priority`
- `coaching.exercise_plan`
- `coaching.mirror_message`
- `coaching.pc2_payload`
