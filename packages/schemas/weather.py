"""Canonical domain models and schemas for Weather & Wind Intelligence (Phase 1 & 2).

Provides strongly-typed, validated domain models for meteorological observations,
cardinal compass directions, wind vector components, calm-wind classifications,
atmospheric parameters, short-term forecasts, and event weather enrichment.
"""

from enum import StrEnum
from pydantic import Field

from packages.schemas.common import BaseDomainModel, Coordinate, UtcDatetime


class DataStatus(StrEnum):
    """Operational data freshness and retrieval status."""

    LIVE = "LIVE"
    CACHED = "CACHED"
    UNAVAILABLE = "UNAVAILABLE"


class DataQuality(StrEnum):
    """Data quality and provenance assurance classification."""

    LIVE = "LIVE"
    CACHED = "CACHED"
    FALLBACK = "FALLBACK"
    UNAVAILABLE = "UNAVAILABLE"


class WindState(StrEnum):
    """Meteorological wind intensity classification based on Beaufort scale."""

    CALM = "CALM"          # < 0.5 m/s (< 1 knot, smoke rises vertically)
    LIGHT = "LIGHT"        # 0.5 - 3.3 m/s (light air / light breeze)
    MODERATE = "MODERATE"  # 3.4 - 7.9 m/s (gentle / moderate breeze)
    FRESH = "FRESH"        # 8.0 - 13.8 m/s (fresh / strong breeze)
    STRONG = "STRONG"      # 13.9 - 20.7 m/s (near gale / gale)
    GALE = "GALE"          # >= 20.8 m/s (severe gale / storm)


class WindVector(BaseDomainModel):
    """Normalized wind vector components, cardinal labels, and directional metrics.

    Meteorological convention:
    - direction_from_deg: Direction FROM which wind blows (0° = North, 90° = East, 180° = South, 270° = West).
    - direction_from_label: 16-point cardinal compass bearing FROM which wind blows (e.g. 'SW').
    - direction_to_deg: Downwind direction TOWARD which wind transports mass ((direction_from + 180) % 360).
    - downwind_direction_label: 16-point cardinal compass bearing for downwind transport (e.g. 'NE').
    - u_ms: Zonal (Eastward positive) component = -speed * sin(direction_from_rad).
    - v_ms: Meridional (Northward positive) component = -speed * cos(direction_from_rad).
    - is_calm: Flag indicating whether wind speed is below the calm threshold (< 0.5 m/s).
    - wind_state: Wind intensity category (CALM, LIGHT, MODERATE, FRESH, STRONG, GALE).
    """

    speed_ms: float = Field(
        ...,
        ge=0.0,
        description="Wind speed at 10m height in meters per second (m/s)",
    )
    direction_from_deg: float = Field(
        ...,
        ge=0.0,
        le=360.0,
        description="Meteorological direction FROM which the wind blows (0-360°)",
    )
    direction_from_label: str = Field(
        ...,
        description="16-point compass label FROM which wind originates (e.g. 'SW', 'N')",
    )
    direction_to_deg: float = Field(
        ...,
        ge=0.0,
        le=360.0,
        description="Downwind direction TOWARD which the wind travels (0-360°)",
    )
    downwind_direction_label: str = Field(
        ...,
        description="16-point compass label TOWARD which wind transports plume (e.g. 'NE', 'S')",
    )
    gust_ms: float | None = Field(
        default=None,
        ge=0.0,
        description="Wind gusts at 10m height in meters per second (m/s)",
    )
    u_ms: float = Field(
        ...,
        description="Zonal wind vector component (Eastward positive, m/s)",
    )
    v_ms: float = Field(
        ...,
        description="Meridional wind vector component (Northward positive, m/s)",
    )
    is_calm: bool = Field(
        default=False,
        description="Whether wind speed is below the calm threshold (< 0.5 m/s)",
    )
    wind_state: WindState = Field(
        default=WindState.LIGHT,
        description="Categorical wind intensity state",
    )


