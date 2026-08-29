"""Canonical Context and Facility domain models."""

import math

from pydantic import Field, field_validator

from packages.schemas.common import BaseDomainModel, BoundingBox, Coordinate
from packages.schemas.enums import ContextType, EvidenceAvailabilityState


class ContextEvidence(BaseDomainModel):
    """Canonical representation of geospatial context and nearby infrastructure.

    Context captures external geospatial features (e.g. OpenStreetMap
    industrial zones, refineries, power stations, land-cover classifications)
    to provide contextual evidence for thermal events.

    IMPORTANT ARCHITECTURAL INVARIANTS:
    - Context is CONTEXTUAL EVIDENCE, not the prediction target or label.
    - Proximity to an industrial facility does NOT prove an industrial fire.
    - Absence in OSM does NOT prove facility absence; state must be explicit.
    - distance_to_event_meters is spatial only and does NOT imply attribution.
    """

    context_id: str = Field(
        ...,
        min_length=1,
        description="Unique canonical identifier for context observation.",
    )
    source_type: str = Field(
        ...,
        min_length=1,
        description="Provider of context data (e.g. 'osm', 'landcover').",
    )
    context_type: ContextType = Field(
        ...,
        description="Classified contextual infrastructure/land-use category.",
    )
    geometry: Coordinate = Field(
        ...,
        description="Representative coordinate of contextual facility/parcel.",
    )
    availability_state: EvidenceAvailabilityState = Field(
        ...,
        description="Availability status of the contextual evidence source.",
    )

    # Optional infrastructure and provenance details
    source_snapshot_id: str | None = Field(
        None,
        min_length=1,
        description="Identifier of context dataset snapshot used.",
    )
    external_facility_id: str | None = Field(
        None,
        min_length=1,
        description="External source identifier (e.g. 'osm_way_123456').",
    )
    facility_name: str | None = Field(
        None,
        description="Name of the facility or infrastructure feature if named.",
    )
    bounding_box: BoundingBox | None = Field(
        None,
        description="Bounding envelope of contextual feature if polygonal.",
    )
    distance_to_event_meters: float | None = Field(
        None,
        ge=0.0,
        description="Distance to associated event centroid in meters.",
    )
    raw_metadata: dict[str, str] | None = Field(
        None,
        description="Normalized key-value tags from contextual source.",
    )

    @field_validator("distance_to_event_meters", mode="after")
    @classmethod
    def _validate_finite_optional(cls, v: float | None) -> float | None:
        if v is not None and not math.isfinite(v):
            raise ValueError("distance_to_event_meters must be finite.")
        return v
