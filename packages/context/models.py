"""Canonical models for normalized external context features and matching rules."""

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator

from packages.schemas.common import BaseDomainModel, BoundingBox, Coordinate
from packages.schemas.enums import ContextType


class SpatialMatchRule(StrEnum):
    """Spatial relationship evaluation rule for context association."""

    PROXIMITY_RADIUS = "proximity_radius"
    CONTAINMENT_ENVELOPE = "containment_envelope"


class ContextFeature(BaseDomainModel):
    """Normalized canonical representation of an external contextual feature.

    Represents an infrastructure parcel, industrial plant, power plant,
    administrative boundary, or land-cover zone retrieved from external
    providers (e.g. OpenStreetMap, WRI Global Power Plant Database, GADM).
    """

    feature_id: str = Field(
        ...,
        min_length=1,
        description="Unique provider feature identifier (e.g. 'osm_way_12345').",
    )
    provider: str = Field(
        ...,
        min_length=1,
        description="Originating data provider or organization (e.g. 'osm', 'wri').",
    )
    dataset_name: str = Field(
        ...,
        min_length=1,
        description="Dataset identifier (e.g. 'planet_osm_polygon', 'wri_power').",
    )
    dataset_version: str = Field(
        ...,
        min_length=1,
        description="Dataset release version or snapshot tag.",
    )
    context_type: ContextType = Field(
        ...,
        description="Classified contextual land-use or infrastructure category.",
    )
    geometry: Coordinate = Field(
        ...,
        description="Representative coordinate (e.g. centroid or point).",
    )
    facility_name: str | None = Field(
        None,
        description="Human-readable name of the facility or feature if available.",
    )
    bounding_box: BoundingBox | None = Field(
        None,
        description="Bounding envelope if the external feature is a polygon.",
    )
    valid_from: datetime | None = Field(
        None,
        description="UTC start of temporal validity. None indicates always valid.",
    )
    valid_to: datetime | None = Field(
        None,
        description="UTC end of temporal validity. None indicates open-ended.",
    )
    raw_metadata: dict[str, str] | None = Field(
        None,
        description="Normalized key-value tags from the external source.",
    )

    @field_validator("valid_to", mode="after")
    @classmethod
    def _validate_temporal_order(
        cls, v: datetime | None, info: object
    ) -> datetime | None:
        return v
