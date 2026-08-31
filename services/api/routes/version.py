"""Version check route handler."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from packages.config.settings import Settings
from services.api.dependencies import get_app_settings
from services.api.schemas.version import VersionResponse
from services.api.services.version import VersionService

router = APIRouter(tags=["version"])


@router.get(
    "/version",
    response_model=VersionResponse,
    status_code=status.HTTP_200_OK,
    summary="System and Contract Version",
    description=(
        "Returns active application semantic version, API interface version, "
        "and domain/ML contract catalog versions (features, targets)."
    ),
)
async def get_version(
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> VersionResponse:
    """Retrieve active system and domain contract version metadata."""
    return VersionService.get_version_info(settings)
