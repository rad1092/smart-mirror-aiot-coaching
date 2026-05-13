# PC2 Integration Guide

PC3 calls PC2 only through sanitized, contract-shaped payloads. PC2 does not
receive raw camera data or PC1 display-only fields.

## Endpoints

PC3 uses these PC2 endpoints:

```text
POST /api/routine/profile
POST /api/coach/generate
```

PC3 settings:

```env
MOCK_LLM=false
PC2_ROUTINE_API_URL=http://<PC2_HOST>:7000/api/routine/profile
PC2_COACH_API_URL=http://<PC2_HOST>:7000/api/coach/generate
```

If PC2 is unavailable, PC3 returns a local fallback response instead of failing
the PC1 flow.

## Pre-Exercise Routine Request

PC1 sends `RecommendationRequestPayload` to PC3. PC3 verifies the saved baseline
and sends PC2 a compact profile request:

```json
{
  "user_id": "profile_1",
  "user_goal": "lower body strength",
  "exercise_experience": "beginner",
  "available_days_per_week": 4,
  "restricted_body_parts": ["knee"],
  "purpose": "pre_exercise_routine",
  "profile_name": "Mirror User",
  "weight_kg": 70
}
```

Mapping rules:

- `goal` becomes a human-readable `user_goal`.
- `weekly_frequency` maps as `once_twice=2`, `three_four=4`, `five_plus=5`.
- `limitations` only allows `knee`, `back`, `shoulder`, and `ankle`.
- Raw images, baseline slot data, PC1 UI-only fields, and null fields are not
  sent.

## Pre-Exercise Routine Response

PC2 should return a `RoutineProfileResponse` with a weekly routine. PC3 flattens
the first valid exercises into PC1 `RecommendationResponsePayload.items`.

Example PC2 response:

```json
{
  "summary": "Weekly lower-body routine generated.",
  "weekly_focus": "Build stable knee and hip control.",
  "weekly_routine": [
    {
      "day_label": "Day 1",
      "focus": "lower body control",
      "exercises": [
        {
          "exercise": "squat",
          "sets": 2,
          "reps": 8,
          "duration_sec": null,
          "rest_sec": 60,
          "focus": "slow tempo",
          "reason": "Practice stable knee tracking."
        }
      ]
    }
  ],
  "cautions": ["Stop if knee pain appears."]
}
```

## Post-Exercise Coaching Request

PC3 calls coaching only for completed exercise sessions:

| mode | event | PC2 call |
| --- | --- | --- |
| `exercise` | `session_completed` | yes |
| `exercise` | frame update | no |

Request:

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

Supported exercise types:

- `squat`
- `jumping_jack`
- `knee_raise`
- `lunge`
- `pushup`

PC3 strips fields that PC2 does not allow, including target tracking,
classifier, measurement quality, image, video, full landmarks, segmentation, and
null fields.

## Post-Exercise Coaching Response

PC2 should return `CoachingResponse` JSON:

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

PC3 preserves this response under the session stop `coaching` field for PC1.
