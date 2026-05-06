# PC2 Prompt Contract

이 문서는 PC3 Vision Gateway와 외부 PC2 Coach API 사이의 prompt/payload 계약입니다.

PC2 서버는 이 저장소에 구현하지 않습니다. PC3는 `.env`의 `PC2_COACH_API_URL`에 설정된 wrapper endpoint만 호출합니다.

## 입력 계약

PC2는 정확히 하나의 JSON 객체인 `FeaturePayload`만 입력으로 받습니다.

허용 입력:

- `user_id`
- `session_id`
- `mode`
- `event`
- `features`
- `baseline_diff`
- `environment`
- `purpose`

금지 입력:

- 원본 이미지 파일
- base64 이미지 문자열
- frame path 또는 local image path
- 영상 파일
- 전체 landmark list
- segmentation mask
- camera stream URL
- `FeaturePayload`에 표현되지 않은 숨은 시각 정보

PC2는 LLM이 이미지를 직접 보지 않는다고 가정해야 합니다. LLM은 PC3가 추출한 수치/상태 feature만 봅니다.

## 출력 계약

PC2는 `CoachingResponse` JSON 객체만 반환해야 합니다.

필수 구조:

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

JSON 밖에 Markdown, 설명문, 추가 자연어 문장을 붙이지 않습니다. 불필요한 top-level key도 추가하지 않습니다.

## 안전 규칙

PC2 모델은 다음을 하면 안 됩니다.

- 의학적 진단처럼 말하기
- 얼굴 feature로 피부 질환, 염증, 부상, 피로, 건강 상태 추정하기
- 외모 비하, 신체 비하, 점수 매기기
- `FeaturePayload`에 없는 사실 추측하기
- 원본 이미지를 봤다고 말하기
- 약물, 치료, 임상 조치 권하기

얼굴/그루밍 값은 자기관리 참고 신호일 뿐입니다. 의료적 근거가 아닙니다.

## mode별 응답 방향

### exercise

사용 데이터:

- `features.exercise`
- `baseline_diff.exercise`

응답 초점:

- 운동 기록
- 스쿼트 횟수
- stability score
- posture error ID
- baseline 대비 변화
- 다음 안전 루틴

PC3는 매 frame마다 PC2를 호출하지 않습니다. `exercise`에서는 `session_completed` 시점에만 PC2를 호출합니다.

`exercise` frame update는 PC3가 직접 처리합니다. PC3 내부에서 pose landmark를 사용할 수 있지만 landmark 전체 목록은 PC2로 보내지 않습니다.

### grooming

사용 데이터:

- `features.face`
- `baseline_diff.face`
- `environment.illuminance`

응답 초점:

- brightness diff
- redness ratio diff
- beard shadow ratio diff
- 조명 확인
- 간단한 자기관리 루틴

피부 질환, 염증, 피로, 건강 상태처럼 말하지 않습니다.

### outfit

사용 데이터:

- `features.outfit`
- `environment`
- `purpose`

응답 초점:

- 상의/하의 색상명
- contrast score
- 전체 tone
- 목적에 맞는 색상 균형
- 필요 시 조명/날씨 확인

PC3는 색상 feature만 만들기 때문에 PC2도 정밀한 스타일 판정처럼 단정하지 않습니다.

### outing

사용 데이터:

- `features.face`
- `features.outfit`
- `baseline_diff.face`
- `environment`
- `purpose`

응답 초점:

- 외출 전 최종 점검
- 얼굴/그루밍 자기관리 확인
- 옷 색상 균형
- 목적별 짧은 reminder
- 조명과 환경 확인

입력 payload에 없는 물건, 상황, 외모 상태를 추측하지 않습니다.

## Trigger 경계

PC3는 `exercise` frame update 중에는 PC2를 호출하지 않습니다.

PC2 coaching 생성 시점:

- `exercise`: session stop 후 `session_completed`
- `grooming`: 단발 분석 완료 후 `analysis_completed`
- `outfit`: 단발 분석 완료 후 `analysis_completed`
- `outing`: 단발 분석 완료 후 `analysis_completed`

## Prompt 작성 원칙

PC2 system prompt에는 최소한 다음 문장을 포함하는 것을 권장합니다.

```text
너는 스마트미러 자기관리 코칭 API다.
너는 이미지를 직접 보지 않는다.
입력은 PC3 Vision Gateway가 만든 FeaturePayload JSON뿐이다.
출력은 CoachingResponse JSON만 허용된다.
의학적 진단, 피부 질환 추정, 외모 비하, 입력에 없는 사실 추측을 하지 않는다.
```
