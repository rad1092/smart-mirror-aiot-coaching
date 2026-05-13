# PC1 연동 가이드

PC1은 운동 전용 스마트미러 UI이고, PC3는 baseline 검증, 운동 frame 분석, WebSocket 실시간 feedback, session 종료 결과를 제공합니다.

## Base URL

로컬 개발 기본값:

```text
http://127.0.0.1:9000
```

PC1이 다른 PC에서 실행되면 PC3 `.env`에서 다음을 설정합니다.

```env
HOST=0.0.0.0
WS_PUBLIC_HOST=<PC3_LAN_IP>
```

## Quick Baseline

PC1 `BaselineSetupPage`는 각 slot마다 캡처 이미지를 PC3로 보냅니다.

```http
POST /api/baselines/users/{user_id}/capture
Content-Type: multipart/form-data
```

form field:

- `slot_type`: `face_front`, `body_front_full`, `body_right_full`, `body_left_full`
- `file`: 이미지 파일

응답:

```json
{
  "valid": true,
  "slot_type": "face_front",
  "reason": null
}
```

`valid=false`이면 PC1은 같은 slot을 다시 촬영하면 됩니다. PC3는 원본 이미지를 저장하지 않고 추출된 baseline 값 또는 slot checkpoint만 저장합니다.

baseline 저장 확인:

```http
GET /api/baselines/users/{user_id}
```

PC1은 `source === "user"`이고 `face`, `body.body_front_full`, `body.body_right_full`, `body.body_left_full`이 있으면 baseline 완료로 처리할 수 있습니다.

## Exercise Session

### 1. Session 시작

```http
POST /api/sessions/start
Content-Type: application/json
```

요청:

```json
{
  "user_id": "profile_1",
  "mode": "exercise",
  "goal": "pushup"
}
```

지원 `goal`:

- `squat`
- `jumping_jack`
- `knee_raise`
- `lunge`
- `pushup`

응답:

```json
{
  "session_id": "sess_abc",
  "user_id": "profile_1",
  "mode": "exercise",
  "goal": "pushup",
  "status": "running",
  "ws_url": "ws://127.0.0.1:9000/ws/sessions/sess_abc"
}
```

### 2. WebSocket 연결

```text
WS /ws/sessions/{session_id}
```

PC3가 보내는 메시지:

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

### 3. Frame 분석

PC1은 운동 중 1-2초 간격으로 현재 frame을 보냅니다.

```http
POST /api/analyze/exercise
Content-Type: multipart/form-data
```

form field:

- `session_id`
- `file`

응답은 frame update만 포함합니다. 이 단계에서는 PC2 코칭을 호출하지 않습니다.

### 4. Session 종료

```http
POST /api/sessions/{session_id}/stop
```

이 시점에 PC3가 최종 exercise feature를 만들고, `MOCK_LLM=false`이면 PC2 `/api/coach/generate`를 호출합니다.

응답의 주요 field:

- `features.exercise.type`: session 시작 때 받은 `goal`
- `features.exercise.count`
- `features.exercise.state`
- `features.exercise.stability_score`
- `features.exercise.posture_errors`
- `features.exercise.measurement_quality`
- `features.exercise.measurement_confidence`
- `baseline_diff.exercise`
- `coaching.summary`
- `coaching.priority`
- `coaching.exercise_plan`
- `coaching.mirror_message`
- `coaching.pc2_payload`

## 주의

- PC1은 PC3에 원본 이미지를 업로드하지만, PC3는 baseline DB나 PC2 요청에 원본 이미지를 저장/전달하지 않습니다.
- 운동 중 실시간 feedback은 PC3가 담당합니다.
- 운동 종료 후 다음 운동 계획과 mirror message는 PC2 응답을 우선 사용합니다.
