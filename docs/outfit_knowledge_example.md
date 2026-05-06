# Outfit Knowledge Example for PC2

This document is an example knowledge source for a future PC2 RAG/knowledge_base.

PC3 does not use this document at runtime. PC3 only extracts outfit features such as `top_color`, `bottom_color`, `contrast_score`, and `tone`.

## color_combination_rules

- Navy pairs well with white, gray, and beige.
- Black pairs well with white, gray, and beige, but black with navy can make the whole outfit look very dark.
- Beige pairs softly with navy, brown, and white.
- Gray works as a neutral bridge color for black, navy, white, and green.
- Brown pairs naturally with beige, white, and muted green.

## purpose_style_rules

### interview

Recommended colors:

- navy
- gray
- white
- black
- beige

Direction:

- Keep the outfit neat and reliable.
- Prefer calm contrast over strong accent colors.
- Avoid overly bright or distracting combinations.

### date

Recommended colors:

- white
- beige
- light_blue
- brown
- navy

Direction:

- Keep the impression soft and natural.
- Use one gentle bright element if the rest of the outfit is dark.

### daily

Recommended colors:

- gray
- black
- white
- navy
- green

Direction:

- Keep comfort and activity in mind.
- Prefer simple combinations that are easy to move in.

## style_categories

- formal
- business_casual
- casual
- sporty

## weather_outfit_rules

- When humidity is high, prefer lighter and brighter combinations over thick dark tones.
- When temperature is low, darker tones and layering can be suggested.
- When illuminance is low, recommend checking the outfit once more under brighter light.

## Boundary

PC3 must not directly use these rules to produce long outfit advice. PC2 can retrieve this knowledge after receiving PC3's `FeaturePayload`.
