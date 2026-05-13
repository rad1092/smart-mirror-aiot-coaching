# PC2 연동 가이드

PC3는 운동 세션 종료 시점에만 PC2 운동 코칭 API를 호출합니다.

## Endpoint

```text
POST http://localhost:7000/api/coach/generate
```

PC3 설정:

```env
MOCK_LLM=false
PC2_COACH_API_URL=http://<PC2_HOST>:7000/api/coach/generate
```

PC2가 없거나 응답이 실패하면 PC3는 로컬 mock coaching으로 fallback합니다.

## 호출 조건

| mode | event | 호출 여부 |
| --- | --- | --- |
| `exercise` | `session_completed` | 호출 |
| `exercise` | frame update | 호출 안 함 |

PC3에는 더 이상 얼굴/옷/외출 분석 모드가 없습니다.

## Request Payload

PC3는 exercise 전용 JSON만 보냅니다.

```json
{
  "user_id": "profile_1",
  "session_id": "sess_abc",
  "mode": "exercise",
  "event": "session_completed",
  "features": {
    "exercise": {
      "type": "pushup",
      "count": 5,
      "state": "up",
      "stability_score": 0.72,
      "posture_errors": []
    }
  },
  "baseline_diff": {
    "exercise": {
      "count_change": -2,
      "stability_change": -0.1
    }
  },
  "environment": {
    "temperature": 24.5,
    "humidity": 48,
    "illuminance": 360
  }
}
```

지원 운동 타입:

- `squat`
- `jumping_jack`
- `knee_raise`
- `lunge`
- `pushup`

PC3는 PC2로 다음 값을 보내지 않습니다.

- 원본 이미지 파일
- base64 이미지
- frame path
- 영상 파일
- 전체 landmark 배열
- segmentation mask
- camera stream URL
- PC1 display-only target/classifier/measurement fields: `person_count`, `target_status`, `target_confidence`, `detected_type`, `exercise_confidence`, `goal_mismatch`, `measurement_quality`, `measurement_confidence`
- 얼굴/옷 feature
- 값이 `null`인 field

## Response Payload

PC2는 항상 JSON `CoachingResponse`를 반환해야 합니다.

```json
{
  "summary": "Plan generated from the final exercise session.",
  "priority": "posture stability",
  "exercise_plan": [
    {
      "exercise": "pushup",
      "sets": 3,
      "reps": 6,
      "duration_sec": null,
      "rest_sec": 60,
      "focus": "slow tempo",
      "reason": "Keep posture stable before increasing reps."
    }
  ],
  "mirror_message": "Slow down and keep posture stable.",
  "warnings": [],
  "pc2_payload": {
    "message": "Slow pushups first.",
    "display_lines": ["slow tempo", "stable posture"]
  }
}
```

PC3는 이 응답을 session stop 응답의 `coaching` field에 보존합니다.
