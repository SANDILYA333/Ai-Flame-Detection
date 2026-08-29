"""Canonical Persistent Source domain model."""

import math

from pydantic import Field, field_validator, model_validator

from packages.schemas.common import (
    BaseDomainModel,
    BoundingBox,
    Coordinate,
    UtcDatetime,
)
from packages.schemas.enums import PersistenceState


class PersistentSource(BaseDomainModel):
    """Canonical representation of a persistent or recurring thermal source.

    A persistent source represents a longer-lived spatial entity associated
    with repeated thermal events over time (e.g. gas flare, industrial kiln).

    IMPORTANT ARCHITECTURAL INVARIANTS:
    - Source identity is distinct and decoupled from any event_id.
    - Persistence is an OBSERVED TEMPORAL CHARACTERISTIC, not proof of flare,
      facility type, or physical causation.
    - No classification logic or persistence thresholds are hard-coded.
    """

    source_id: str = Field(
        ...,
        min_length=1,
        description="Unique canonical identifier for persistent thermal source.",
    )
    linked_event_ids: list[str] = Field(
        ...,
        min_length=1,
        description="List of unique event IDs associated with source.",
    )
    total_event_count: int = Field(
        ...,
        ge=1,
        description="Total count of associated events (matches linked_event_ids).",
    )
    centroid_geometry: Coordinate = Field(
        ...,
        description="Representative spatial centroid coordinate of source.",
    )
    first_seen_at: UtcDatetime = Field(
        ...,
        description="Timestamp of earliest observation in UTC.",
    )
    last_seen_at: UtcDatetime = Field(
        ...,
        description="Timestamp of latest observation in UTC.",
    )
    active_days_count: int = Field(
        ...,
        ge=1,
        description="Number of distinct calendar days with thermal activity.",
    )
    persistence_state: PersistenceState = Field(
        ...,
        description="Observed persistence classification.",
    )
    persistence_configuration_id: str = Field(
        ...,
        min_length=1,
        description="Identifier of persistence scoring configuration contract.",
    )
    persistence_configuration_version: str = Field(
        ...,
        min_length=1,
        description="Version string of persistence scoring configuration.",
    )

    # Optional descriptive and lineage attributes
    bounding_box: BoundingBox | None = Field(
        None,
        description="Spatial bounding envelope encompassing associated events.",
    )
    persistence_run_id: str | None = Field(
        None,
        min_length=1,
        description="Lineage pipeline run ID that computed persistence.",
    )
    recurrence_ratio: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Observed activity ratio over observation window (0-1).",
    )
    notes: str | None = Field(
        None,
        description="Operational or diagnostic notes regarding the source.",
    )

    @field_validator("linked_event_ids", mode="after")
    @classmethod
    def _validate_unique_event_ids(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("Persistent source must link to at least one event ID.")
        cleaned = [e.strip() for e in v if e and e.strip()]
        if len(cleaned) != len(v):
            raise ValueError("linked_event_ids cannot contain empty or blank strings.")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("linked_event_ids must contain unique identifiers.")
        return cleaned

    @field_validator("recurrence_ratio", mode="after")
    @classmethod
    def _validate_finite_optional(cls, v: float | None) -> float | None:
        if v is not None and not math.isfinite(v):
            raise ValueError("recurrence_ratio must be finite.")
        return v

    @model_validator(mode="after")
    def _validate_source_invariants(self) -> "PersistentSource":
        if self.last_seen_at < self.first_seen_at:
            raise ValueError(
                f"last_seen_at ({self.last_seen_at}) cannot precede "
                f"first_seen_at ({self.first_seen_at})."
            )
        if self.total_event_count != len(self.linked_event_ids):
            raise ValueError(
                f"total_event_count ({self.total_event_count}) must match "
                f"length of linked_event_ids ({len(self.linked_event_ids)})."
            )
        return self
