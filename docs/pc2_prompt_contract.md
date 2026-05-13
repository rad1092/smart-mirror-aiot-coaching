# PC2 Prompt and Payload Contract

This document defines what PC2 receives from PC3 and what PC2 should return.
PC2 should behave as a JSON API, not as a free-form chat endpoint.

## General Rules

PC2 does not see raw images. It should use only the sanitized profile, exercise
feature, baseline diff, environment, and purpose fields supplied by PC3.

Allowed request data:

- `user_id`
- `session_id`
- `mode`
- `event`
- `features.exercise`
- `baseline_diff.exercise`
- `environment`
- `purpose`
- sanitized routine profile fields

Forbidden request data:

- raw image files
- base64 image strings
- frame paths
- video files
- full landmark lists
- segmentation masks
- camera stream URLs
- PC1 display-only target/classifier/measurement fields
- unknown extra fields
- null fields

## Routine Profile Request

PC3 sends this to `POST /api/routine/profile` before exercise:

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

PC2 should return a routine profile response with `summary`, `weekly_focus`,
`weekly_routine`, and optional `cautions`. PC3 will flatten the weekly routine
into PC1 recommendation items.

## Exercise Feature Request

PC3 sends this to `POST /api/coach/generate` after a completed exercise session:

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
  "purpose": "post-exercise coaching"
}
```

Supported exercise types:

- `squat`
- `jumping_jack`
- `knee_raise`
- `lunge`
- `pushup`

## Coaching Response

PC2 should return JSON only. Do not wrap the response in markdown, code fences,
or natural-language prefaces.

```json
{
  "summary": "Create the next exercise plan from posture stability and rep count.",
  "priority": "posture stability",
  "exercise_plan": [
    {
      "exercise": "squat",
      "sets": 3,
      "reps": 6,
      "duration_sec": null,
      "rest_sec": 60,
      "focus": "slow tempo",
      "reason": "Stable knee tracking matters more than adding reps."
    }
  ],
  "mirror_message": "Slow down and keep posture stable.",
  "warnings": [],
  "pc2_payload": {
    "message": "Prioritize stable posture before adding reps.",
    "display_lines": ["stable posture", "slow tempo"]
  }
}
```

## Prompt Safety Rules

PC2 prompts should include at least these rules:

```text
You are an exercise planning API for a smart mirror.
You do not see raw images.
Use only the sanitized profile, exercise features, baseline diff, environment, and retrieved exercise knowledge.
Do not infer facts that are not present in the input.
Do not give medical diagnosis or treatment advice.
Return only valid JSON for the expected response schema.
```

## Fallback Rules

If an LLM call fails or returns plain text, PC2 should wrap the fallback into the
expected JSON response shape. PC3 also has local fallback responses when PC2 is
unavailable.
