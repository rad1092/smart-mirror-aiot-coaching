# PC1 연결 가이드

이 문서는 PC1 스마트미러 프론트 앱이 PC3 Vision Gateway와 연결할 때 필요한 흐름을 정리한 문서입니다.

PC1은 아직 이 저장소에 구현되어 있지 않습니다. PC1 담당자는 이 문서를 기준으로 Tauri + React + TypeScript 앱에서 PC3 REST API와 WebSocket을 호출하면 됩니다.

## 기본 연결 방향

PC1은 PC3만 호출합니다.

```text
PC1 스마트미러 앱
  -> PC3 REST API
  -> PC3 WebSocket

PC1은 PC2를 직접 호출하지 않음
```

PC2 LLM Coach API 호출은 PC3가 담당합니다. PC1은 PC2 endpoint, LLM 모델, RAG DB, prompt를 알 필요가 없습니다.

## 개발 환경 주소

PC1과 PC3가 같은 컴퓨터에서 실행될 때:

```text
PC3 REST base URL: http://127.0.0.1:9000
PC3 WebSocket:    ws://127.0.0.1:9000/ws/sessions/{session_id}
```

PC1이 다른 PC에서 실행되고 PC3가 LAN에 열려 있을 때:

```text
PC3 REST base URL: http://<PC3_LAN_IP>:9000
PC3 WebSocket:    ws://<PC3_LAN_IP>:9000/ws/sessions/{session_id}
```

PC3 `.env` 예시:

```env
HOST=0.0.0.0
WS_PUBLIC_HOST=<PC3_LAN_IP>
CORS_ALLOW_ORIGINS=http://localhost:1420,http://127.0.0.1:1420,tauri://localhost
```

인터넷 포트포워딩으로 PC3를 외부에 노출하지 마세요. 같은 LAN 안에서만 연결하는 것을 전제로 합니다.

## PC1 전체 흐름

운동 모드 기준:

1. PC1에서 사용자와 목적을 선택합니다.
2. `POST /api/sessions/start`를 호출합니다.
3. 응답의 `session_id`, `ws_url`을 저장합니다.
4. `ws_url`로 WebSocket을 연결합니다.
5. 웹캠 frame을 일정 주기로 `POST /api/analyze/exercise`에 업로드합니다.
6. WebSocket으로 `count`, `state`, `feedback`을 수신해 화면 카드에 표시합니다.
7. 사용자가 종료하면 `POST /api/sessions/{session_id}/stop`을 호출합니다.
8. stop 응답의 `coaching` JSON을 최종 결과 카드에 표시합니다.

grooming/outfit/outing 모드 기준:

1. `POST /api/sessions/start`를 호출합니다.
2. 이미지 1장을 각 analyze endpoint에 업로드합니다.
3. REST 응답의 `features`, `baseline_diff`, `environment`, `coaching`을 화면에 표시합니다.
4. 필요하면 `POST /api/sessions/{session_id}/stop`으로 session을 정리합니다.

## Session 시작

```http
POST /api/sessions/start
Content-Type: application/json
```

요청:

```json
{
  "user_id": "user_1",
  "mode": "exercise",
  "goal": "squat"
}
```

`mode` 값:

- `exercise`
- `grooming`
- `outfit`
- `outing`

응답:

```json
{
  "session_id": "sess_xxx",
  "user_id": "user_1",
  "mode": "exercise",
  "goal": "squat",
  "status": "running",
  "ws_url": "ws://127.0.0.1:9000/ws/sessions/sess_xxx"
}
```

PC1은 `session_id`와 `ws_url`을 화면 상태에 보관해야 합니다.

## 운동 WebSocket 연결

```text
ws://127.0.0.1:9000/ws/sessions/{session_id}
```

수신 메시지:

```json
{
  "type": "exercise_update",
  "session_id": "sess_xxx",
  "count": 8,
  "state": "down",
  "feedback": "무릎이 안쪽으로 모이지 않게 해주세요."
}
```

PC1 표시 권장:

- `count`: 큰 숫자 또는 운동 카운터
- `state`: `idle`, `up`, `down`
- `feedback`: 짧은 한글 안내 문구

WebSocket은 운동 실시간 업데이트 전용입니다. grooming/outfit/outing에는 WebSocket이 필수 아닙니다.

## 운동 frame 업로드

```http
POST /api/analyze/exercise
Content-Type: multipart/form-data
```

필드:

- `session_id`: session start에서 받은 값
- `file`: 웹캠 frame 이미지

응답:

