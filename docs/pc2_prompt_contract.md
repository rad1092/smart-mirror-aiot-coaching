# PC2 Prompt Contract

This document defines the prompt and payload contract between PC3 Vision Gateway and the external PC2 Coach API.

PC2 is not implemented in this repository. PC3 calls only the wrapper endpoint configured by `PC2_COACH_API_URL`.

## Input Contract

PC2 receives exactly one JSON object: `FeaturePayload`.

Allowed input:

- `user_id`
- `session_id`
- `mode`
- `event`
- `features`
- `baseline_diff`
- `environment`
- `purpose`

Forbidden input:

- Raw image files
- Base64 image strings
- Frame paths or local image paths
- Video files
- Full landmark lists
- Segmentation masks
- Camera stream URLs
- Any hidden visual context not represented in `FeaturePayload`

PC2 must assume that the LLM never sees the image. It sees only numeric and symbolic feature values extracted by PC3.

## Output Contract

PC2 must return only a `CoachingResponse` JSON object.

Required shape:

```json
{
  "summary": "string",
  "priority": "string",
  "routine": [
    {
      "title": "string",
      "description": "string"
    }
  ],
  "mirror_message": "string",
  "warnings": ["string"]
}
```

No markdown, no prose outside JSON, and no extra top-level keys should be returned.

## Safety Rules

The model must not:

- Claim to diagnose a medical condition.
- Infer skin disease, inflammation, injury, fatigue, or health status from the face features.
- Insult, shame, or rank the user's appearance.
- Insult or shame the user's body.
- Guess facts that are not present in `FeaturePayload`.
- Pretend that it saw the raw image.
- Recommend medication, treatment, or clinical action.

Face and grooming values are self-management signals only. They are not medical evidence.

## Mode Guidance

### exercise

Use `features.exercise` and `baseline_diff.exercise`.

Focus on:

- Exercise record
- Squat count
- Stability score
- Posture error IDs
- Baseline diff
- Safe next routine

Do not call PC2 for every frame. PC3 calls this mode only on `session_completed`.

`exercise` frame updates are handled inside PC3 and must not trigger PC2. PC3 may use pose landmarks internally, but landmark lists must not be sent to PC2.

### grooming

Use `features.face` and `baseline_diff.face`.

Focus on:

- Brightness diff
- Redness ratio diff as a neutral visual feature
- Beard shadow ratio diff
- Simple self-management routine
- Lighting and grooming check

Do not describe medical conditions, skin disease, inflammation, fatigue, or health status.

### outfit

Use `features.outfit`, `environment`, and optional `purpose`.

Focus on:

- Top and bottom color names
- Contrast score
- Overall tone
- Purpose-aware color balance suggestion
- Environment-aware check when useful

Do not claim precise style judgment beyond the extracted color features.

### outing

Use `features.face`, `features.outfit`, `baseline_diff.face`, `environment`, and `purpose`.

Focus on:

- Final check before going out
- Face feature self-management check
- Outfit color balance
- Purpose-specific reminders
- Environment and lighting reminders

Do not infer unseen items or context outside the payload.

## Trigger Boundary

PC3 must not call PC2 during `exercise` frame updates. PC2 coaching is generated only at session stop for exercise, or after a completed one-shot analysis for grooming, outfit, and outing.
