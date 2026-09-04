"""FastAPI route handlers for normalized industrial infrastructure assets."""

from typing import Annotated, Any

from fastapi import APIRouter, Query, status

from packages.schemas.industrial_asset import IndustrialAsset
from services.api.schemas.layers import GeoJsonFeatureCollection
from services.api.services.industrial import IndustrialAssetQueryService

router = APIRouter(tags=["industrial-assets"])


@router.get(
    "/api/industrial-assets",
    response_model=GeoJsonFeatureCollection,
    status_code=status.HTTP_200_OK,
    operation_id="get_industrial_assets",
    summary="Retrieve normalized industrial assets as RFC 7946 GeoJSON",
    description=(
        "Returns a RFC 7946 GeoJSON FeatureCollection of normalized "
        "industrial facilities (power plants, refineries, oil & gas complexes). "
        "Supports spatial bounding box, industry, status, and state filtering."
    ),
)
@router.get(
    "/industrial-assets",
    response_model=GeoJsonFeatureCollection,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_industrial_assets(
    min_lat: Annotated[
        float | None, Query(description="Min bounding box latitude", ge=-90, le=90)
    ] = None,
    max_lat: Annotated[
        float | None, Query(description="Max bounding box latitude", ge=-90, le=90)
    ] = None,
    min_lon: Annotated[
        float | None, Query(description="Min bounding box longitude", ge=-180, le=180)
    ] = None,
    max_lon: Annotated[
        float | None, Query(description="Max bounding box longitude", ge=-180, le=180)
    ] = None,
    bbox: Annotated[
        str | None,
        Query(
            description=(
                "Bounding box formatted as 'min_lon,min_lat,max_lon,max_lat'"
            )
        ),
    ] = None,
    industry: Annotated[
        str | None,
        Query(
            description=(
                "Filter by industry type (e.g. 'power', 'oil_gas', 'metallurgy')"
            )
        ),
    ] = None,
    status: Annotated[
        str | None,
        Query(
            description=(
                "Filter by operational status (e.g. 'operating', 'construction')"
            )
        ),
    ] = None,
    state: Annotated[
        str | None,
        Query(description="Filter by Indian State or Union Territory name"),
    ] = None,
    include_expansion: Annotated[
        bool,
        Query(
            description="Include expansion metallurgy and steel facilities"
        ),
    ] = False,
    limit: Annotated[
        int, Query(description="Maximum features to return", ge=1, le=5000)
    ] = 2000,
    offset: Annotated[int, Query(description="Number of features to skip", ge=0)] = 0,
) -> GeoJsonFeatureCollection:
    """Retrieve normalized industrial assets as RFC 7946 GeoJSON FeatureCollection."""
    return IndustrialAssetQueryService.query_assets_geojson(
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        bbox_str=bbox,
        industry=industry,
        status=status,
        state=state,
        include_expansion=include_expansion,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/api/industrial-assets/summary",
    status_code=status.HTTP_200_OK,
    operation_id="get_industrial_assets_summary",
    summary="Retrieve inventory summary and breakdown for industrial assets",
    description=(
        "Returns total counts, map-eligible facility counts, source provenance, "
        "and industry sector distribution."
    ),
)
@router.get(
    "/industrial-assets/summary",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_industrial_assets_summary(
    include_expansion: Annotated[
        bool,
        Query(
            description="Include expansion metallurgy and steel facilities in metrics"
        ),
    ] = False,
) -> dict[str, Any]:
    """Retrieve operational inventory summary for industrial assets."""
    return IndustrialAssetQueryService.get_summary(include_expansion=include_expansion)


@router.get(
    "/api/industrial-assets/{asset_id}",
    response_model=IndustrialAsset,
    status_code=status.HTTP_200_OK,
    operation_id="get_industrial_asset_detail",
    summary="Retrieve single normalized industrial asset details by ID",
    description=(
        "Returns the complete canonical representation of an industrial facility "
        "including exact location, operational status, capacity, and linked duplicates."
    ),
)
@router.get(
    "/industrial-assets/{asset_id}",
    response_model=IndustrialAsset,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_industrial_asset_detail(asset_id: str) -> IndustrialAsset:
    """Retrieve details for a specific industrial asset by ID."""
    return IndustrialAssetQueryService.get_asset_by_id(asset_id)
