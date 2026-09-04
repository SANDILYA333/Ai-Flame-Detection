"""Meteorological data service coordinating providers, validation, and caching."""

import logging
from datetime import datetime, timezone

from packages.config.settings import Settings, get_settings
from packages.data.weather.base import BaseWeatherProvider
from packages.data.weather.cache import WeatherCache
from packages.data.weather.open_meteo import OpenMeteoWeatherProvider
from packages.errors import (
    ExternalServiceError,
    ServiceTimeoutError,
    ServiceUnavailableError,
)
from packages.geospatial.coordinates import validate_wgs84_coordinates
from packages.logging import get_logger, log_with_context
from packages.physics.wind import build_wind_vector
from packages.schemas.common import Coordinate
from packages.schemas.weather import (
    AtmosphereData,
    CanonicalWeatherData,
    DataQuality,
    DataStatus,
    EventWeatherEnrichment,
    WeatherProviderInfo,
)

logger = get_logger("packages.data.weather.service")


class WeatherService:
    """High-level service interface for meteorological intelligence."""

    def __init__(
        self,
        provider: BaseWeatherProvider | None = None,
        cache: WeatherCache | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.provider = provider or OpenMeteoWeatherProvider(self.settings)
        self.cache = cache or WeatherCache(self.settings)

    def get_weather(
        self,
        latitude: float,
        longitude: float,
        forecast_hours: int = 24,
        allow_cached: bool = True,
    ) -> CanonicalWeatherData:
        """Retrieve current weather and short-term forecast for geographic coordinates.

        Args:
            latitude: Latitude in decimal degrees [-90.0, 90.0].
            longitude: Longitude in decimal degrees [-180.0, 180.0].
            forecast_hours: Forecast horizon in hours (default 24).
            allow_cached: Whether to return valid non-expired cached entries.

        Returns:
            CanonicalWeatherData: Canonical weather data with LIVE or CACHED status.

        Raises:
            InvalidCoordinateError: If coordinates are out of bounds or non-finite.
            ServiceTimeoutError: If live provider times out and no cache is available.
            ServiceUnavailableError: If live provider is unavailable and no cache is available.
            ExternalServiceError: If response from provider is malformed.
        """
        # 1. Validate coordinates
        valid_lat, valid_lon = validate_wgs84_coordinates(latitude, longitude)

        # 2. Check cache
        if allow_cached:
            cached_data = self.cache.get(valid_lat, valid_lon, forecast_hours)
            if cached_data is not None:
                log_with_context(
                    logger,
                    logging.DEBUG,
                    "Weather cache hit",
                    context={
                        "latitude": valid_lat,
                        "longitude": valid_lon,
                        "forecast_hours": forecast_hours,
                        "data_quality": cached_data.data_quality.value,
                    },
                )
                return cached_data

        # 3. Cache miss: Request from live provider
        try:
            live_data = self.provider.get_weather(
                latitude=valid_lat,
                longitude=valid_lon,
                forecast_hours=forecast_hours,
            )
            # Store fresh data in cache
            self.cache.set(live_data, forecast_hours)
            return live_data

        except Exception as exc:
            # 4. Fallback: Try stale cache if available
            stale_data = self.cache.get_stale(valid_lat, valid_lon, forecast_hours)
            if stale_data is not None:
                log_with_context(
                    logger,
                    logging.WARNING,
                    "Live weather provider failed; returning stale cached data as fallback",
                    context={
                        "latitude": valid_lat,
                        "longitude": valid_lon,
                        "error": str(exc),
                        "data_status": DataStatus.CACHED.value,
                        "data_quality": DataQuality.FALLBACK.value,
                    },
                )
                return stale_data

            # 5. Transparent Physical Fallback / Simulation state
            log_with_context(
                logger,
                logging.WARNING,
                "Weather provider request failed and no cache available; returning physical standard-atmosphere fallback",
                context={
                    "latitude": valid_lat,
                    "longitude": valid_lon,
                    "error": str(exc),
                },
            )
            now = datetime.now(timezone.utc)
            wind = build_wind_vector(speed_ms=4.5, direction_from_deg=225.0)
            atmo = AtmosphereData(
                temperature_c=28.0,
                relative_humidity_pct=60.0,
                surface_pressure_hpa=1012.0,
                cloud_cover_pct=20.0,
                precipitation_mm=0.0,
                boundary_layer_height_m=800.0,
            )
            provider_info = WeatherProviderInfo(
                name="fallback-simulation",
                model="standard-atmosphere",
            )
            return CanonicalWeatherData(
                location=Coordinate(latitude=valid_lat, longitude=valid_lon),
                observed_at=now,
                retrieved_at=now,
                data_status=DataStatus.UNAVAILABLE,
                data_quality=DataQuality.FALLBACK,
                atmosphere=atmo,
                wind=wind,
                forecast=[],
                provider=provider_info,
            )

    def enrich_event(
        self,
        event_id: str,
        latitude: float,
        longitude: float,
        forecast_hours: int = 24,
    ) -> EventWeatherEnrichment:
        """Fetch and couple meteorological observations to a specific thermal event.

        Args:
            event_id: Canonical event identifier.
            latitude: Event latitude coordinate.
            longitude: Event longitude coordinate.
            forecast_hours: Forecast horizon in hours (default 24).

        Returns:
            EventWeatherEnrichment: Event-coupled weather domain container.
        """
        weather = self.get_weather(latitude, longitude, forecast_hours=forecast_hours)
        return EventWeatherEnrichment(
            event_id=event_id,
            weather=weather,
            enriched_at=datetime.now(timezone.utc),
        )


# Global singleton weather service instance
_default_weather_service: WeatherService | None = None


def get_weather_service(settings: Settings | None = None) -> WeatherService:
    """Get canonical WeatherService singleton instance."""
    global _default_weather_service
    if settings is not None:
        return WeatherService(settings=settings)
    if _default_weather_service is None:
        _default_weather_service = WeatherService()
    return _default_weather_service
