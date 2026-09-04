"""FastAPI route handlers for Weather & Wind Intelligence (Phase 1 & 2)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from packages.config.settings import Settings
from packages.data.weather import get_weather_service
from packages.errors import ValidationError
from services.api.dependencies import get_app_settings
from services.api.schemas.weather import EventWeatherResponse, WeatherResponse

router = APIRouter(prefix="/weather", tags=["weather"])


def _handle_get_weather(
    settings: Settings,
    latitude: float | None = None,
    longitude: float | None = None,
    lat: float | None = None,
    lon: float | None = None,
    forecast_hours: int = 24,
    allow_cached: bool = True,
) -> WeatherResponse:
    """Internal handler for weather coordinate lookup."""
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

    weather_service = get_weather_service(settings)
    canonical_data = weather_service.get_weather(
        latitude=eff_lat,
        longitude=eff_lon,
        forecast_hours=forecast_hours,
        allow_cached=allow_cached,
    )

    return WeatherResponse(
        location=canonical_data.location,
        observed_at=canonical_data.observed_at,
        retrieved_at=canonical_data.retrieved_at,
        data_status=canonical_data.data_status,
        data_quality=canonical_data.data_quality,
        atmosphere=canonical_data.atmosphere,
        wind=canonical_data.wind,
        forecast=canonical_data.forecast,
        provider=canonical_data.provider,
    )


@router.get(
    "",
    response_model=WeatherResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve real-time meteorological observations and wind vectors",
    description=(
        "Returns canonical weather data, atmospheric metrics, short-term forecast, "
        "and orthogonal wind vector decomposition for given WGS-84 geographic coordinates."
    ),
)
def get_weather(
    settings: Annotated[Settings, Depends(get_app_settings)],
    latitude: Annotated[
        float | None,
        Query(
            ge=-90.0,
            le=90.0,
            description="Latitude in decimal degrees [-90.0, 90.0]",
        ),
    ] = None,
    longitude: Annotated[
        float | None,
        Query(
            ge=-180.0,
            le=180.0,
            description="Longitude in decimal degrees [-180.0, 180.0]",
        ),
    ] = None,
    lat: Annotated[
        float | None,
        Query(
            ge=-90.0,
            le=90.0,
            description="Alias for latitude in decimal degrees",
        ),
    ] = None,
    lon: Annotated[
        float | None,
        Query(
            ge=-180.0,
            le=180.0,
            description="Alias for longitude in decimal degrees",
        ),
    ] = None,
    forecast_hours: Annotated[
        int,
        Query(
            ge=0,
            le=168,
            description="Forecast horizon lead time in hours (default 24)",
        ),
    ] = 24,
    allow_cached: Annotated[
        bool,
        Query(
            description="Whether to permit returning non-expired spatially cached data",
        ),
    ] = True,
) -> WeatherResponse:
    """Fetch current meteorological state and wind vector for coordinates."""
    return _handle_get_weather(
        settings=settings,
        latitude=latitude,
        longitude=longitude,
        lat=lat,
        lon=lon,
        forecast_hours=forecast_hours,
        allow_cached=allow_cached,
    )


@router.get(
    "/current",
    response_model=WeatherResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve current meteorological conditions (endpoint alias)",
    description="Alias endpoint for retrieving current weather and wind vector at coordinates.",
)
def get_current_weather(
    settings: Annotated[Settings, Depends(get_app_settings)],
    latitude: Annotated[
        float | None,
        Query(ge=-90.0, le=90.0, description="Latitude [-90.0, 90.0]"),
    ] = None,
    longitude: Annotated[
        float | None,
        Query(ge=-180.0, le=180.0, description="Longitude [-180.0, 180.0]"),
    ] = None,
    lat: Annotated[
        float | None,
        Query(ge=-90.0, le=90.0, description="Latitude alias"),
    ] = None,
    lon: Annotated[
        float | None,
        Query(ge=-180.0, le=180.0, description="Longitude alias"),
    ] = None,
    forecast_hours: Annotated[
        int,
        Query(ge=0, le=168, description="Forecast horizon in hours"),
    ] = 24,
    allow_cached: Annotated[
        bool,
        Query(description="Allow non-expired cached responses"),
    ] = True,
) -> WeatherResponse:
    """Retrieve current weather observation and wind components."""
    return _handle_get_weather(
        settings=settings,
        latitude=latitude,
        longitude=longitude,
        lat=lat,
        lon=lon,
        forecast_hours=forecast_hours,
        allow_cached=allow_cached,
    )


@router.get(
    "/events/{event_id}",
    response_model=EventWeatherResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve meteorological context enriched for a specific thermal event",
    description="Couples live/cached weather observations to a specific thermal event coordinate.",
)
def get_event_weather(
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
    forecast_hours: Annotated[
        int,
        Query(ge=0, le=168, description="Forecast horizon in hours"),
    ] = 24,
) -> EventWeatherResponse:
    """Enrich a thermal event with meteorological observation."""
    from services.api.services.events import EventQueryService

    eff_lat = latitude
    eff_lon = longitude

    if eff_lat is None or eff_lon is None:
        event_detail = EventQueryService.get_event(event_id)
        lon, lat = event_detail.geometry["coordinates"]
        eff_lat = eff_lat if eff_lat is not None else lat
        eff_lon = eff_lon if eff_lon is not None else lon

    weather_service = get_weather_service(settings)
    enrichment = weather_service.enrich_event(
        event_id=event_id,
        latitude=eff_lat,
        longitude=eff_lon,
        forecast_hours=forecast_hours,
    )

    weather_resp = WeatherResponse(
        location=enrichment.weather.location,
        observed_at=enrichment.weather.observed_at,
        retrieved_at=enrichment.weather.retrieved_at,
        data_status=enrichment.weather.data_status,
        data_quality=enrichment.weather.data_quality,
        atmosphere=enrichment.weather.atmosphere,
        wind=enrichment.weather.wind,
        forecast=enrichment.weather.forecast,
        provider=enrichment.weather.provider,
    )

    return EventWeatherResponse(
        event_id=enrichment.event_id,
        weather=weather_resp,
        enriched_at=enrichment.enriched_at,
    )
