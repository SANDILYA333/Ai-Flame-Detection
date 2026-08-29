"""Canonical Thermal Event domain model."""

import math

from pydantic import Field, field_validator, model_validator

from packages.schemas.common import (
    BaseDomainModel,
    BoundingBox,
    Coordinate,
    UtcDatetime,
)


class Event(BaseDomainModel):
    """Canonical representation of a thermal event formed by clustering detections.

    An event represents a spatio-temporal cluster of individual detections
    believed to correspond to a coherent physical heating episode.

    IMPORTANT ARCHITECTURAL INVARIANTS:
    - centroid_geometry is an event representation, NOT exact facility location.
    - No clustering parameters (radius, time gap) are hard-coded in this model.
    - An event must retain its member detection references for provenance.
    """

    event_id: str = Field(
        ...,
        min_length=1,
        description="Unique canonical identifier for the thermal event.",
    )
    detection_ids: list[str] = Field(
        ...,
        min_length=1,
        description="List of unique detection identifiers composing event.",
    )
    detection_count: int = Field(
        ...,
        ge=1,
        description="Total count of member detections (matches detection_ids).",
    )
    started_at: UtcDatetime = Field(
        ...,
        description="Earliest acquisition timestamp among detections in UTC.",
    )
    ended_at: UtcDatetime = Field(
        ...,
        description="Latest acquisition timestamp among detections in UTC.",
    )
    centroid_geometry: Coordinate = Field(
        ...,
        description="Representative spatial centroid of the event cluster.",
    )
    formation_configuration_id: str = Field(
        ...,
        min_length=1,
        description="Identifier of event formation configuration contract used.",
    )
    formation_configuration_version: str = Field(
        ...,
        min_length=1,
        description="Version string of event formation algorithm/configuration.",
    )

    # Optional descriptive summary and lineage fields
    bounding_box: BoundingBox | None = Field(
        None,
        description="Spatial bounding envelope encompassing member detections.",
    )
    formation_run_id: str | None = Field(
        None,
        min_length=1,
        description="Lineage pipeline run identifier that formed this event.",
    )
    duration_seconds: float | None = Field(
        None,
        ge=0.0,
        description="Duration of the event in seconds (ended_at - started_at).",
    )
    mean_frp_mw: float | None = Field(
        None,
        ge=0.0,
        description="Mean Fire Radiative Power across detections in MW.",
    )
    max_frp_mw: float | None = Field(
        None,
        ge=0.0,
        description="Maximum Fire Radiative Power across detections in MW.",
    )
    notes: str | None = Field(
        None,
        description="Operational or diagnostic notes on event formation.",
    )

    @field_validator("detection_ids", mode="after")
    @classmethod
    def _validate_unique_detection_ids(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("Event must contain at least one detection ID.")
        cleaned = [d.strip() for d in v if d and d.strip()]
        if len(cleaned) != len(v):
            raise ValueError("detection_ids cannot contain empty or blank strings.")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("detection_ids must contain unique identifiers.")
        return cleaned

    @field_validator("duration_seconds", "mean_frp_mw", "max_frp_mw", mode="after")
    @classmethod
    def _validate_finite_optional(cls, v: float | None) -> float | None:
        if v is not None and not math.isfinite(v):
            raise ValueError("Numeric metrics must be finite.")
        return v

    @model_validator(mode="after")
    def _validate_event_invariants(self) -> "Event":
        if self.ended_at < self.started_at:
            raise ValueError(
                f"ended_at ({self.ended_at}) cannot precede "
                f"started_at ({self.started_at})."
            )
        if self.detection_count != len(self.detection_ids):
            raise ValueError(
                f"detection_count ({self.detection_count}) must match "
                f"number of detection_ids ({len(self.detection_ids)})."
            )
        return self