```json
{
  "session_id": "sess_xxx",
  "type": "exercise_update",
  "exercise": {
    "type": "squat",
    "count": 8,
    "state": "down",
    "stability_score": 0.74,
    "posture_errors": ["knees_caving_in"]
  },
  "feedback": "무릎이 안쪽으로 모이지 않게 해주세요."
}
```

중요:

- 이 응답에는 `coaching`이 없습니다.
- PC3는 frame마다 PC2를 호출하지 않습니다.
- PC1은 frame upload 응답과 WebSocket 메시지 중 하나를 기준으로 실시간 UI를 갱신하면 됩니다.

## 운동 session 종료

```http
POST /api/sessions/{session_id}/stop
```

응답:

```json
{
  "session_id": "sess_xxx",
  "status": "stopped",
  "features": {
    "exercise": {
      "type": "squat",
      "count": 12,
      "state": "up",
      "stability_score": 0.78,
      "posture_errors": ["knees_caving_in"]
    },
    "face": null,
    "outfit": null
  },
  "baseline_diff": {
    "exercise": {
      "count_change": -3,
      "stability_change": -0.04
    }
  },
  "environment": {
    "temperature": 24.5,
    "humidity": 48,
    "illuminance": 360
  },
  "coaching": {
    "summary": "오늘은 자세 안정화에 집중하면 좋습니다.",
    "priority": "무릎 정렬 안정화",
    "routine": [
      {
        "title": "자세 조정",
        "description": "발끝과 무릎 방향을 맞추고 천천히 내려가세요."
      }
    ],
    "mirror_message": "오늘은 개수보다 자세를 안정적으로 잡는 데 집중하세요.",
    "warnings": ["통증이 있으면 운동을 중단하세요."]
  }
}
```

PC1은 `coaching.summary`, `coaching.priority`, `coaching.routine`, `coaching.mirror_message`, `coaching.warnings`를 카드 UI로 보여주면 됩니다.

## Grooming 분석

```http
POST /api/analyze/grooming
Content-Type: multipart/form-data
```

필드:

- `session_id`
- `file`: 얼굴 또는 상반신 이미지

응답에는 `features.face`, `baseline_diff.face`, `environment`, `coaching`이 포함됩니다.

PC1은 얼굴 관련 결과를 질병/피부 진단처럼 표현하지 말고, 밝기/붉은기/수염 그림자 같은 자기관리 feature로만 표시해야 합니다.

## Outfit 분석

```http
POST /api/analyze/outfit
Content-Type: multipart/form-data
```

필드:

- `session_id`
- `file`: 전신 또는 옷이 보이는 이미지
- `purpose`: 선택값. `interview`, `date`, `daily`, `casual`

응답에는 `features.outfit`, `environment`, `coaching`이 포함됩니다.

## Outing 분석

```http
POST /api/analyze/outing
Content-Type: multipart/form-data
```

필드:

- `session_id`
- `file`: 외출 전 거울 이미지
- `purpose`: `interview`, `date`, `daily`

PC3는 같은 이미지에서 face/outfit feature를 만들고 최신 sensor environment를 합쳐 coaching을 반환합니다.

## Sensor update

PC1 또는 센서 gateway는 주기적으로 환경값을 업데이트할 수 있습니다.

```http
POST /api/sensors/update
Content-Type: application/json
```

요청:

```json
{
  "temperature": 24.5,
  "humidity": 48,
  "illuminance": 360
}
```

## 사용자 baseline 생성

처음 실행 시 PC1은 사용자를 `user_1`, `user_2`처럼 만들고 baseline을 저장할 수 있습니다.

```http
POST /api/baselines/users/user_1
Content-Type: application/json
```

요청 예시:

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

PC3는 baseline 값만 저장합니다. 원본 얼굴 이미지, 운동 영상, 웹캠 frame은 저장하지 않습니다.

## 에러 처리

PC1에서 반드시 처리할 케이스:

- session이 없으면 `404`
- session mode와 analyze endpoint mode가 다르면 `400`
- 이미지 decode 실패 시 `400`
- WebSocket 연결이 끊기면 session은 유지되므로 재연결 가능
- PC2가 없으면 `MOCK_LLM=true` 기준 mock coaching 반환

## PC1이 지켜야 할 원칙

- PC1은 PC2를 직접 호출하지 않습니다.
- PC1은 PC3의 `ws_url`을 사용해 WebSocket에 연결합니다.
- PC1은 raw image를 PC2에 보내지 않습니다.
- PC1은 exercise frame upload를 너무 빠르게 보내지 않도록 조절합니다.
- PC1 화면 문구는 의학적 진단이나 외모 평가처럼 보이지 않게 표현합니다.
