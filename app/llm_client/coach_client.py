from __future__ import annotations

import logging

import httpx

from app.config import Settings
from app.schemas.coaching import CoachingResponse, RoutineItem
from app.schemas.feature import FeaturePayload


logger = logging.getLogger(__name__)


class CoachClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def generate(self, payload: FeaturePayload) -> CoachingResponse:
        if self._settings.mock_llm:
            return self._mock_response(payload)

        try:
            async with httpx.AsyncClient(timeout=self._settings.pc2_timeout_seconds) as client:
                response = await client.post(
                    self._settings.pc2_coach_api_url,
                    json=payload.model_dump(mode="json"),
                )
                response.raise_for_status()
            return CoachingResponse.model_validate(response.json())
        except Exception:
            logger.exception("PC2 Coach API call failed. Falling back to mock coaching.")
            return self._mock_response(payload)

    def _mock_response(self, payload: FeaturePayload) -> CoachingResponse:
        mode = payload.mode
        if mode == "exercise":
            exercise = payload.features.exercise
            count = exercise.count if exercise else 0
            return CoachingResponse(
                summary=f"스쿼트 {count}회를 기록했고 자세 안정도를 기준으로 마무리 피드백을 제공합니다.",
                priority="자세 안정화",
                routine=[
                    RoutineItem(
                        title="무릎 정렬 확인",
                        description="발끝과 무릎 방향을 맞추고 천천히 내려갔다 올라오세요.",
                    )
                ],
                mirror_message="오늘은 개수보다 안정적인 자세에 집중하세요.",
                warnings=["통증이 있으면 운동을 중단하세요."],
            )
        if mode == "grooming":
            return CoachingResponse(
                summary="얼굴 밝기, 붉은기, 수염 그림자 수치를 기준으로 그루밍 체크를 완료했습니다.",
                priority="정돈감 개선",
                routine=[
                    RoutineItem(
                        title="조명과 정돈 확인",
                        description="거울 앞 조명을 고르게 맞추고 수염 그림자가 진한 부분을 확인하세요.",
                    )
                ],
                mirror_message="진단이 아니라 오늘 화면 기준의 정돈 체크입니다.",
                warnings=["자극이 느껴지면 사용 중인 제품이나 면도 방식을 조정하세요."],
            )
        if mode == "outfit":
            return CoachingResponse(
                summary="상의와 하의 대표 색상, 대비, 전체 톤을 기준으로 조합을 확인했습니다.",
                priority="색상 균형",
                routine=[
                    RoutineItem(
                        title="톤 균형 맞추기",
                        description="상의와 하의 대비가 강하면 신발이나 가방 색을 중간 톤으로 맞춰 보세요.",
                    )
                ],
                mirror_message="현재 색상 조합은 단순 대표색 기준으로 평가되었습니다.",
                warnings=["중요한 일정에는 실제 조명 아래에서 한 번 더 확인하세요."],
            )
        return CoachingResponse(
            summary="얼굴, 옷 색상, 실내 환경 수치를 함께 보고 외출 전 점검을 완료했습니다.",
            priority="목적별 최종 점검",
            routine=[
                RoutineItem(
                    title="외출 전 확인",
                    description="옷 색상 조합과 조명 상태를 확인하고 목적에 맞게 한 가지 포인트만 조정하세요.",
                )
            ],
            mirror_message="입력된 feature 기준으로 외출 전 체크를 마쳤습니다.",
            warnings=["입력 이미지에 보이지 않는 내용은 판단하지 않았습니다."],
        )
