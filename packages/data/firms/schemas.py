"""Raw NASA FIRMS source record schemas and parsing error models."""

import math
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from packages.schemas.common import BaseDomainModel
from packages.schemas.detection import Detection


class RawFirmsCsvRow(BaseModel):
    """Validation schema for raw, unnormalized NASA FIRMS CSV row.

    Captures vendor-specific column names and applies initial type/boundary checks
    before canonical domain normalization.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="allow",  # Allow vendor extra metadata without rejecting row
        str_strip_whitespace=True,
    )

    latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Observation latitude in WGS-84 decimal degrees (-90 to 90).",
    )
    longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Observation longitude in WGS-84 decimal degrees (-180 to 180).",
    )
    acq_date: str = Field(
        ...,
        min_length=8,
        max_length=10,
        description="Acquisition date string (e.g. 'YYYY-MM-DD').",
    )
    acq_time: str = Field(
        ...,
        min_length=1,
        max_length=6,
        description="Acquisition time string (e.g. 'HHMM' or 'HH:MM').",
    )
    satellite: str = Field(
        ...,
        min_length=1,
        description="Observing satellite/platform identifier.",
    )
    instrument: str | None = Field(
        None,
        description="Sensor instrument name (e.g. 'VIIRS', 'MODIS').",
    )
    confidence: str | None = Field(
        None,
        description="Source confidence string or numeric score as string.",
    )
    version: str | None = Field(
        None,
        description="Source data product processing version.",
    )
    bright_ti4: float | None = Field(
        None,
        ge=0.0,
        description="VIIRS I-4 band brightness temperature in Kelvin.",
    )
    bright_ti5: float | None = Field(
        None,
        ge=0.0,
        description="VIIRS I-5 band brightness temperature in Kelvin.",
    )
    brightness: float | None = Field(
        None,
        ge=0.0,
        description="MODIS Channel 21/22 brightness temperature in Kelvin.",
    )
    bright_t31: float | None = Field(
        None,
        ge=0.0,
        description="MODIS Channel 31 brightness temperature in Kelvin.",
    )
    frp: float | None = Field(
        None,
        ge=0.0,
        description="Fire Radiative Power in Megawatts (MW).",
    )
    scan: float | None = Field(
        None,
        gt=0.0,
        description="Along-scan pixel dimension in kilometers.",
    )
    track: float | None = Field(
        None,
        gt=0.0,
        description="Along-track pixel dimension in kilometers.",
    )
    daynight: str | None = Field(
        None,
        description="Daytime ('D') or Nighttime ('N') observation indicator.",
    )

    @field_validator(
        "latitude",
        "longitude",
        "bright_ti4",
        "bright_ti5",
        "brightness",
        "bright_t31",
        "frp",
        "scan",
        "track",
        mode="after",
    )
    @classmethod
    def _validate_finite(cls, v: float | None) -> float | None:
        if v is not None and not math.isfinite(v):
            raise ValueError("Numeric measurement must be finite (not NaN or Inf).")
        return v


class FirmsRowError(BaseDomainModel):
    """Structured diagnostic representation of a malformed FIRMS record row."""

    row_index: int = Field(
        ...,
        ge=0,
        description="0-indexed line number in source input.",
    )
    field_name: str | None = Field(
        None,
        description="Specific column/field name causing failure if known.",
    )
    raw_value: str | None = Field(
        None,
        description="Raw string value that failed validation.",
    )
    error_message: str = Field(
        ...,
        min_length=1,
        description="Detailed diagnostic error message.",
    )
    raw_row_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Full raw row dictionary for auditability.",
    )


class FirmsParseReport(BaseDomainModel):
    """Structured result of a batch FIRMS fixture parsing operation."""

    source_snapshot_id: str = Field(..., min_length=1)
    total_rows: int = Field(..., ge=0)
    valid_count: int = Field(..., ge=0)
    error_count: int = Field(..., ge=0)
    valid_detections: list[Detection] = Field(default_factory=list)
    row_errors: list[FirmsRowError] = Field(default_factory=list)
