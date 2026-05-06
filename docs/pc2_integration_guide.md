# PC2 연결 가이드

이 문서는 PC2 로컬 LLM Coach API 서버가 PC3 Vision Gateway와 연결될 때 필요한 endpoint, payload, 응답 규칙을 정리한 문서입니다.

PC2 서버는 이 저장소에 구현되어 있지 않습니다. PC2 담당자는 이 문서와 [pc2_prompt_contract.md](pc2_prompt_contract.md)를 기준으로 별도 서버를 구현하면 됩니다.

## 연결 방향

PC3가 PC2를 호출합니다.

```text
PC1 -> PC3 -> PC2
```

PC1은 PC2를 직접 호출하지 않습니다. PC2는 PC3에서 전달하는 `FeaturePayload`만 받아 coaching JSON을 생성합니다.

## PC2 endpoint

PC3 기본 설정:

```env
PC2_COACH_API_URL=http://localhost:8100/api/coach/generate
MOCK_LLM=true
```

PC2 실제 연결 시:

```env
MOCK_LLM=false
PC2_COACH_API_URL=http://<PC2_HOST>:8100/api/coach/generate
```

PC2가 제공해야 하는 API:

```http
POST /api/coach/generate
Content-Type: application/json
```

## 입력: FeaturePayload

PC2는 원본 이미지를 받지 않습니다. 입력은 반드시 `FeaturePayload` JSON 하나입니다.

예시:

```json
{
  "user_id": "user_1",
  "session_id": "sess_xxx",
  "mode": "exercise",
  "event": "session_completed",
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
  "purpose": null
}
```

금지 입력:

- raw image file
- base64 image
- frame path
- video path
- full landmark list
- segmentation mask
- camera stream URL

PC2 prompt는 “이미지를 직접 보지 않는다”는 전제로 작성해야 합니다.

## 출력: CoachingResponse

PC2는 반드시 `CoachingResponse` JSON만 반환합니다.

```json
{
  "summary": "오늘은 평소보다 스쿼트 횟수가 조금 줄었고, 무릎 정렬 오류가 감지되었습니다.",
  "priority": "무릎 정렬 안정화",
  "routine": [
    {
      "title": "자세 조정",
      "description": "발끝과 무릎 방향을 맞추고 천천히 내려가세요."
    }
  ],
  "mirror_message": "오늘은 개수보다 자세를 안정적으로 잡는 데 집중하세요.",
  "warnings": [
    "통증이 있으면 운동을 중단하세요."
  ]
}
```

반환하면 안 되는 것:

- Markdown 설명문
- JSON 밖의 자연어 문장
- 이미지 판독처럼 보이는 문장
- 입력에 없는 사실 추측
- 의학적 진단
- 외모 비하 또는 신체 평가

## PC2 호출 시점

PC3는 모든 frame마다 PC2를 호출하지 않습니다.

| mode | event | PC2 호출 여부 |
| --- | --- | --- |
| `exercise` | `frame_update` | 호출하지 않음 |
| `exercise` | `session_completed` | 호출 |
| `grooming` | `analysis_completed` | 호출 |
| `outfit` | `analysis_completed` | 호출 |
| `outing` | `analysis_completed` | 호출 |

운동 실시간 count/state/feedback은 PC3가 직접 처리합니다. PC2는 최종 요약과 루틴 제안만 담당합니다.

## Mode별 응답 방향

### exercise

사용 입력:

- `features.exercise.count`
- `features.exercise.stability_score`
- `features.exercise.posture_errors`
- `baseline_diff.exercise.count_change`
- `baseline_diff.exercise.stability_change`

응답 방향:

- 오늘 운동 요약
- 자세 오류 우선순위
- 다음 세트 또는 다음날 루틴
- 안전 문구

### grooming

사용 입력:

- `features.face.brightness`
- `features.face.redness`
- `features.face.beard_shadow`
- `baseline_diff.face`
- `environment.illuminance`

응답 방향:

- 조명 확인
- 세안/보습/정돈 같은 자기관리 루틴
- 수염 그림자 정리 제안

금지:

- 피부 질환 추정
- 염증/피로/건강 이상 판단
- 외모 평가

### outfit

사용 입력:

- `features.outfit.top_color`
- `features.outfit.bottom_color`
- `features.outfit.contrast_score`
- `features.outfit.tone`
- `purpose`
- `environment`

응답 방향:

- 색상 조합 요약
- 목적별 색상 균형 제안
- 조명/기온/습도에 따른 외출 전 확인

PC3가 스타일을 확정 분류하지 않으므로 PC2도 과도하게 단정하지 않습니다.

### outing

사용 입력:

- `features.face`
- `features.outfit`
- `baseline_diff.face`
- `environment`
- `purpose`

응답 방향:

- 외출 전 최종 체크
- 얼굴/그루밍 자기관리 확인
- 옷 색상 균형 확인
- 목적별 짧은 루틴

## PC2 최소 FastAPI 형태 예시

PC2 담당자가 구현할 wrapper 형태 예시입니다. 실제 vLLM/RAG 로직은 이 함수 내부에서 호출하면 됩니다.

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class CoachRequest(BaseModel):
    user_id: str
    session_id: str
    mode: str
    event: str
    features: dict
    baseline_diff: dict | None = None
    environment: dict | None = None
    purpose: str | None = None


@app.post("/api/coach/generate")
async def generate(payload: CoachRequest):
    return {
        "summary": "FeaturePayload를 기준으로 생성한 요약입니다.",
        "priority": "오늘의 우선순위",
        "routine": [
            {
                "title": "루틴 제목",
                "description": "루틴 설명"
            }
        ],
        "mirror_message": "스마트미러에 표시할 짧은 문장입니다.",
        "warnings": ["통증이나 불편감이 있으면 중단하세요."]
    }
```

## PC2 담당자가 지켜야 할 원칙

- PC2는 이미지를 직접 보지 않습니다.
- PC2는 PC3의 feature JSON만 신뢰합니다.
- PC2는 `CoachingResponse` 스키마만 반환합니다.
- PC2는 장문 설명을 JSON 밖에 붙이지 않습니다.
- PC2 RAG 지식은 PC2 쪽에 둡니다.
- PC3 저장소의 `docs/*_knowledge_example.md`는 PC2 RAG 지식 예시일 뿐, PC3 runtime에서 사용하지 않습니다.
