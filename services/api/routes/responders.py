"""FastAPI route handlers for emergency responders and notification workflows."""

from fastapi import APIRouter

from services.api.schemas.responders import (
    EscalationDecision,
    EventResponseRecommendation,
    NotificationMode,
    NotificationRequest,
    NotificationResponse,
    ResponseActivityResponse,
)
from services.api.services.escalation import EscalationPolicyService
from services.api.services.responders import (
    NotificationAuditService,
    ResponseRecommendationService,
)

router = APIRouter(prefix="/events", tags=["emergency-response"])


@router.get(
    "/{event_id}/escalation",
    response_model=EscalationDecision,
    operation_id="get_event_escalation_decision",
    summary="Retrieve authoritative emergency escalation policy decision",
    description=(
        "Evaluates deterministic backend escalation policy based on calibrated confidence "
        "and operational attention, returning actionable escalation state and policy drivers."
    ),
)
def get_event_escalation_decision(event_id: str) -> EscalationDecision:
    """Retrieve authoritative emergency escalation policy decision for an event."""
    return EscalationPolicyService.evaluate_event(event_id)


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
def get_event_responders(
    event_id: str,
    demo_phone: str | None = None,
) -> EventResponseRecommendation:
    """Retrieve prioritized emergency responder recommendations for an event."""
    return ResponseRecommendationService.get_recommendations_for_event(
        event_id, demo_phone=demo_phone
    )


@router.post(
    "/{event_id}/response/notify",
    response_model=NotificationResponse,
    operation_id="notify_responder",
    summary="Submit analyst-confirmed notification or mobilization request",
    description=(
        "Processes an analyst-confirmed emergency response notification. "
        "Dispatches multi-channel alerts (SMS, WhatsApp) in live or simulated mode."
    ),
)
def notify_responder(
    event_id: str,
    payload: NotificationRequest,
) -> NotificationResponse:
    """Submit an analyst-confirmed notification or mobilization request."""
    return NotificationAuditService.process_notification(event_id, payload)


@router.post(
    "/{event_id}/response/escalate",
    response_model=NotificationResponse,
    operation_id="escalate_event_response",
    summary="Trigger automatic or manual multi-channel emergency escalation",
    description=(
        "Executes high-confidence or critical medical escalation workflow "
        "with multi-channel SMS and WhatsApp dispatch and audit trail."
    ),
)
def escalate_event_response(
    event_id: str,
    payload: NotificationRequest,
) -> NotificationResponse:
    """Trigger emergency escalation workflow for an event."""
    return NotificationAuditService.process_notification(event_id, payload)


@router.get(
    "/{event_id}/response/activity",
    response_model=ResponseActivityResponse,
    operation_id="get_event_response_activity",
    summary="Retrieve response audit history and session activity",
    description=("Returns historical log of analyst notifications for an event."),
)
def get_event_response_activity(event_id: str) -> ResponseActivityResponse:
    """Retrieve response audit history and session activity for an event."""
    records = NotificationAuditService.get_activity_for_event(event_id)
    return ResponseActivityResponse(
        event_id=event_id,
        total_records=len(records),
        records=records,
    )


@router.post(
    "/{event_id}/response/auto-escalate",
    response_model=list[NotificationResponse],
    operation_id="auto_escalate_event",
    summary="Backend-controlled automatic emergency response escalation evaluation",
    description=(
        "Evaluates event confidence (>98%) and CRITICAL medical escalation policy, "
        "automatically dispatching alerts to nearest fire and hospital responders if eligible."
    ),
)
def auto_escalate_event(
    event_id: str,
    mode: NotificationMode = NotificationMode.SIMULATED,
) -> list[NotificationResponse]:
    """Execute backend-controlled automatic escalation evaluation and dispatch."""
    return NotificationAuditService.evaluate_and_trigger_automatic_escalation(
        event_id, mode=mode
    )
