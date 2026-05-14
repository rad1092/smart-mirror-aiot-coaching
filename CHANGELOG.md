# 변경 이력

## 2026-05-14 16:03:12 +09:00 - 이번 변경 - 라이브 운동 5종 검증과 720p 프레임 계약

주요 변경:

- 실제 ABKO 웹캠 기준으로 `squat`, `jumping_jack`, `knee_raise`, `pushup`, `lunge` 5종의 count 증가를 확인했다.
- `knee_raise`는 `up -> idle -> up` 흔들림으로 같은 반복이 두 번 세지지 않도록 전용 hysteresis를 적용했다.
- 같은 세션의 `/api/analyze/exercise` 요청을 session lock으로 직렬 처리해 HTTP 응답 count와 WebSocket count가 어긋나지 않게 했다.
- PC1 운동 프레임 권장 해상도를 `1280x720` JPEG로 명시했다. 최소 fallback은 `960x540`으로 본다.
- `multi_person_detected`도 운동 중 count 증가를 막는 blocking 상태로 기록한다.

검증:

- `uv run --with-requirements requirements.txt python -m pytest -q`
  - `76 passed`
- 라이브 확인:
  - `squat`: count 증가 확인
  - `jumping_jack`: count `12`까지 증가 확인
  - `knee_raise`: HTTP/WS count `15/15`, gap `0`, `+2` 튐 없음
  - `pushup`: HTTP/WS count `4/4`, gap `0`, `+2` 튐 없음
  - `lunge`: HTTP/WS count `7/7`, left/right `4/3`, gap `0`, `+2` 튐 없음

주의:

- `pushup`, `lunge`는 카메라 위치가 나쁘면 후반에 `target_lost`가 뜰 수 있다.
- `lunge`의 `detected_type`은 아직 `squat`으로 오판하는 경우가 있어, 선택 운동 `goal` 기준 카운트 로직을 우선 사용한다.

이 문서는 `main` 브랜치의 Git 기록을 기준으로 정리한 PC3 변경 이력입니다.

## 현재 버전 기준

- 현재 브랜치: `main`
- 원격 저장소: `origin=https://github.com/rad1092/smart-mirror-aiot-coaching.git`
- 현재 HEAD: 이번 작업 커밋 기준
- 원격 `origin/main`: `662297c`
- Git tag: 없음
- 문서 갱신 시각: `2026-05-14 13:50:34 +09:00`

현재 저장소에는 별도 tag가 없으므로, 아래 주요 커밋들을 실질적인 버전 경계로 봅니다.

## 2026-05-14 13:50:34 +09:00 - 이번 커밋 - 운동별 프레임 업로드 주기 계약 보강

주요 변경:

- PC1 실시간 프레임 업로드 주기를 운동별로 명시.
- `squat`, `pushup`, `lunge`는 300ms 간격 권장.
- `knee_raise`, `jumping_jack`은 200ms 간격 권장.
- 이전 `/api/analyze/exercise` 요청이 끝나지 않았으면 다음 프레임은 skip해야 한다는 조건을 명시.
- 고정 `setInterval`보다 요청 완료 후 150-300ms 뒤 다음 프레임을 보내는 adaptive loop를 권장.

검증:

- 문서 계약 변경만 있음. 런타임 테스트는 생략.

## 2026-05-14 13:46:25 +09:00 - 이번 커밋 - 사용자 추적 안정화와 실시간 프레임 계약 명확화

주요 변경:

- 첫 유효 pose로 target을 고정한 뒤 짧은 인식 끊김은 `target_recovering`으로 처리.
- `TARGET_LOST_GRACE_FRAMES=8` 설정을 추가해 grace 구간 동안 count와 rep phase를 보존.
- grace 초과 시에만 `target_lost`로 전환하고, 다른 사람이 들어와도 target을 자동 교체하지 않도록 추적 signature와 match 기준을 보강.
- `model_disagreement`는 1프레임 즉시 차단하지 않고 연속 불일치일 때 count 차단.
- 운동별 body height와 confident landmark ratio threshold를 완화.
- PC1에 노출되는 feedback, baseline reason, fallback, coaching 문구를 자연스러운 한국어로 정리.
- PC1 실시간 계약에 `/api/analyze/exercise`를 300-500ms 간격으로 반복 호출해야 한다는 조건을 명시.

검증:

- `uv run --with-requirements requirements.txt python -m pytest -q`
  - `74 passed`

## 2026-05-13 16:43:52 +09:00 - 이번 커밋 - baseline 문구 단순화

