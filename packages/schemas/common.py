"""Common domain models, coordinate representations, and validation helpers."""

import math
from datetime import datetime
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


def _validate_tz_aware(dt: datetime) -> datetime:
    """Validate that datetime is timezone-aware."""
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError(
            "Datetime must be timezone-aware (e.g. UTC). Naive datetimes are rejected."
        )
    return dt


UtcDatetime = Annotated[datetime, AfterValidator(_validate_tz_aware)]


class BaseDomainModel(BaseModel):
    """Base model for all canonical domain entities.

    Enforces immutability, forbids extraneous fields, and strips whitespace.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
        validate_default=True,
    )


class Coordinate(BaseDomainModel):
    """Canonical geographic coordinate representation in EPSG:4326."""

    latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Latitude in decimal degrees (-90.0 to 90.0)",
    )
    longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Longitude in decimal degrees (-180.0 to 180.0)",
    )

    @field_validator("latitude", "longitude", mode="after")
    @classmethod
    def _validate_finite(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("Coordinate value must be finite (not NaN or Inf).")
        return v


class BoundingBox(BaseDomainModel):
    """Canonical geographic bounding box representation in EPSG:4326."""

    min_latitude: float = Field(..., ge=-90.0, le=90.0)
    min_longitude: float = Field(..., ge=-180.0, le=180.0)
    max_latitude: float = Field(..., ge=-90.0, le=90.0)
    max_longitude: float = Field(..., ge=-180.0, le=180.0)

    @field_validator(
        "min_latitude", "min_longitude", "max_latitude", "max_longitude", mode="after"
    )
    @classmethod
    def _validate_finite(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("Bounding box coordinate values must be finite.")
        return v

    @model_validator(mode="after")
    def _validate_bounds(self) -> "BoundingBox":
        if self.min_latitude > self.max_latitude:
            raise ValueError(
                f"min_latitude ({self.min_latitude}) cannot exceed "
                f"max_latitude ({self.max_latitude})."
            )
        if self.min_longitude > self.max_longitude:
            raise ValueError(
                f"min_longitude ({self.min_longitude}) cannot exceed "
                f"max_longitude ({self.max_longitude})."
            )
        return self


class ProvenanceReference(BaseDomainModel):
    """Lineage reference for domain records."""

    source: str = Field(..., min_length=1, description="Source provider identifier")
    source_snapshot_id: str | None = Field(
        None, min_length=1, description="External snapshot identifier"
    )
    pipeline_run_id: str | None = Field(
        None, min_length=1, description="Execution run identifier"
    )
    configuration_id: str | None = Field(
        None, min_length=1, description="Configuration contract identifier"
    )
    configuration_version: str | None = Field(
        None, min_length=1, description="Configuration version"
    )
