"""Application service for data source status and capabilities (API-004)."""

from packages.config.settings import Settings
from packages.errors import ErrorCode, NotFoundError
from packages.schemas.enums import SourceRole
from services.api.schemas.sources import (
    SourceAvailabilityState,
    SourceOperationalMode,
    SourcesStatusResponse,
    SourceStatusItem,
)


class SourceStatusService:
    """Service providing registered data source availability and mode metadata."""

    @classmethod
    def get_sources_status(cls, settings: Settings) -> SourcesStatusResponse:
        """Assemble operational status for all registered data sources."""
        has_firms_key = settings.FIRMS_MAP_KEY is not None

        sources: list[SourceStatusItem] = [
            SourceStatusItem(
                source_id="nasa_firms",
                name="NASA FIRMS Thermal Anomalies / Active Fire Data",
                provider="NASA Earthdata / EOSDIS",
                role=SourceRole.OBSERVATION,
                mode=(
                    SourceOperationalMode.LIVE
                    if has_firms_key
                    else SourceOperationalMode.OFFLINE
                ),
                status=(
                    SourceAvailabilityState.CONFIGURED
                    if has_firms_key
                    else SourceAvailabilityState.OFFLINE_ONLY
                ),
                details={
                    "base_url": settings.FIRMS_BASE_URL,
                    "has_map_key": has_firms_key,
                    "timeout_seconds": settings.FIRMS_TIMEOUT_SECONDS,
                    "max_retries": settings.FIRMS_MAX_RETRIES,
                    "supported_products": [
                        "VIIRS_NOAA20_NRT",
                        "VIIRS_SNPP_NRT",
                        "MODIS_NRT",
                    ],
                },
            ),
            SourceStatusItem(
                source_id="osm",
                name="OpenStreetMap Infrastructure & Context",
                provider="OpenStreetMap Foundation",
                role=SourceRole.CONTEXT,
                mode=SourceOperationalMode.HYBRID,
                status=SourceAvailabilityState.AVAILABLE,
                details={
                    "context_types": [
                        "industrial",
                        "oil_gas",
                        "power",
                        "mining",
                        "agricultural",
                        "urban",
                    ],
                },
            ),
            SourceStatusItem(
                source_id="wri_power_plants",
                name="WRI Global Power Plant Database",
                provider="World Resources Institute",
                role=SourceRole.CONTEXT,
                mode=SourceOperationalMode.OFFLINE,
                status=SourceAvailabilityState.AVAILABLE,
                details={
                    "coverage": "Global",
                    "focus": "Thermal & Industrial Power Generation",
                },
            ),
            SourceStatusItem(
                source_id="gem_fossil_infrastructure",
                name="GEM Global Fossil Infrastructure Trackers",
                provider="Global Energy Monitor",
                role=SourceRole.CONTEXT,
                mode=SourceOperationalMode.OFFLINE,
                status=SourceAvailabilityState.AVAILABLE,
                details={
                    "trackers": [
                        "Global Gas Plant Tracker",
                        "Global Oil & Gas Extraction Tracker",
                    ],
                },
            ),
            SourceStatusItem(
                source_id="landcover",
                name="Copernicus / ESA Land Cover Classification",
                provider="ESA / European Union Copernicus",
                role=SourceRole.CONTEXT,
                mode=SourceOperationalMode.OFFLINE,
                status=SourceAvailabilityState.AVAILABLE,
                details={
                    "resolution_meters": 10.0,
                    "classes": ["industrial", "forest", "cropland", "urban"],
                },
            ),
        ]

        return SourcesStatusResponse(
            service="sih26162-api",
            environment=settings.ENVIRONMENT.value,
            sources=sources,
        )

    @classmethod
    def get_source(cls, settings: Settings, source_id: str) -> SourceStatusItem:
        """Retrieve operational availability metadata for a specific source."""
        all_sources = cls.get_sources_status(settings).sources
        target_source = next((s for s in all_sources if s.source_id == source_id), None)
        if target_source is None:
            raise NotFoundError(
                message=f"Source '{source_id}' not found.",
                code=ErrorCode.RESOURCE_NOT_FOUND,
            )
        return target_source