주요 변경:

- README와 PC1 연동 문서의 baseline 설명을 필수 항목 두 개만 남기는 방식으로 단순화.
- PC3 baseline 완료 기준은 `face_front`, `body_front_full` 두 개로 유지.
- 별도 예외 처리 설명이나 과거 항목 안내 문구를 제거.

검증:

- `uv run --with-requirements requirements.txt python -m pytest -q`

## 2026-05-13 16:33:56 +09:00 - 이번 커밋 - PC3 baseline 슬롯을 2개로 축소

주요 변경:

- PC3 baseline capture API의 기준 슬롯을 두 개로 정리.
- 허용 baseline 슬롯을 `face_front`, `body_front_full`로 고정.
- 루틴 추천 전 baseline 검증도 `face_front`, `body_front_full`만 요구하도록 정리.
- PC1 연동 문서와 README의 baseline 안내를 같은 기준으로 정리.

검증:

- `uv run --with-requirements requirements.txt python -m pytest -q`

## 2026-05-13 14:17:01 +09:00 - 이번 커밋 - 얼굴 baseline을 프로필 사진용 얼굴 검출로 단순화

주요 변경:

- PC3 `face_front` baseline을 신원 인증/얼굴 분석이 아니라 프로필 사진용 정면 얼굴 체크로 정리.
- 기존 단순 밝기 체크 대신 OpenCV frontal face detector로 얼굴이 하나 이상 보일 때만 `face_front` 저장.
- 저장되는 face baseline에는 `captured`, `brightness`, `face_detected`, `face_count`만 남김.
- body baseline 3슬롯은 기존처럼 MediaPipe pose/full-body 검증 유지.
- PC2 요청에는 얼굴 feature를 보내지 않는 기존 exercise-only 정책 유지.
- README와 PC1 연동 문서에 `face_front`의 의미를 명확히 설명.

검증:

- `uv run --with-requirements requirements.txt python -m pytest tests/test_baseline_api.py tests/test_routines_api.py -q`
  - `19 passed`
- `uv run --with-requirements requirements.txt python -m pytest -q`
  - `74 passed`

## 2026-05-13 12:01:47 +09:00 - 60dd82a - 변경 이력/흐름 문서와 SKILL 규칙 추가

주요 변경:

- 저장소 루트에 `CHANGELOG.md` 추가.
- 저장소 루트에 `FLOW_CHANGES.md` 추가.
- 저장소 루트에 `SKILL.md` 추가.
- 커밋/푸시 전에는 `CHANGELOG.md`와 `FLOW_CHANGES.md`를 만들거나 갱신한다는 최소 규칙을 남김.
- 런타임 코드 변경은 없음.

## 2026-05-13 11:31:01 +09:00 - 3f418a8 - PC2 스케줄 루틴 계약 정렬

현재 최신 원격 기준입니다.

주요 변경:

- PC3 루틴 중계를 최신 PC2 스케줄 루틴 계약에 맞춤.
- 기존 PC1 nested `RecommendationRequestPayload` 호환성 유지.
- PC2 문서에 나온 flat routine request도 PC3에서 받을 수 있게 확장.
- `start_date`를 PC2 루틴 생성 요청에 전달.
- PC2 응답의 스케줄/상세 루틴 메타데이터 보존:
  - `routine_id`
  - `start_date`
  - `scheduled_dates`
  - `weekly_routine`
  - `how_to`
  - `tips`
- 날짜별 루틴 조회 API 추가:
  - `GET /api/routines/profile/{user_id}/day?target_date=YYYY-MM-DD`
- `PC2_ROUTINE_DAY_API_URL` 설정 추가.
- PC1/PC2 연동 문서와 PC2 prompt contract 문서 갱신.
- 구현 시점 검증:
  - `72 passed`

## 2026-05-13 10:19:43 +09:00 - 8d13a2d - PC3를 통한 PC2 운동 전 루틴 플랜 중계

주요 변경:

- `POST /api/routines/profile` 추가.
- PC1의 루틴 추천 payload를 PC3가 받기 시작.
- PC3가 profile 필수값과 저장된 baseline 완료 여부를 확인한 뒤 PC2 호출.
- `PC2_ROUTINE_API_URL` 추가.
- PC2 루틴 생성 요청을 strict하게 정제.
- PC2가 없거나 실패하면 PC1이 렌더 가능한 `source="basic"` fallback 반환.
- 루틴 API 테스트 추가.

