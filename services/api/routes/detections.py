"""Detection query and listing route handler."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query, status

from packages.schemas.enums import DayNight
from services.api.schemas.detections import DetectionsResponse
from services.api.services.detections import DetectionQueryService

router = APIRouter(tags=["detections"])


@router.get(
    "/detections",
    response_model=DetectionsResponse,
    status_code=status.HTTP_200_OK,
    summary="Query Canonical Detections",
    description=(
        "Returns canonical thermal anomaly detection records from satellite sensors "
        "with spatial (bounding box), temporal (start/end time), "
        "source/satellite/instrument, day/night, and pagination filters."
    ),
)
async def get_detections(
    min_lat: Annotated[
        float | None,
        Query(
            ge=-90.0,
            le=90.0,
            description="Minimum latitude in decimal degrees (-90.0 to 90.0)",
        ),
    ] = None,
    max_lat: Annotated[
        float | None,
        Query(
            ge=-90.0,
            le=90.0,
            description="Maximum latitude in decimal degrees (-90.0 to 90.0)",
        ),
    ] = None,
    min_lon: Annotated[
        float | None,
        Query(
            ge=-180.0,
            le=180.0,
            description="Minimum longitude in decimal degrees (-180.0 to 180.0)",
        ),
    ] = None,
    max_lon: Annotated[
        float | None,
        Query(
            ge=-180.0,
            le=180.0,
            description="Maximum longitude in decimal degrees (-180.0 to 180.0)",
        ),
    ] = None,
    start_time: Annotated[
        datetime | None,
        Query(description="Observation start time in UTC (ISO-8601)"),
    ] = None,
    end_time: Annotated[
        datetime | None,
        Query(description="Observation end time in UTC (ISO-8601)"),
    ] = None,
    source: Annotated[
        str | None,
        Query(description="Filter by observation source adapter or product type"),
    ] = None,
    satellite: Annotated[
        str | None,
        Query(
            description="Filter by observing satellite (e.g. 'NOAA-20', 'Suomi-NPP')"
        ),
    ] = None,
    instrument: Annotated[
        str | None,
        Query(description="Filter by sensor instrument (e.g. 'VIIRS', 'MODIS')"),
    ] = None,
    day_night: Annotated[
        DayNight | None,
        Query(description="Filter by day ('D') or night ('N') observation flag"),
    ] = None,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=1000,
            description="Maximum number of records to return per page",
        ),
    ] = 50,
    offset: Annotated[
        int,
        Query(
            ge=0,
            description="Number of matching records to skip",
        ),
    ] = 0,
) -> DetectionsResponse:
    """Retrieve filtered and paginated canonical thermal detection records."""
    return DetectionQueryService.query_detections(
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        start_time=start_time,
        end_time=end_time,
        source=source,
        satellite=satellite,
        instrument=instrument,
        day_night=day_night,
        limit=limit,
        offset=offset,
    )