class AtmosphereData(BaseDomainModel):
    """Meteorological and atmospheric properties affecting combustion and dispersion."""

    temperature_c: float = Field(
        ...,
        description="Air temperature at 2m above ground in degrees Celsius (°C)",
    )
    relative_humidity_pct: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Relative humidity at 2m above ground (0-100%)",
    )
    surface_pressure_hpa: float | None = Field(
        default=None,
        ge=0.0,
        description="Atmospheric surface pressure in hectopascals (hPa)",
    )
    precipitation_mm: float | None = Field(
        default=0.0,
        ge=0.0,
        description="Precipitation rate / accumulation in millimeters (mm)",
    )
    cloud_cover_pct: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Total cloud cover percentage (0-100%)",
    )
    boundary_layer_height_m: float | None = Field(
        default=None,
        ge=0.0,
        description="Atmospheric boundary layer mixing height in meters (m)",
    )
    soil_moisture_m3_m3: float | None = Field(
        default=None,
        ge=0.0,
        description="Surface volumetric soil moisture (m³/m³)",
    )


class WeatherForecastPoint(BaseDomainModel):
    """Discrete short-term forecast interval record."""

    forecast_time: UtcDatetime = Field(
        ...,
        description="Timestamp for which the forecast prediction applies",
    )
    horizon_hours: int = Field(
        ...,
        ge=0,
        description="Forecast lead time in hours from observation epoch",
    )
    atmosphere: AtmosphereData = Field(
        ...,
        description="Forecasted atmospheric conditions",
    )
    wind: WindVector = Field(
        ...,
        description="Forecasted wind vector and direction",
    )


class WeatherProviderInfo(BaseDomainModel):
    """Provenance and identity of the meteorological data provider."""

    name: str = Field(
        default="open-meteo",
        description="Identifier of the meteorological service provider",
    )
    model: str | None = Field(
        default=None,
        description="Numerical weather prediction model name (e.g. best_match, ecmwf_ifs)",
    )


class CanonicalWeatherData(BaseDomainModel):
    """Canonical internal weather and environmental data model.

    Serves as the single source of truth for real-time wind conditions,
    atmospheric parameters, and short-term forecasts across the platform.
    """

    location: Coordinate = Field(
        ...,
        description="Geographic coordinate where weather is observed/evaluated",
    )
    observed_at: UtcDatetime = Field(
        ...,
        description="Meteorological observation or model forecast timestamp",
    )
    retrieved_at: UtcDatetime = Field(
        ...,
        description="Timestamp when the data was ingested by the application",
    )
    data_status: DataStatus = Field(
        default=DataStatus.LIVE,
        description="Data freshness status: LIVE, CACHED, or UNAVAILABLE",
    )
    data_quality: DataQuality = Field(
        default=DataQuality.LIVE,
        description="Data quality assurance: LIVE, CACHED, FALLBACK, or UNAVAILABLE",
    )
    atmosphere: AtmosphereData = Field(
        ...,
        description="Current atmospheric state",
    )
    wind: WindVector = Field(
        ...,
        description="Current wind speed, direction, and vector decomposition",
    )
    forecast: list[WeatherForecastPoint] = Field(
        default_factory=list,
        description="Short-term weather forecast trajectory (6h, 12h, 24h horizons)",
    )
    provider: WeatherProviderInfo = Field(
        default_factory=lambda: WeatherProviderInfo(name="open-meteo"),
        description="Metadata describing data provider origin",
    )


class EventWeatherEnrichment(BaseDomainModel):
    """Enriched meteorological context attached to a thermal anomaly / fire event."""

    event_id: str = Field(
        ...,
        description="Unique identifier of the thermal anomaly event",
    )
    weather: CanonicalWeatherData = Field(
        ...,
        description="Canonical meteorological observation at event location and epoch",
    )
    enriched_at: UtcDatetime = Field(
        ...,
        description="Timestamp when weather context was coupled to the event",
    )