## 2026-05-13 10:06:46 +09:00 - 4f41f37 - Dual MediaPipe 측정 품질 가드 추가

주요 변경:

- Lite + Full dual MediaPipe 측정 파이프라인 도입.
- 세션 단위 측정 품질 카운터와 PC2 호출 보호 로직 추가.
- 측정 품질이 낮으면 PC2 코칭을 호출하지 않고 PC3 local feedback 반환.
- baseline body slot 검증을 full-body visibility/quality 기준으로 강화.
- `model_disagreement`, `fast_only`, `dual_verified`, `blocked` 계열 품질 상태 처리.

## 2026-05-13 09:46:00 +09:00 - b54a021 - 기본 pose 모델 variant를 full로 변경

주요 변경:

- 기본 pose model variant를 `full`로 변경.
- dual pipeline에서는 Lite를 빠른 tracking 용도로 계속 사용.

## 2026-05-13 09:35:39 +09:00 - 5743931 - Target tracking과 운동 분류기 추가

주요 변경:

- 세션 시작 후 첫 유효 사람을 target user로 lock하는 추적 방식 추가.
- 여러 사람이 들어올 때 target 전환을 막는 continuity 기반 선택 로직 추가.
- PC1 표시용 target/classifier 필드 추가:
  - `person_count`
  - `target_status`
  - `target_confidence`
  - `detected_type`
  - `exercise_confidence`
  - `goal_mismatch`
- MediaPipe Full 모델 추가:
  - `models/pose/pose_landmarker_full.task`
- 경량 운동 분류기 메타데이터 추가:
  - `models/exercise_classifier/exercise_classifier.json`

## 2026-05-12 17:16:19 +09:00 - a86d0b4 - Pose Landmarker Lite 모델 파일 포함

주요 변경:

- 실제 런타임에 필요한 모델 파일을 저장소에 포함:
  - `models/pose/pose_landmarker_lite.task`
- `models/.gitignore`에 필요한 `.task` 파일 예외 추가.
- 모델 문서 갱신.

## 2026-05-12 14:41:22 +09:00 - 041cbeb - 운동 자세 분석 확장 및 안정화

주요 변경:

- 기존 squat 중심 분석에서 공통 운동 5종으로 확장:
  - `squat`
  - `pushup`
  - `lunge`
  - `knee_raise`
  - `jumping_jack`
- 운동별 state/count/posture error/stability score 계산 추가.
- 반복 카운트 안정화를 위한 상태 전환 로직 강화.
- `config/exercise_thresholds.json`, `data/exercise_rules.json` 갱신.
- pose analyzer 테스트 대폭 추가.

## 2026-05-12 09:58:15 +09:00 - a4a99b0 - PC3 exercise-only 범위 정리

주요 변경:

- PC3에서 운동 외 기능 제거.
- 제거된 기능:
  - face analysis
  - outfit/color analysis
  - grooming 관련 문서
  - segmentation placeholder
- PC3 역할을 baseline, pose analysis, session, WebSocket, PC2 exercise coaching으로 축소.
- PC2 payload도 exercise-only 범위로 축소.

## 2026-05-12 09:28:29 +09:00 - df07a8f - PC1/PC2 운동 계약 정렬

주요 변경:

- PC1 baseline capture 호환 API 추가.
- PC2 strict exercise payload filtering 추가.
- PC1 realtime 화면용 필드 추가:
  - `posture_errors`
  - `stability_score`
- PC1/PC2 공통 운동 타입으로 session goal 정규화:
  - `squat`
  - `jumping_jack`
  - `knee_raise`
  - `lunge`
  - `pushup`
- PC2 payload 직렬화와 session stop 응답 테스트 추가.

## 초기 구성

초기 주요 커밋:

- `2026-05-07 10:08:05 +09:00` - `3d718a1`: 이전 `pc1` 디렉터리 제거.
- `2026-05-06 18:00:17 +09:00` - `1444f10`: PC1 통합 branch merge.
- `2026-05-06 17:52:52 +09:00` - `5291395`: `pc1` subtree merge.
- `2026-05-06 17:52:52 +09:00` - `d1d8b0a`: `pc1/` content squash.
- `2026-05-06 16:54:30 +09:00` - `cd69936`: 문서 번역 및 연동 가이드 추가.
- `2026-05-06 16:42:44 +09:00` - `1dfb0fb`: 공유 프로젝트 저장소 역할 정리.
- `2026-05-06 16:20:17 +09:00` - `bdf1634`: 초기 PC3 Vision Gateway 구현.
