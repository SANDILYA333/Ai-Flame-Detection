"""Atmospheric dispersion service orchestrating meteorological context and Gaussian hazard modeling (Phase 3)."""

import logging
from datetime import datetime, timezone

from packages.config.settings import Settings, get_settings
from packages.data.weather.service import WeatherService, get_weather_service
from packages.logging import get_logger, log_with_context
from packages.physics.dispersion import AtmosphericDispersionEngine
from packages.physics.wind import build_wind_vector
from packages.schemas.dispersion import AtmosphericDispersionResult
from packages.schemas.weather import DataQuality

logger = get_logger("packages.data.weather.dispersion_service")


class AtmosphericDispersionService:
    """Service coupling meteorological observations with Gaussian dispersion hazard modeling."""

    def __init__(
        self,
        weather_service: WeatherService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.weather_service = weather_service or get_weather_service(self.settings)

    def calculate_dispersion(
        self,
        latitude: float,
        longitude: float,
        frp_mw: float | None = None,
        release_height_m: float | None = None,
        custom_wind_speed_ms: float | None = None,
        custom_wind_direction_deg: float | None = None,
        is_daytime: bool | None = None,
        max_distance_km: float | None = None,
        allow_cached_weather: bool = True,
    ) -> AtmosphericDispersionResult:
        """Calculate downwind hazard dispersion for geographic coordinates.

        Args:
            latitude: Origin latitude [-90.0, 90.0].
            longitude: Origin longitude [-180.0, 180.0].
            frp_mw: Optional Fire Radiative Power in MW (>= 0).
            release_height_m: Optional effective release/stack height in meters.
            custom_wind_speed_ms: Optional explicit wind speed override (m/s).
            custom_wind_direction_deg: Optional explicit wind direction override (degrees FROM).
            is_daytime: Optional daytime insolation indicator (inferred from UTC hour if None).
            max_distance_km: Optional downwind horizon limit in kilometers.
            allow_cached_weather: Allow returning cached weather for coordinates.

        Returns:
            AtmosphericDispersionResult: Downwind trajectory, boundaries, and concentration profile.
        """
        cloud_cover_pct = None

        if custom_wind_speed_ms is not None and custom_wind_direction_deg is not None:
            # User/simulation explicit meteorological override
            wind = build_wind_vector(
                speed_ms=custom_wind_speed_ms,
                direction_from_deg=custom_wind_direction_deg,
            )
            data_quality = DataQuality.LIVE
        else:
            # Ingest live/cached weather from Phase 2 WeatherService
            try:
                weather = self.weather_service.get_weather(
                    latitude=latitude,
                    longitude=longitude,
                    allow_cached=allow_cached_weather,
                )
                wind = weather.wind
                cloud_cover_pct = weather.atmosphere.cloud_cover_pct
                data_quality = weather.data_quality
            except Exception as exc:
                log_with_context(
                    logger,
                    logging.WARNING,
                    "Weather service unavailable for dispersion calculation; using conservative neutral fallback",
                    context={
                        "latitude": latitude,
                        "longitude": longitude,
                        "error": str(exc),
                    },
                )
                wind = build_wind_vector(speed_ms=3.0, direction_from_deg=270.0)
                cloud_cover_pct = 50.0
                data_quality = DataQuality.FALLBACK

        if is_daytime is None:
            now_hour = datetime.now(timezone.utc).hour
            eff_is_daytime = 6 <= now_hour < 18
        else:
            eff_is_daytime = is_daytime

        log_with_context(
            logger,
            logging.INFO,
            "Calculating atmospheric dispersion hazard corridor",
            context={
                "latitude": latitude,
                "longitude": longitude,
                "frp_mw": frp_mw,
                "wind_speed_ms": wind.speed_ms,
                "wind_direction_from_label": wind.direction_from_label,
                "downwind_direction_label": wind.downwind_direction_label,
                "data_quality": data_quality.value,
            },
        )

        return AtmosphericDispersionEngine.calculate_dispersion(
            latitude=latitude,
            longitude=longitude,
            frp_mw=frp_mw or 50.0,
            wind=wind,
            release_height_m=release_height_m,
            cloud_cover_pct=cloud_cover_pct,
            is_daytime=eff_is_daytime,
            max_distance_km=max_distance_km,
            data_quality=data_quality,
        )

    def evaluate_dispersion_for_coordinates(
        self,
        latitude: float,
        longitude: float,
        frp_mw: float = 50.0,
        release_height_m: float = 15.0,
        is_daytime: bool = True,
        custom_wind_speed_ms: float | None = None,
        custom_wind_direction_deg: float | None = None,
        allow_cached_weather: bool = True,
    ) -> AtmosphericDispersionResult:
        """Alias for calculate_dispersion."""
        return self.calculate_dispersion(
            latitude=latitude,
            longitude=longitude,
            frp_mw=frp_mw,
            release_height_m=release_height_m,
            custom_wind_speed_ms=custom_wind_speed_ms,
            custom_wind_direction_deg=custom_wind_direction_deg,
            is_daytime=is_daytime,
            allow_cached_weather=allow_cached_weather,
        )

    def evaluate_event_dispersion(
        self,
        event_id: str,
        latitude: float,
        longitude: float,
        frp_mw: float | None = None,
        release_height_m: float | None = None,
        max_distance_km: float | None = None,
    ) -> AtmosphericDispersionResult:
        """Calculate downwind hazard corridor coupled to a specific thermal event."""
        now_hour = datetime.now(timezone.utc).hour
        is_daytime = 6 <= now_hour < 18

        try:
            weather = self.weather_service.get_weather(latitude=latitude, longitude=longitude)
            wind = weather.wind
            cloud_cover_pct = weather.atmosphere.cloud_cover_pct
            data_quality = weather.data_quality
        except Exception as exc:
            log_with_context(
                logger,
                logging.WARNING,
                "Weather service unavailable for event dispersion; using neutral fallback",
                context={
                    "event_id": event_id,
                    "latitude": latitude,
                    "longitude": longitude,
                    "error": str(exc),
                },
            )
            wind = build_wind_vector(speed_ms=3.0, direction_from_deg=270.0)
            cloud_cover_pct = 50.0
            data_quality = DataQuality.FALLBACK

        return AtmosphericDispersionEngine.calculate_dispersion(
            latitude=latitude,
            longitude=longitude,
            frp_mw=frp_mw or 50.0,
            wind=wind,
            event_id=event_id,
            release_height_m=release_height_m,
            cloud_cover_pct=cloud_cover_pct,
            is_daytime=is_daytime,
            max_distance_km=max_distance_km,
            data_quality=data_quality,
        )

    def evaluate_dispersion_for_event(
        self,
        event_id: str,
        latitude: float,
        longitude: float,
        frp_mw: float = 50.0,
        release_height_m: float = 15.0,
    ) -> AtmosphericDispersionResult:
        """Alias for evaluate_event_dispersion."""
        return self.evaluate_event_dispersion(
            event_id=event_id,
            latitude=latitude,
            longitude=longitude,
            frp_mw=frp_mw,
            release_height_m=release_height_m,
        )



# Global singleton dispersion service instance
_default_dispersion_service: AtmosphericDispersionService | None = None


def get_dispersion_service(settings: Settings | None = None) -> AtmosphericDispersionService:
    """Get canonical AtmosphericDispersionService singleton instance."""
    global _default_dispersion_service
    if settings is not None:
        return AtmosphericDispersionService(settings=settings)
    if _default_dispersion_service is None:
        _default_dispersion_service = AtmosphericDispersionService()
    return _default_dispersion_service
