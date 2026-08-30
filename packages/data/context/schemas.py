"""Raw schemas and diagnostic reporting models for external context ingestion."""

import math
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from packages.context.models import ContextFeature
from packages.schemas.common import BaseDomainModel


class RawContextRow(BaseModel):
    """Validation schema for a tabular context record (e.g. power plants catalog)."""

    model_config = ConfigDict(
        frozen=True,
        extra="allow",  # Preserve additional provider attributes
        str_strip_whitespace=True,
    )

    latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Feature centroid latitude in WGS-84 decimal degrees.",
    )
    longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Feature centroid longitude in WGS-84 decimal degrees.",
    )
    facility_name: str | None = Field(
        None,
        description="Human-readable facility name.",
    )
    facility_id: str | None = Field(
        None,
        description="Provider-specific feature identifier.",
    )
    facility_type: str | None = Field(
        None,
        description="Sector or industry classification (e.g. 'Power', 'Refinery').",
    )
    primary_fuel: str | None = Field(
        None,
        description="Primary fuel or energy source (e.g. 'Coal', 'Gas', 'Oil').",
    )
    capacity_mw: float | None = Field(
        None,
        ge=0.0,
        description="Electrical or thermal production capacity in MW.",
    )
    country: str | None = Field(
        None,
        description="3-letter or 2-letter country code.",
    )
    valid_from: str | None = Field(
        None,
        description="Start date or year of operation.",
    )
    valid_to: str | None = Field(
        None,
        description="Decommissioning or closure date if applicable.",
    )

    @field_validator("latitude", "longitude", "capacity_mw", mode="after")
    @classmethod
    def _validate_finite(cls, v: float | None) -> float | None:
        if v is not None and not math.isfinite(v):
            raise ValueError("Numeric measurement must be finite.")
        return v


class RawContextFeatureError(BaseDomainModel):
    """Structured diagnostic representation of a malformed contextual feature."""

    item_index: int = Field(
        ...,
        ge=0,
        description="0-indexed position of feature in source input.",
    )
    feature_id: str | None = Field(
        None,
        description="Provider feature identifier if available.",
    )
    field_name: str | None = Field(
        None,
        description="Specific attribute/field causing failure if known.",
    )
    error_message: str = Field(
        ...,
        min_length=1,
        description="Detailed diagnostic error message.",
    )
    raw_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Original raw feature payload for provenance audit.",
    )


class ContextIngestionReport(BaseDomainModel):
    """Diagnostic batch report for external context dataset ingestion."""

    provider: str = Field(..., min_length=1)
    dataset_name: str = Field(..., min_length=1)
    dataset_version: str = Field(..., min_length=1)
    total_items: int = Field(..., ge=0)
    valid_count: int = Field(..., ge=0)
    error_count: int = Field(..., ge=0)
    valid_features: list[ContextFeature] = Field(default_factory=list)
    errors: list[RawContextFeatureError] = Field(default_factory=list)
