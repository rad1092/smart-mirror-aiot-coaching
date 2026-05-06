from __future__ import annotations

from fastapi import APIRouter, Depends

from app.baseline.baseline_service import BaselineService
from app.dependencies import get_baseline_service
from app.schemas.baseline import BaselineResponse, BaselineUpsertRequest, BaselineUpsertResponse


router = APIRouter(prefix="/api/baselines", tags=["baselines"])


@router.get("/users/{user_id}", response_model=BaselineResponse)
def get_user_baseline(
    user_id: str,
    baseline_service: BaselineService = Depends(get_baseline_service),
) -> BaselineResponse:
    return BaselineResponse(
        user_id=user_id,
        source=baseline_service.get_baseline_source(user_id),
        baseline=baseline_service.get_baseline(user_id),
    )


@router.post("/users/{user_id}", response_model=BaselineUpsertResponse)
def upsert_user_baseline(
    user_id: str,
    request: BaselineUpsertRequest,
    baseline_service: BaselineService = Depends(get_baseline_service),
) -> BaselineUpsertResponse:
    baseline = baseline_service.upsert_baseline(user_id, request.to_updates())
    return BaselineUpsertResponse(
        user_id=user_id,
        source="user",
        baseline=baseline,
    )
