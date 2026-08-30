"""Schemas for API-006 Events."""

from datetime import datetime

from pydantic import BaseModel, Field

from packages.schemas.common import BaseDomainModel


class EventResponse(BaseModel):
    """API representation of a canonical thermal event."""

    event_id: str = Field(
        ..., description="Unique canonical identifier for the event."
    )
    started_at: datetime = Field(
        ..., description="Earliest detection acquisition timestamp in UTC."
    )
    ended_at: datetime = Field(
        ..., description="Latest detection acquisition timestamp in UTC."
    )
    duration_seconds: float | None = Field(
        None, description="Duration of the event in seconds."
    )
    centroid_latitude: float = Field(
        ..., description="Representative spatial centroid latitude."
    )
    centroid_longitude: float = Field(
        ..., description="Representative spatial centroid longitude."
    )
    detection_count: int = Field(
        ..., description="Total count of member detections."
    )
    mean_frp_mw: float | None = Field(
        None, description="Mean Fire Radiative Power across detections in MW."
    )
    max_frp_mw: float | None = Field(
        None, description="Maximum Fire Radiative Power across detections in MW."
    )
    classification_state: str | None = Field(
        None, description="Assigned classification label if adjudicated."
    )
    persistence_state: str | None = Field(
        None, description="Assigned persistence state if tracked."
    )


class EventPagination(BaseDomainModel):
    """Pagination metadata for event collections."""

    total_count: int = Field(
        ..., description="Total number of events matching the filters."
    )
    limit: int = Field(..., description="Maximum number of records returned.")
    offset: int = Field(..., description="Number of records skipped.")
    has_next: bool = Field(
        ..., description="Whether additional records exist beyond this page."
    )


class EventDetailResponse(BaseModel):
    """Detailed canonical event response (API-007)."""

    event_id: str = Field(..., description="Unique canonical identifier for the event.")
    geometry: dict[str, str | list[float]] = Field(
        ..., description="GeoJSON Point representation of the event centroid."
    )
    started_at: datetime = Field(
        ..., description="Earliest detection acquisition timestamp in UTC."
    )
    ended_at: datetime = Field(
        ..., description="Latest detection acquisition timestamp in UTC."
    )
    duration_seconds: float | None = Field(
        None, description="Duration of the event in seconds."
    )
    detection_count: int = Field(
        ..., description="Total count of member detections."
    )
    context_status: str = Field(
        ..., description="Contextual evidence status (AVAILABLE/UNAVAILABLE)."
    )
    intelligence_status: str | None = Field(
        None, description="Assigned classification label if adjudicated."
    )


class TimelineObservation(BaseModel):
    """Single observation in an event's timeline."""

    timestamp: datetime = Field(..., description="Acquisition timestamp in UTC.")
    detection_id: str = Field(..., description="Canonical detection identifier.")
    latitude: float = Field(..., description="Detection centroid latitude.")
    longitude: float = Field(..., description="Detection centroid longitude.")
    source: str = Field(..., description="Observation source provider.")
    frp_mw: float | None = Field(None, description="Fire Radiative Power (MW).")
    confidence: str | None = Field(None, description="Source-provided confidence.")


class EventTimelineResponse(BaseModel):
    """Timeline response for an event (API-008)."""

    event_id: str = Field(..., description="Unique canonical identifier for the event.")
    started_at: datetime = Field(
        ..., description="Earliest detection acquisition timestamp in UTC."
    )
    ended_at: datetime = Field(
        ..., description="Latest detection acquisition timestamp in UTC."
    )
    timeline: list[TimelineObservation] = Field(
        ..., description="Chronological sequence of detections."
    )


class EventsResponse(BaseDomainModel):
    """Response wrapper for a paginated collection of canonical thermal events."""

    service: str = Field(default="sih26162-api", description="Service identifier.")
    pagination: EventPagination = Field(..., description="Pagination metadata.")
    events: list[EventResponse] = Field(..., description="List of thermal events.")
