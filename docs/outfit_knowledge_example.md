# PC2용 옷 색상/스타일 지식 예시

이 문서는 나중에 PC2 RAG/knowledge_base에 넣을 수 있는 코디 지식 예시입니다.

PC3 runtime은 이 문서를 사용하지 않습니다. PC3는 `top_color`, `bottom_color`, `contrast_score`, `tone` 같은 feature만 추출합니다.

## color_combination_rules

- navy는 white, gray, beige와 잘 어울립니다.
- black은 white, gray, beige와 잘 어울리지만 navy와 함께 쓰면 전체가 어두워 보일 수 있습니다.
- beige는 navy, brown, white와 부드럽게 어울립니다.
- gray는 black, navy, white, green 사이에서 중립적인 연결 색으로 사용할 수 있습니다.
- brown은 beige, white, muted green과 자연스럽게 어울립니다.

## purpose_style_rules

### interview

권장 색상:

- navy
- gray
- white
- black
- beige

방향:

- 단정하고 신뢰감 있는 인상을 우선합니다.
- 강한 포인트 색보다 차분한 대비를 권장합니다.
- 지나치게 화려하거나 시선을 분산시키는 조합은 피합니다.

### date

권장 색상:

- white
- beige
- light_blue
- brown
- navy

방향:

- 부드럽고 자연스러운 인상을 우선합니다.
- 전체가 어두우면 한 가지 밝은 요소를 추가할 수 있습니다.

### daily

권장 색상:

- gray
- black
- white
- navy
- green

방향:

- 편안함과 활동성을 우선합니다.
- 움직이기 쉽고 과하게 복잡하지 않은 조합을 권장합니다.

## style_categories

PC2 RAG에서 참고할 수 있는 style category 예시입니다.

- formal
- business_casual
- casual
- sporty

PC3는 이 category를 확정 분류하지 않습니다.

## weather_outfit_rules

- 습도가 높으면 두껍고 어두운 tone보다 가볍고 밝은 조합을 제안할 수 있습니다.
- 기온이 낮으면 어두운 tone과 layering을 제안할 수 있습니다.
- 조도가 낮으면 더 밝은 조명에서 옷 색상을 다시 확인하라고 안내할 수 있습니다.

## 경계

PC3는 이 지식을 직접 사용해 긴 코디 조언을 만들지 않습니다. PC2가 PC3의 `FeaturePayload`를 받은 뒤 RAG 지식으로 참고할 수 있습니다.
