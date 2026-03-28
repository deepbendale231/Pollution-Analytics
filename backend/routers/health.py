from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from ..schemas.response import HealthResponse
from ..services.model_service import get_loaded_model_artifacts

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
def health_check() -> HealthResponse:
    model, scaler = get_loaded_model_artifacts()
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(timezone.utc),
        model_loaded=bool(model is not None and scaler is not None),
    )
