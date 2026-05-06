# Grooming Knowledge Example for PC2

This document is an example knowledge source for a future PC2 RAG/knowledge_base.

PC3 does not use this document at runtime. PC3 only extracts numeric face features such as `brightness`, `redness`, and `beard_shadow`.

## low_brightness

Allowed guidance:

- The lighting may be low, so check once more under brighter light.
- Consider a simple wash, moisturizer, and grooming check routine.

## high_redness

Allowed guidance:

- Say only that the red tone feature is stronger than usual.
- Suggest using gentler grooming steps or checking under neutral light.

Forbidden guidance:

- Do not call it inflammation.
- Do not infer a skin disease.
- Do not infer health status.

## high_beard_shadow

Allowed guidance:

- If beard shadow is stronger than usual, suggest shaving or cleaning up the jawline.
- For interview or presentation purposes, focus on a neat impression.

## Forbidden Expressions

- Your skin is bad.
- A disease is suspected.
- This is inflammation.
- Your health condition looks poor.
- Any insult or appearance-based shaming.

## Boundary

PC3 must not directly use these rules to produce long grooming advice. PC2 can retrieve this knowledge after receiving PC3's `FeaturePayload`.
