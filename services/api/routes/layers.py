"""FastAPI route handlers for GeoJSON map layers (API-012, GIS-001/002/004)."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query, status

from services.api.schemas.layers import GeoJsonFeatureCollection
from services.api.services.layers import LayerQueryService

router = APIRouter(prefix="/layers", tags=["layers"])


@router.get(
    "/events",
    response_model=GeoJsonFeatureCollection,
    status_code=status.HTTP_200_OK,
    operation_id="get_events_layer",
    summary="Retrieve canonical thermal events map layer",
    description=(
        "Returns a RFC 7946 GeoJSON FeatureCollection of canonical thermal events. "
        "Supports spatial bounding box and temporal range filtering."
    ),
)
def get_events_layer(
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
    start_time: Annotated[
        datetime | None,
        Query(description="Filter events starting at or after timestamp"),
    ] = None,
    end_time: Annotated[
        datetime | None,
        Query(description="Filter events ending at or before timestamp"),
    ] = None,
    status: Annotated[
        str | None,
        Query(description="Filter by operational status"),
    ] = None,
    classification_state: Annotated[
        str | None,
        Query(description="Filter by classification class (e.g. 'industrial')"),
    ] = None,
    min_frp_mw: Annotated[
        float | None,
        Query(description="Filter by minimum FRP in MW", ge=0.0),
    ] = None,
    geometry_type: Annotated[
        str,
        Query(description="Geometry representation: 'point' or 'envelope'"),
    ] = "point",
    limit: Annotated[
        int, Query(description="Maximum features to return", ge=1, le=1000)
    ] = 100,
    offset: Annotated[int, Query(description="Number of features to skip", ge=0)] = 0,
) -> GeoJsonFeatureCollection:
    """Retrieve canonical thermal events map layer."""
    return LayerQueryService.get_events_layer(
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        start_time=start_time,
        end_time=end_time,
        status=status,
        classification_state=classification_state,
        min_frp_mw=min_frp_mw,
        geometry_type=geometry_type,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/persistent-sources",
    response_model=GeoJsonFeatureCollection,
    status_code=status.HTTP_200_OK,
    operation_id="get_persistent_sources_layer",
    summary="Retrieve persistent thermal sources map layer",
    description=(
        "Returns a RFC 7946 GeoJSON FeatureCollection of persistent or recurring "
        "thermal sources with longitudinal activity metrics."
    ),
)
def get_persistent_sources_layer(
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
    limit: Annotated[
        int, Query(description="Maximum features to return", ge=1, le=1000)
    ] = 100,
    offset: Annotated[int, Query(description="Number of features to skip", ge=0)] = 0,
) -> GeoJsonFeatureCollection:
    """Retrieve persistent thermal sources map layer."""
    return LayerQueryService.get_persistent_sources_layer(
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/industrial",
    response_model=GeoJsonFeatureCollection,
    status_code=status.HTTP_200_OK,
    operation_id="get_industrial_layer",
    summary="Retrieve industrial context infrastructure map layer",
    description=(
        "Returns a RFC 7946 GeoJSON FeatureCollection of external industrial "
        "infrastructure (refineries, petrochemicals, power plants, flare arrays)."
    ),
)
def get_industrial_layer(
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
    context_type: Annotated[
        str | None,
        Query(
            description="Filter context type (e.g. 'industrial', 'oil_gas', 'power')"
        ),
    ] = None,
    limit: Annotated[
        int, Query(description="Maximum features to return", ge=1, le=1000)
    ] = 100,
    offset: Annotated[int, Query(description="Number of features to skip", ge=0)] = 0,
) -> GeoJsonFeatureCollection:
    """Retrieve industrial infrastructure map layer."""
    return LayerQueryService.get_industrial_layer(
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        context_type=context_type,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/land-cover",
    response_model=GeoJsonFeatureCollection,
    status_code=status.HTTP_200_OK,
    operation_id="get_land_cover_layer",
    summary="Retrieve land-cover and vegetation context map layer",
    description=(
        "Returns a RFC 7946 GeoJSON FeatureCollection of external land-use, "
        "cropland, forest/vegetation, or urban context boundaries."
    ),
)
def get_land_cover_layer(
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
    context_type: Annotated[
        str | None,
        Query(description="Filter by context type (e.g. 'agricultural')"),
    ] = None,
    limit: Annotated[
        int, Query(description="Maximum features to return", ge=1, le=1000)
    ] = 100,
    offset: Annotated[int, Query(description="Number of features to skip", ge=0)] = 0,
) -> GeoJsonFeatureCollection:
    """Retrieve land-cover and vegetation map layer."""
    return LayerQueryService.get_land_cover_layer(
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        context_type=context_type,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/detections",
    response_model=GeoJsonFeatureCollection,
    status_code=status.HTTP_200_OK,
    operation_id="get_detections_layer",
    summary="Retrieve raw thermal anomaly detections map layer (GIS-003)",
    description=(
        "Returns a RFC 7946 GeoJSON FeatureCollection of canonical raw observations. "
        "Supports rendering observational centroid Points or sensor pixel footprints "
        "without overclaiming spatial precision."
    ),
)
def get_detections_layer(
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
    start_time: Annotated[
        datetime | None,
        Query(description="Filter detections acquired at or after timestamp"),
    ] = None,
    end_time: Annotated[
        datetime | None,
        Query(description="Filter detections acquired at or before timestamp"),
    ] = None,
    source: Annotated[
        str | None,
        Query(description="Filter by source or product type (e.g. 'firms', 'nrt')"),
    ] = None,
    satellite: Annotated[
        str | None,
        Query(description="Filter by satellite name (e.g. 'NOAA-20')"),
    ] = None,
    instrument: Annotated[
        str | None,
        Query(description="Filter by instrument name (e.g. 'VIIRS')"),
    ] = None,
    min_frp_mw: Annotated[
        float | None,
        Query(description="Filter by minimum FRP in MW", ge=0.0),
    ] = None,
    geometry_type: Annotated[
        str,
        Query(description="Geometry representation: 'point' or 'footprint'"),
    ] = "point",
    limit: Annotated[
        int, Query(description="Maximum features to return", ge=1, le=1000)
    ] = 100,
    offset: Annotated[int, Query(description="Number of features to skip", ge=0)] = 0,
) -> GeoJsonFeatureCollection:
    """Retrieve raw thermal anomaly detections map layer."""
    return LayerQueryService.get_detections_layer(
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        start_time=start_time,
        end_time=end_time,
        source=source,
        satellite=satellite,
        instrument=instrument,
        min_frp_mw=min_frp_mw,
        geometry_type=geometry_type,
        limit=limit,
        offset=offset,
    )
