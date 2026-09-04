"""Pydantic API schemas for Atmospheric Dispersion & Downwind Hazard Intelligence endpoints (Phase 3)."""

from pydantic import BaseModel, Field

from packages.schemas.common import Coordinate, UtcDatetime
from packages.schemas.dispersion import (
    DispersionSamplePoint,
    DispersionSummary,
)
from packages.schemas.weather import DataQuality, WindVector


class DispersionCalculationRequest(BaseModel):
    """Payload for on-demand atmospheric dispersion calculation."""

    latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Latitude of release / thermal event origin (-90 to +90)",
    )
    longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Longitude of release / thermal event origin (-180 to +180)",
    )
    frp_mw: float | None = Field(
        default=None,
        ge=0.0,
        description="Fire Radiative Power in MW (used to scale buoyant plume height and emissions proxy)",
    )
    release_height_m: float | None = Field(
        default=None,
        ge=0.0,
        description="Explicit stack/emission release height in meters",
    )
    custom_wind_speed_ms: float | None = Field(
        default=None,
        ge=0.0,
        description="Override wind speed in m/s (bypasses live meteorological wind speed)",
    )
    custom_wind_direction_deg: float | None = Field(
        default=None,
        ge=0.0,
        le=360.0,
        description="Override wind direction in meteorological degrees (bypasses live wind direction)",
    )
    is_daytime: bool | None = Field(
        default=None,
        description="Override day/night indicator for solar insolation / stability estimation",
    )
    max_distance_km: float | None = Field(
        default=None,
        ge=0.5,
        le=50.0,
        description="Override downwind calculation horizon in kilometers",
    )


class DispersionCalculationResponse(BaseModel):
    """Canonical API response contract for atmospheric dispersion evaluations."""

    source_location: Coordinate = Field(
        ...,
        description="Origin coordinate of the thermal/industrial release",
    )
    event_id: str | None = Field(
        default=None,
        description="Coupled thermal anomaly event ID if applicable",
    )
    evaluated_at: UtcDatetime = Field(
        ...,
        description="Timestamp when dispersion evaluation was generated",
    )
    wind: WindVector = Field(
        ...,
        description="Meteorological wind conditions applied to the model",
    )
    dispersion: DispersionSummary = Field(
        ...,
        description="High-level parameters and stability summary",
    )
    trajectory: list[DispersionSamplePoint] = Field(
        default_factory=list,
        description="Downwind centerline and lateral cross-section sampling points",
    )
    data_quality: DataQuality = Field(
        default=DataQuality.LIVE,
        description="Meteorological data quality assurance inherited from weather layer",
    )
    model_confidence: str = Field(
        default="MEDIUM",
        description="Confidence classification (HIGH, MEDIUM, LOW, DEGRADED_CALM)",
    )
