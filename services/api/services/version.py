"""Application service for version and contract metadata (API-003)."""

from packages.config.settings import Settings
from services.api.schemas.version import VersionContracts, VersionResponse
from services.ml.features.standard_set import STANDARD_FEATURE_VERSION
from services.ml.labels.targets import STANDARD_TARGET_SET_VERSION


class VersionService:
    """Service providing canonical version and contract metadata."""

    @classmethod
    def get_version_info(cls, settings: Settings) -> VersionResponse:
        """Assemble active application and domain/ML contract versions."""
        return VersionResponse(
            service="sih26162-api",
            version="0.1.0",
            api_version="v1",
            environment=settings.ENVIRONMENT.value,
            contracts=VersionContracts(
                features=STANDARD_FEATURE_VERSION,
                targets=STANDARD_TARGET_SET_VERSION,
            ),
        )
