# PC2 Prompt/Payload Contract

이 문서는 PC2가 PC3에서 받는 입력과 PC3로 돌려줘야 하는 출력 형식을 정의합니다.

## 입력 원칙

PC2는 이미지 모델이 아닙니다. PC2는 PC3가 계산한 운동 feature, baseline diff, environment, purpose만 사용합니다.

허용 입력:

- `user_id`
- `session_id`
- `mode`
- `event`
- `features.exercise`
- `baseline_diff.exercise`
- `environment`
- `purpose`

금지 입력:

- 원본 이미지
- base64 이미지 문자열
- frame path
- 영상 파일
- 전체 landmark list
- segmentation mask
- camera stream URL
- PC1 display-only target/classifier fields: `person_count`, `target_status`, `target_confidence`, `detected_type`, `exercise_confidence`, `goal_mismatch`
- 계약에 없는 field

## FeaturePayload

PC2가 받는 요청은 `mode="exercise"`와 `event="session_completed"`일 때만 유효합니다.

```json
{
  "user_id": "profile_1",
  "session_id": "sess_abc",
  "mode": "exercise",
  "event": "session_completed",
  "features": {
    "exercise": {
      "type": "squat",
      "count": 8,
      "state": "down",
      "stability_score": 0.64,
      "posture_errors": ["knees_caving_in"]
    }
  },
  "baseline_diff": {
    "exercise": {
      "count_change": -3,
      "stability_change": -0.05
    }
  },
  "environment": {
    "temperature": 24.5,
    "humidity": 48,
    "illuminance": 360
  },
  "purpose": "다음 운동 계획 생성"
}
```

지원 운동 타입:

- `squat`
- `jumping_jack`
- `knee_raise`
- `lunge`
- `pushup`

PC2는 `count`와 `rep_count` 중 하나 이상을 사용할 수 있게 설계되어도 좋지만, 현재 PC3는 기본적으로 `count`를 보냅니다.

## CoachingResponse

PC2는 JSON 객체만 반환합니다. Markdown 설명, 코드블록, 자연어 wrapper를 붙이지 않습니다.

```json
{
  "summary": "현재 자세 안정성과 반복 횟수를 기준으로 다음 운동 계획을 만들었습니다.",
  "priority": "posture stability",
  "exercise_plan": [
    {
      "exercise": "tempo squat",
      "sets": 3,
      "reps": 6,
      "duration_sec": null,
      "rest_sec": 60,
      "focus": "slow tempo",
      "reason": "무릎 정렬을 안정화한 뒤 반복 횟수를 늘리는 편이 안전합니다."
    }
  ],
  "mirror_message": "속도를 낮추고 자세를 먼저 안정화하세요.",
  "warnings": [],
  "pc2_payload": {
    "message": "자세 안정화 먼저, 반복 횟수는 천천히 늘리세요.",
    "display_lines": ["slow tempo", "stable posture"]
  }
}
```

## Prompt 안전 규칙

PC2 prompt에는 최소한 다음 규칙이 들어가야 합니다.

```text
You are an exercise planning API for a smart mirror.
You do not see raw images.
Use only the exercise features, baseline diff, saved baseline profile, environment, and retrieved exercise knowledge.
Do not infer facts that are not present in the input.
Do not give medical diagnosis or treatment advice.
Return only valid CoachingResponse JSON.
```

## Fallback 규칙

LLM 호출이 실패하거나 plain text만 생성해도 PC2 서버는 raw text를 그대로 반환하지 않습니다. 서버가 최소 `CoachingResponse` JSON으로 감싸서 반환해야 합니다.

fallback 예시:

```json
{
  "summary": "자세 안정화를 우선으로 다음 세트를 진행하세요.",
  "priority": "posture stability",
  "exercise_plan": [],
  "mirror_message": "자세 안정화를 우선으로 다음 세트를 진행하세요.",
  "warnings": ["LLM fallback response was used."],
  "pc2_payload": {
    "message": "자세 안정화를 우선으로 다음 세트를 진행하세요.",
    "display_lines": ["자세 안정화", "천천히 진행"]
  }
}
```

PC3도 PC2 호출 실패 시 같은 구조의 로컬 fallback을 반환합니다.
