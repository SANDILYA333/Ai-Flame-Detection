"""Data source status route handler."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from packages.config.settings import Settings
from services.api.dependencies import get_app_settings
from services.api.schemas.sources import SourcesStatusResponse
from services.api.services.sources import SourceStatusService

router = APIRouter(tags=["sources"])


@router.get(
    "/sources/status",
    response_model=SourcesStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Data Source Availability and Mode Status",
    description=(
        "Returns operational availability, source roles (OBSERVATION, CONTEXT), "
        "and operational modes (live, offline, hybrid) for registered data providers."
    ),
)
async def get_sources_status(
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> SourcesStatusResponse:
    """Retrieve operational availability and status across all registered sources."""
    return SourceStatusService.get_sources_status(settings)
