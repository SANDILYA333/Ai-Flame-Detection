"""Pydantic API schemas for Weather & Wind endpoints (Phase 1 & 2)."""

from pydantic import BaseModel, Field

from packages.schemas.common import Coordinate, UtcDatetime
from packages.schemas.weather import (
    AtmosphereData,
    DataQuality,
    DataStatus,
    WeatherForecastPoint,
    WeatherProviderInfo,
    WindVector,
)


class WeatherResponse(BaseModel):
    """Canonical API response contract for weather and wind observations."""

    location: Coordinate = Field(
        ...,
        description="Geographic coordinate of observation",
    )
    observed_at: UtcDatetime = Field(
        ...,
        description="Observation / model run epoch",
    )
    retrieved_at: UtcDatetime = Field(
        ...,
        description="Time data was fetched by the system",
    )
    data_status: DataStatus = Field(
        ...,
        description="Freshness status (LIVE, CACHED, UNAVAILABLE)",
    )
    data_quality: DataQuality = Field(
        default=DataQuality.LIVE,
        description="Quality assurance status (LIVE, CACHED, FALLBACK, UNAVAILABLE)",
    )
    atmosphere: AtmosphereData = Field(
        ...,
        description="Atmospheric conditions",
    )
    wind: WindVector = Field(
        ...,
        description="Wind speed, directional angles, cardinal labels, and decomposed vector",
    )
    forecast: list[WeatherForecastPoint] = Field(
        default_factory=list,
        description="Short-term forecast trajectory points",
    )
    provider: WeatherProviderInfo = Field(
        ...,
        description="Meteorological provider provenance",
    )


class EventWeatherResponse(BaseModel):
    """Event-coupled meteorological context response."""

    event_id: str = Field(
        ...,
        description="Canonical thermal anomaly event identifier",
    )
    weather: WeatherResponse = Field(
        ...,
        description="Meteorological conditions at the event coordinate",
    )
    enriched_at: UtcDatetime = Field(
        ...,
        description="Timestamp when event was coupled with weather context",
    )
