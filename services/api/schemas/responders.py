"""FastAPI schemas for emergency responders and notification workflows."""

from pydantic import BaseModel, ConfigDict, Field

from packages.schemas.responders import (
    ChannelDeliveryStatus,
    ChannelResult,
    EmergencyResponder,
    EscalationDecision,
    EscalationState,
    EscalationType,
    EventResponseRecommendation,
    NotificationAction,
    NotificationChannel,
    NotificationMode,
    NotificationRequest,
    NotificationResponse,
    NotificationStatus,
    ResponderType,
    ResponseActivityRecord,
    ResponsePriority,
)

__all__ = [
    "ChannelDeliveryStatus",
    "ChannelResult",
    "EmergencyResponder",
    "EscalationDecision",
    "EscalationState",
    "EscalationType",
    "EventResponseRecommendation",
    "NotificationAction",
    "NotificationChannel",
    "NotificationMode",
    "NotificationRequest",
    "NotificationResponse",
    "NotificationStatus",
    "ResponderType",
    "ResponseActivityRecord",
    "ResponseActivityResponse",
    "ResponsePriority",
]


class ResponseActivityResponse(BaseModel):
    """Container schema for returning a list of response activity audit records."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str = Field(description="Target thermal event ID")
    total_records: int = Field(description="Total count of historical response actions")
    records: list[ResponseActivityRecord] = Field(
        default_factory=list,
        description="Chronological audit records of analyst notifications",
    )
