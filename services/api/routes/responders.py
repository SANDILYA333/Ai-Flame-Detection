"""FastAPI route handlers for emergency responders and notification workflows."""

from fastapi import APIRouter

from services.api.schemas.responders import (
    EventResponseRecommendation,
    NotificationRequest,
    NotificationResponse,
    ResponseActivityResponse,
)
from services.api.services.responders import (
    NotificationAuditService,
    ResponseRecommendationService,
)

router = APIRouter(prefix="/events", tags=["emergency-response"])


@router.get(
    "/{event_id}/responders",
    response_model=EventResponseRecommendation,
    operation_id="get_event_responders",
    summary="Retrieve prioritized emergency responder recommendations",
    description=(
        "Calculates geodesic distance, modeled response ETA, and applies "
        "deterministic policy to identify nearest relevant emergency resources."
    ),
)
def get_event_responders(event_id: str) -> EventResponseRecommendation:
    """Retrieve prioritized emergency responder recommendations for an event."""
    return ResponseRecommendationService.get_recommendations_for_event(event_id)


@router.post(
    "/{event_id}/response/notify",
    response_model=NotificationResponse,
    operation_id="notify_responder",
    summary="Submit analyst-confirmed notification or mobilization request",
    description=(
        "Processes an analyst-confirmed emergency response notification. "
        "In prototype/demo mode, returns a safe SIMULATED notification record."
    ),
)
def notify_responder(
    event_id: str,
    payload: NotificationRequest,
) -> NotificationResponse:
    """Submit an analyst-confirmed notification or mobilization request."""
    return NotificationAuditService.process_notification(event_id, payload)


@router.get(
    "/{event_id}/response/activity",
    response_model=ResponseActivityResponse,
    operation_id="get_event_response_activity",
    summary="Retrieve response audit history and session activity",
    description=(
        "Returns historical log of analyst notifications for an event."
    ),
)
def get_event_response_activity(event_id: str) -> ResponseActivityResponse:
    """Retrieve response audit history and session activity for an event."""
    records = NotificationAuditService.get_activity_for_event(event_id)
    return ResponseActivityResponse(
        event_id=event_id,
        total_records=len(records),
        records=records,
    )
