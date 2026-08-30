"""Health check route handler."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from packages.config.settings import Settings
from services.api.dependencies import get_app_settings
from services.api.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Service Health Check",
    description="Returns operational service status, version, and environment.",
)
async def get_health(
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> HealthResponse:
    """Check API operational health status."""
    return HealthResponse(
        status="ok",
        service="sih26162-api",
        version="0.1.0",
        environment=settings.ENVIRONMENT.value,
    )
