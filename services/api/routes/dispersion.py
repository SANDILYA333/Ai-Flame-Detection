"""FastAPI route handlers for Atmospheric Dispersion & Downwind Hazard Intelligence (Phase 3)."""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status

from packages.config.settings import Settings
from packages.data.weather import get_dispersion_service
from packages.errors import ValidationError
from services.api.dependencies import get_app_settings
from services.api.schemas.dispersion import (
    DispersionCalculationRequest,
    DispersionCalculationResponse,
)

router = APIRouter(prefix="/dispersion", tags=["dispersion"])


@router.post(
    "",
    response_model=DispersionCalculationResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute atmospheric dispersion and hazard corridor for coordinates",
    description=(
        "Performs Gaussian plume atmospheric dispersion modeling using validated meteorological "
        "conditions (or custom parameter overrides). Evaluates downwind centerline trajectory, "
        "lateral cross-sections, Pasquill-Gifford stability, and relative ground-level concentration decay."
    ),
)
def calculate_dispersion_post(
    settings: Annotated[Settings, Depends(get_app_settings)],
    request: Annotated[
        DispersionCalculationRequest,
        Body(description="Atmospheric dispersion calculation parameters"),
    ],
) -> DispersionCalculationResponse:
    """Calculate atmospheric dispersion from JSON request body."""
    dispersion_service = get_dispersion_service(settings)
    result = dispersion_service.calculate_dispersion(
        latitude=request.latitude,
        longitude=request.longitude,
        frp_mw=request.frp_mw,
        release_height_m=request.release_height_m,
        custom_wind_speed_ms=request.custom_wind_speed_ms,
        custom_wind_direction_deg=request.custom_wind_direction_deg,
        is_daytime=request.is_daytime,
        max_distance_km=request.max_distance_km,
    )

    return DispersionCalculationResponse(
        source_location=result.source_location,
        event_id=result.event_id,
        evaluated_at=result.evaluated_at,
        wind=result.wind,
        dispersion=result.dispersion,
        trajectory=result.trajectory,
        data_quality=result.data_quality,
        model_confidence=result.model_confidence,
    )


@router.get(
    "",
    response_model=DispersionCalculationResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute atmospheric dispersion and hazard corridor (GET query parameters)",
    description=(
        "Query-based Gaussian plume atmospheric dispersion calculation for rapid UI inspection "
        "and downstream subsystem integration."
    ),
)
def calculate_dispersion_get(
    settings: Annotated[Settings, Depends(get_app_settings)],
    latitude: Annotated[
        float | None,
        Query(ge=-90.0, le=90.0, description="Latitude in decimal degrees [-90, 90]"),
    ] = None,
    longitude: Annotated[
        float | None,
        Query(ge=-180.0, le=180.0, description="Longitude in decimal degrees [-180, 180]"),
    ] = None,
    lat: Annotated[
        float | None,
        Query(ge=-90.0, le=90.0, description="Alias for latitude"),
    ] = None,
    lon: Annotated[
        float | None,
        Query(ge=-180.0, le=180.0, description="Alias for longitude"),
    ] = None,
    frp_mw: Annotated[
        float | None,
        Query(ge=0.0, description="Fire Radiative Power in MW"),
    ] = None,
    release_height_m: Annotated[
        float | None,
        Query(ge=0.0, description="Stack / emission release height in meters"),
    ] = None,
    custom_wind_speed_ms: Annotated[
        float | None,
        Query(ge=0.0, description="Custom wind speed override in m/s"),
    ] = None,
    custom_wind_direction_deg: Annotated[
        float | None,
        Query(ge=0.0, le=360.0, description="Custom wind direction override in degrees"),
    ] = None,
    is_daytime: Annotated[
        bool | None,
        Query(description="Solar daytime flag override"),
    ] = None,
    max_distance_km: Annotated[
        float | None,
        Query(ge=0.5, le=50.0, description="Downwind calculation horizon in km"),
    ] = None,
) -> DispersionCalculationResponse:
    """Calculate atmospheric dispersion via query parameters."""
    eff_lat = latitude if latitude is not None else lat
    eff_lon = longitude if longitude is not None else lon

    if eff_lat is None or eff_lon is None:
        raise ValidationError(
            "Both latitude (or 'lat') and longitude (or 'lon') query parameters are required.",
            details={
                "provided_latitude": eff_lat,
                "provided_longitude": eff_lon,
            },
        )

    dispersion_service = get_dispersion_service(settings)
    result = dispersion_service.calculate_dispersion(
        latitude=eff_lat,
        longitude=eff_lon,
        frp_mw=frp_mw,
        release_height_m=release_height_m,
        custom_wind_speed_ms=custom_wind_speed_ms,
        custom_wind_direction_deg=custom_wind_direction_deg,
        is_daytime=is_daytime,
        max_distance_km=max_distance_km,
    )

    return DispersionCalculationResponse(
        source_location=result.source_location,
        event_id=result.event_id,
        evaluated_at=result.evaluated_at,
        wind=result.wind,
        dispersion=result.dispersion,
        trajectory=result.trajectory,
        data_quality=result.data_quality,
        model_confidence=result.model_confidence,
    )


@router.get(
    "/events/{event_id}",
    response_model=DispersionCalculationResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute atmospheric dispersion coupled to a thermal event",
    description="Evaluates atmospheric dispersion and hazard corridor for a specific thermal event coordinate.",
)
def get_event_dispersion(
    event_id: str,
    settings: Annotated[Settings, Depends(get_app_settings)],
    latitude: Annotated[
        float | None,
        Query(ge=-90.0, le=90.0, description="Event latitude coordinate"),
    ] = None,
    longitude: Annotated[
        float | None,
        Query(ge=-180.0, le=180.0, description="Event longitude coordinate"),
    ] = None,
    frp_mw: Annotated[
        float | None,
        Query(ge=0.0, description="Fire Radiative Power in MW"),
    ] = None,
    release_height_m: Annotated[
        float | None,
        Query(ge=0.0, description="Release height in meters"),
    ] = None,
    max_distance_km: Annotated[
        float | None,
        Query(ge=0.5, le=50.0, description="Downwind horizon in km"),
    ] = None,
) -> DispersionCalculationResponse:
    """Evaluate atmospheric dispersion for a given thermal anomaly event."""
    from services.api.services.events import EventQueryService

    eff_lat = latitude
    eff_lon = longitude
    eff_frp = frp_mw

    if eff_lat is None or eff_lon is None:
        event_detail = EventQueryService.get_event(event_id)
        lon, lat = event_detail.geometry["coordinates"]
        eff_lat = eff_lat if eff_lat is not None else lat
        eff_lon = eff_lon if eff_lon is not None else lon

    dispersion_service = get_dispersion_service(settings)
    result = dispersion_service.evaluate_event_dispersion(
        event_id=event_id,
        latitude=eff_lat,
        longitude=eff_lon,
        frp_mw=eff_frp,
        release_height_m=release_height_m,
        max_distance_km=max_distance_km,
    )

    return DispersionCalculationResponse(
        source_location=result.source_location,
        event_id=result.event_id,
        evaluated_at=result.evaluated_at,
        wind=result.wind,
        dispersion=result.dispersion,
        trajectory=result.trajectory,
        data_quality=result.data_quality,
        model_confidence=result.model_confidence,
    )
