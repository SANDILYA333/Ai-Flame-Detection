"""Canonical domain models and schemas for Atmospheric Dispersion & Downwind Hazard Intelligence (Phase 3)."""

from enum import StrEnum
from pydantic import Field

from packages.schemas.common import BaseDomainModel, Coordinate, UtcDatetime
from packages.schemas.weather import DataQuality, WindVector


class PasquillStabilityClass(StrEnum):
    """Pasquill-Gifford atmospheric stability classification."""

    A = "A"  # Very Unstable (high solar insolation, light winds)
    B = "B"  # Moderately Unstable
    C = "C"  # Slightly Unstable
    D = "D"  # Neutral (overcast day/night, or moderate-high winds)
    E = "E"  # Slightly Stable (nighttime, moderate clouds)
    F = "F"  # Moderately Stable (clear night, light winds)


class DispersionSamplePoint(BaseDomainModel):
    """Spatial cross-section sample along downwind trajectory."""

    downwind_distance_km: float = Field(
        ...,
        ge=0.0,
        description="Downwind distance from incident origin in kilometers",
    )
    centerline_point: Coordinate = Field(
        ...,
        description="Geographic coordinate along downwind plume centerline",
    )
    left_boundary_point: Coordinate = Field(
        ...,
        description="Geographic coordinate of left lateral hazard boundary",
    )
    right_boundary_point: Coordinate = Field(
        ...,
        description="Geographic coordinate of right lateral hazard boundary",
    )
    sigma_y_m: float = Field(
        ...,
        ge=0.0,
        description="Horizontal crosswind dispersion standard deviation in meters",
    )
    sigma_z_m: float = Field(
        ...,
        ge=0.0,
        description="Vertical dispersion standard deviation in meters",
    )
    lateral_width_km: float = Field(
        ...,
        ge=0.0,
        description="Total modeled lateral hazard width at this downwind step (km)",
    )
    relative_concentration: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Normalized relative ground-level concentration [0.0 (negligible) to 1.0 (peak)]",
    )


class DispersionSummary(BaseDomainModel):
    """Aggregate parameters and physical descriptors of the modeled hazard corridor."""

    model_name: str = Field(
        default="Gaussian Atmospheric Dispersion (Briggs Parameterization)",
        description="Atmospheric dispersion methodology used",
    )
    is_engineering_approximation: bool = Field(
        default=True,
        description="Explicit notice that model is an engineering approximation for situational awareness",
    )
    stability_class: PasquillStabilityClass = Field(
        ...,
        description="Estimated Pasquill-Gifford atmospheric stability class (A-F)",
    )
    stability_rationale: str = Field(
        ...,
        description="Explanation of how stability was inferred from meteorological inputs",
    )
    effective_release_height_m: float = Field(
        ...,
        ge=0.0,
        description="Effective plume release height in meters",
    )
    source_strength_proxy: float = Field(
        ...,
        ge=0.0,
        description="Relative emission source strength proxy derived from FRP",
    )
    max_hazard_distance_km: float = Field(
        ...,
        ge=0.0,
        description="Maximum modeled downwind hazard corridor extent in kilometers",
    )
    max_hazard_width_km: float = Field(
        ...,
        ge=0.0,
        description="Maximum lateral hazard width across the corridor in kilometers",
    )
    plume_angle_deg: float = Field(
        ...,
        ge=0.0,
        le=360.0,
        description="Downwind transport azimuth in degrees (0-360°)",
    )
    calm_stagnation_flag: bool = Field(
        default=False,
        description="Whether atmospheric stagnation/calm wind broadened the dispersion envelope",
    )


class AtmosphericDispersionResult(BaseDomainModel):
    """Canonical domain model representing atmospheric dispersion hazard around an incident."""

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
