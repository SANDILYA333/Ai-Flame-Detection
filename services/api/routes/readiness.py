"""Readiness check route handler."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import JSONResponse

from packages.config.settings import Settings
from services.api.dependencies import get_app_settings
from services.api.schemas.readiness import DependencyStatus, ReadinessResponse
from services.api.services.readiness import ReadinessCheckService

router = APIRouter(tags=["readiness"])


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "description": "All required system dependencies are operational.",
            "model": ReadinessResponse,
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "One or more critical dependencies are unavailable.",
            "model": ReadinessResponse,
        },
    },
    summary="System Readiness Check",
    description=(
        "Performs readiness verification across backend dependencies (database, "
        "model registry, configuration) without exposing credentials or secrets."
    ),
)
async def get_readiness(
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> Response:
    """Evaluate system readiness across essential dependencies."""
    readiness = ReadinessCheckService.evaluate_readiness(settings)

    if readiness.status == DependencyStatus.READY:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=readiness.model_dump(mode="json"),
        )

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=readiness.model_dump(mode="json"),
    )
