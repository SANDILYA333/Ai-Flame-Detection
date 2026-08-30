"""FastAPI routes for canonical thermal events (API-006)."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query

from packages.schemas.intelligence import IntelligenceResult
from services.api.schemas.events import (
    EventDetailResponse,
    EventEvidenceResponse,
    EventsResponse,
    EventTimelineResponse,
)
from services.api.services.events import EventQueryService

router = APIRouter(prefix="/events", tags=["events"])


@router.get(
    "",
    response_model=EventsResponse,
    operation_id="get_events",
    summary="Retrieve and filter canonical thermal events",
    description=(
        "Returns a paginated list of derived thermal events. "
        "Allows spatial, temporal, classification, and persistence filtering."
    ),
)
def get_events(
    min_lat: Annotated[
        float | None, Query(description="Min bounding box latitude", ge=-90, le=90)
    ] = None,
    max_lat: Annotated[
        float | None, Query(description="Max bounding box latitude", ge=-90, le=90)
    ] = None,
    min_lon: Annotated[
        float | None, Query(description="Min bounding box longitude", ge=-180, le=180)
    ] = None,
    max_lon: Annotated[
        float | None, Query(description="Max bounding box longitude", ge=-180, le=180)
    ] = None,
    start_time: Annotated[datetime | None, Query(description="Start time")] = None,
    end_time: Annotated[datetime | None, Query(description="End time")] = None,
    status: Annotated[
        str | None, Query(description="Persistence state filter (e.g., 'CANDIDATE')")
    ] = None,
    classification_state: Annotated[
        str | None, Query(description="Target classification (e.g., 'industrial')")
    ] = None,
    limit: Annotated[
        int, Query(description="Maximum records to return", ge=1, le=1000)
    ] = 50,
    offset: Annotated[int, Query(description="Number of records to skip", ge=0)] = 0,
) -> EventsResponse:
    """Retrieve and filter canonical thermal events."""
    return EventQueryService.query_events(
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        start_time=start_time,
        end_time=end_time,
        status=status,
        classification_state=classification_state,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{event_id}",
    response_model=EventDetailResponse,
    operation_id="get_event",
    summary="Retrieve canonical thermal event detail",
    description="Returns full canonical detail for a specific thermal event.",
)
def get_event(event_id: str) -> EventDetailResponse:
    """Retrieve canonical thermal event detail."""
    return EventQueryService.get_event(event_id)


@router.get(
    "/{event_id}/timeline",
    response_model=EventTimelineResponse,
    operation_id="get_event_timeline",
    summary="Retrieve canonical thermal event timeline",
    description="Returns deterministic chronological detection sequence.",
)
def get_event_timeline(event_id: str) -> EventTimelineResponse:
    """Retrieve canonical event timeline."""
    return EventQueryService.get_event_timeline(event_id)


@router.get(
    "/{event_id}/evidence",
    response_model=EventEvidenceResponse,
    operation_id="get_event_evidence",
    summary="Retrieve canonical thermal event evidence",
    description="Returns scientific reference and contextual evidence.",
)
def get_event_evidence(event_id: str) -> EventEvidenceResponse:
    """Retrieve canonical thermal event evidence."""
    return EventQueryService.get_event_evidence(event_id)


@router.get(
    "/{event_id}/intelligence",
    response_model=IntelligenceResult,
    operation_id="get_event_intelligence",
    summary="Retrieve canonical thermal event intelligence",
    description="Returns intelligence inference result, calibration, and abstention.",
)
def get_event_intelligence(event_id: str) -> IntelligenceResult:
    """Retrieve canonical thermal event intelligence."""
    return EventQueryService.get_event_intelligence(event_id)
