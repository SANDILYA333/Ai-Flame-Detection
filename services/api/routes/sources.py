"""Data source status route handler."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from packages.config.settings import Settings
from services.api.dependencies import get_app_settings
from services.api.schemas.sources import (
    SourcesStatusResponse,
    SourceStatusItem,
)
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


@router.get(
    "/sources",
    response_model=SourcesStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="List all registered data sources",
    description="Returns a list of all configured and offline data sources.",
)
async def list_sources(
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> SourcesStatusResponse:
    """Retrieve operational availability and status across all registered sources."""
    return SourceStatusService.get_sources_status(settings)


@router.get(
    "/sources/{source_id}",
    response_model=SourceStatusItem,
    status_code=status.HTTP_200_OK,
    summary="Retrieve detailed metadata for one source",
    description="Returns metadata for one registered source by ID.",
)
async def get_source(
    source_id: str,
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> SourceStatusItem:
    """Retrieve operational availability metadata for a specific source."""
    return SourceStatusService.get_source(settings, source_id)
