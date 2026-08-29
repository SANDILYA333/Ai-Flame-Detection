"""Canonical Detection domain model."""

import math

from pydantic import Field, field_validator

from packages.schemas.common import BaseDomainModel, Coordinate, UtcDatetime
from packages.schemas.enums import DayNight


class Detection(BaseDomainModel):
    """Canonical representation of a single remote-sensing thermal observation.

    This model represents a single observation from a satellite sensor (e.g.
    NASA FIRMS VIIRS/MODIS) normalized into canonical internal contracts without
    leaking vendor-specific naming conventions.
    """

    detection_id: str = Field(
        ...,
        min_length=1,
        description="Unique canonical identifier for the detection record.",
    )
    source: str = Field(
        ...,
        min_length=1,
        description="Identifier of observation source adapter (e.g. 'firms').",
    )
    source_snapshot_id: str = Field(
        ...,
        min_length=1,
        description="Identifier of source snapshot containing this record.",
    )
    acquired_at: UtcDatetime = Field(
        ...,
        description="Observation timestamp in UTC supplied by satellite sensor.",
    )
    geometry: Coordinate = Field(
        ...,
        description="Geographic point coordinate of observation pixel centroid.",
    )
    satellite: str = Field(
        ...,
        min_length=1,
        description="Observing satellite name (e.g. 'NOAA-20', 'Terra').",
    )
    instrument: str = Field(
        ...,
        min_length=1,
        description="Observing sensor instrument (e.g. 'VIIRS', 'MODIS').",
    )
    product_type: str = Field(
        ...,
        min_length=1,
        description="Product processing tier (e.g. 'nrt', 'standard', 'urt').",
    )
    product_version: str = Field(
        ...,
        min_length=1,
        description="Version string of the source data product.",
    )
    raw_hash: str = Field(
        ...,
        min_length=1,
        description="Cryptographic hash of raw record for deduplication.",
    )

    # Optional physical measurements
    frp_mw: float | None = Field(
        None,
        ge=0.0,
        description="Fire Radiative Power measured in megawatts (MW).",
    )
    brightness_ti4_k: float | None = Field(
        None,
        ge=0.0,
        description="Brightness temperature in Kelvin from TI4 band.",
    )
    brightness_ti5_k: float | None = Field(
        None,
        ge=0.0,
        description="Brightness temperature in Kelvin from TI5 band.",
    )
    confidence: str | None = Field(
        None,
        description="Source-provided confidence string or categorization.",
    )
    scan_km: float | None = Field(
        None,
        gt=0.0,
        description="Along-scan pixel dimension in kilometers.",
    )
    track_km: float | None = Field(
        None,
        gt=0.0,
        description="Along-track pixel dimension in kilometers.",
    )
    day_night: DayNight | None = Field(
        None,
        description="Daytime or nighttime observation indicator.",
    )

    @field_validator(
        "frp_mw",
        "brightness_ti4_k",
        "brightness_ti5_k",
        "scan_km",
        "track_km",
        mode="after",
    )
    @classmethod
    def _validate_finite_optional(cls, v: float | None) -> float | None:
        if v is not None and not math.isfinite(v):
            raise ValueError("Numeric measurement must be finite (not NaN or Inf).")
        return v
