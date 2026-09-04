"""Canonical domain models for emergency responders and notification workflows."""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ResponderType(StrEnum):
    """Categorical type of emergency responder resource."""

    FIRE_STATION = "FIRE_STATION"
    CHEMICAL_FIRE_STATION = "CHEMICAL_FIRE_STATION"
    INDUSTRIAL_FIRE_SAFETY = "INDUSTRIAL_FIRE_SAFETY"
    MUNICIPAL_FIRE_STATION = "MUNICIPAL_FIRE_STATION"
    HOSPITAL = "HOSPITAL"
    BURN_ICU = "BURN_ICU"
    BURN_INTENSIVE_CARE_HOSPITAL = "BURN_INTENSIVE_CARE_HOSPITAL"
    SPECIALIZED_HAZMAT_UNIT = "SPECIALIZED_HAZMAT_UNIT"
    PORT_EMERGENCY_SERVICES = "PORT_EMERGENCY_SERVICES"
    NDRF = "NDRF"
    NDRF_DISASTER_BATTALION = "NDRF_DISASTER_BATTALION"
    OTHER = "OTHER"


class ResponsePriority(StrEnum):
    """Deterministic operational response priority tier."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    MONITOR_ONLY = "MONITOR_ONLY"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class NotificationAction(StrEnum):
    """Operational action requested by an analyst."""

    NOTIFY = "NOTIFY"
    MOBILIZE = "MOBILIZE"


class NotificationStatus(StrEnum):
    """Execution status of an emergency notification/mobilization request."""

    READY = "READY"
    CONFIRMING = "CONFIRMING"
    PROCESSING = "PROCESSING"
    SIMULATED = "SIMULATED"
    SENT = "SENT"
    PROVIDER_ACCEPTED = "PROVIDER_ACCEPTED"
    DELIVERED = "DELIVERED"
    PARTIAL = "PARTIAL"
    DUPLICATE_SUPPRESSED = "DUPLICATE_SUPPRESSED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    CANCELLED = "CANCELLED"


class NotificationMode(StrEnum):
    """Execution environment mode for notification actions."""

    SIMULATED = "SIMULATED"
    LIVE = "LIVE"


class EscalationState(StrEnum):
    """Authoritative backend escalation state according to frozen operational policy."""

    NO_ESCALATION = "NO_ESCALATION"
    ADMIN_REVIEW_REQUIRED = "ADMIN_REVIEW_REQUIRED"
    AUTOMATIC_ESCALATION = "AUTOMATIC_ESCALATION"


class EscalationDecision(BaseModel):
    """Authoritative backend emergency escalation decision payload."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str = Field(description="Target thermal event identifier")
    confidence: float | None = Field(
        default=None,
        description="Calibrated model confidence score in [0.0, 1.0]",
    )
    operational_priority: ResponsePriority = Field(
        description="Authoritative operational attention / response priority"
    )
    escalation_state: EscalationState = Field(
        description="Authoritative escalation policy state"
    )
    automatic: bool = Field(
        default=False,
        description="Whether automatic emergency escalation is permitted",
    )
    medical_escalation: bool = Field(
        default=False,
        description="Whether medical/ambulance escalation is required",
    )
    policy_drivers: list[str] = Field(
        default_factory=list,
        description="Explicit policy rationale explaining why the decision was made",
    )
    evaluated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Decision evaluation timestamp in UTC",
    )
    policy_version: str = Field(
        default="v1.0.0",
        description="Version identifier of the authoritative escalation policy",
    )


class EscalationType(StrEnum):
    """Trigger source for emergency response escalation."""

    NO_ESCALATION = "NO_ESCALATION"
    ADMIN_REVIEW = "ADMIN_REVIEW"
    ADMIN_CONFIRMED = "ADMIN_CONFIRMED"
    HIGH_CONFIDENCE_AUTO = "HIGH_CONFIDENCE_AUTO"
    CRITICAL_MEDICAL = "CRITICAL_MEDICAL"


class NotificationChannel(StrEnum):
    """Delivery communication channels for emergency alerts."""

    SMS = "SMS"
    WHATSAPP = "WHATSAPP"


class ChannelDeliveryStatus(StrEnum):
    """Outcome status for a specific notification channel dispatch."""

    SENT = "SENT"
    PROVIDER_ACCEPTED = "PROVIDER_ACCEPTED"
    DELIVERED = "DELIVERED"
    SIMULATED = "SIMULATED"
    DUPLICATE_SUPPRESSED = "DUPLICATE_SUPPRESSED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    PROVIDER_REJECTED = "PROVIDER_REJECTED"
    UNKNOWN = "UNKNOWN"


class ChannelResult(BaseModel):
    """Result of an alert delivery attempt on a single communication channel."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    channel: NotificationChannel = Field(description="Target delivery channel")
    status: ChannelDeliveryStatus = Field(description="Channel delivery status")
    recipient: str = Field(description="Destination phone number")
    destination_masked: str | None = Field(
        default=None, description="Masked destination phone number for privacy/audit"
    )
    message: str = Field(description="Channel status or summary message")
    provider: str | None = Field(
        default=None,
        description="Messaging provider used (e.g., 'fast2sms', 'richautomate')",
    )
    provider_message_id: str | None = Field(
        default=None, description="External provider message identifier"
    )
    correlation_id: str | None = Field(
        default=None, description="Distributed correlation identifier"
    )
    submitted_at: datetime | None = Field(
        default=None, description="Timestamp when submitted to provider"
    )
    delivered_at: datetime | None = Field(
        default=None, description="Timestamp when confirmed delivered"
    )
    retry_count: int = Field(
        default=0, description="Retry attempts executed for this channel"
    )
    error_details: str | None = Field(
        default=None, description="Detailed error description if failed"
    )


class EmergencyResponder(BaseModel):
    """Structured representation of an emergency responder resource."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(description="Unique responder identifier")
    name: str = Field(description="Official name of emergency facility or unit")
    type: ResponderType = Field(description="Responder classification type")
    city: str = Field(description="City or local district")
    state: str = Field(description="State or province")
    latitude: float = Field(
        description="Geographic latitude in WGS-84 decimal degrees",
        ge=-90.0,
        le=90.0,
    )
    longitude: float = Field(
        description="Geographic longitude in WGS-84 decimal degrees",
        ge=-180.0,
        le=180.0,
    )
    distance_meters: float = Field(
        description="Calculated geodesic distance from event origin in meters",
        ge=0.0,
    )
    formatted_distance: str = Field(
        description="Human-readable distance string (e.g., '4.2 km')"
    )
    estimated_eta_minutes: int | None = Field(
        default=None,
        description=(
            "Modeled estimated arrival time in minutes based on emergency response transit. "
            "Set to None when road transit is not physically applicable (e.g. offshore)."
        ),
        ge=0,
    )
    formatted_eta: str = Field(
        description="Human-readable ETA string (e.g., '~8 min', 'Offshore Transit Required')"
    )
    capabilities: list[str] = Field(
        default_factory=list,
        description="Verified operational capabilities",
    )
    phone: str = Field(default="N/A", description="Emergency contact phone number")
    jurisdiction: str = Field(
        default="Regional Emergency Jurisdiction",
        description="Operational jurisdiction",
    )
    source: str = Field(
        default="National Disaster Response & Industrial Infrastructure Registry",
        description="Provenance data source",
    )
    recommendation_reason: str = Field(
        description="Explainable rationale for recommending this responder"
    )
    plume_impact_status: str = Field(
        default="UNAVAILABLE",
        description="Plume hazard corridor intersection status",
    )


class EventResponseRecommendation(BaseModel):
    """Deterministic response recommendation package for a thermal event."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str = Field(description="Target thermal event ID")
    response_priority: ResponsePriority = Field(
        description="Deterministic operational response priority"
    )
    priority_reason: str = Field(
        description="Operational rationale for priority assignment"
    )
    confidence: float | None = Field(
        default=None,
        description="Calibrated model confidence score in [0.0, 1.0]",
    )
    auto_escalation_eligible: bool = Field(
        default=False,
        description="Whether event meets automatic demo escalation criteria (>98% or CRITICAL)",
    )
    auto_escalation_triggered: bool = Field(
        default=False,
        description="Whether automatic escalation has been executed for this event",
    )
    escalation_type: EscalationType | None = Field(
        default=None,
        description="Active or evaluated escalation type",
    )
    is_routine_flare: bool = Field(
        default=False,
        description="Whether event is classified as routine operational flaring",
    )
    is_abstained_or_unknown: bool = Field(
        default=False,
        description="Whether event classification is unknown or abstained",
    )
    medical_escalation: bool = Field(
        default=False,
        description="Whether medical / ambulance emergency escalation is indicated",
    )
    policy_drivers: list[str] = Field(
        default_factory=list,
        description="List of policy rule drivers explaining escalation state",
    )
    escalation_decision: EscalationDecision | None = Field(
        default=None,
        description="Full authoritative backend escalation decision contract",
    )
    responders: list[EmergencyResponder] = Field(
        default_factory=list,
        description="Ranked list of relevant emergency responders",
    )
    nearest_hospitals: list[EmergencyResponder] = Field(
        default_factory=list,
        description="Top 2 nearest hospital / burn trauma responders",
    )
    nearest_fire_stations: list[EmergencyResponder] = Field(
        default_factory=list,
        description="Top 2 nearest fire station responders",
    )
    specialized_responders: list[EmergencyResponder] = Field(
        default_factory=list,
        description="Applicable specialized responders (e.g. Hazmat, Port Emergency)",
    )
    ndrf_responders: list[EmergencyResponder] = Field(
        default_factory=list,
        description="Applicable regional NDRF disaster battalions",
    )
    recommendation_basis: list[str] = Field(
        default_factory=list,
        description="List of evidence signals backing recommendation",
    )
    evaluated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Evaluation timestamp",
    )


class NotificationRequest(BaseModel):
    """Payload sent by an analyst or system to initiate a notification."""

    model_config = ConfigDict(extra="forbid")

    responder_id: str = Field(description="Target responder identifier")
    action: NotificationAction = Field(
        default=NotificationAction.NOTIFY,
        description="Action to perform",
    )
    mode: NotificationMode = Field(
        default=NotificationMode.SIMULATED,
        description="Notification mode (SIMULATED for demo)",
    )
    recipient_phone: str | None = Field(
        default=None,
        description="Destination phone number for demo alert (+91 or E.164)",
    )
    channels: list[NotificationChannel] = Field(
        default_factory=lambda: [NotificationChannel.SMS, NotificationChannel.WHATSAPP],
        description="Target notification channels",
    )
    escalation_type: EscalationType = Field(
        default=EscalationType.ADMIN_CONFIRMED,
        description="Trigger classification for escalation",
    )
    analyst_notes: str | None = Field(
        default=None,
        description="Optional operational notes from the analyst",
    )


class NotificationResponse(BaseModel):
    """Structured response returned after processing notification."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    notification_id: str = Field(
        description="Unique deterministic notification record ID"
    )
    event_id: str = Field(description="Associated thermal event ID")
    responder_id: str = Field(description="Recipient responder ID")
    responder_name: str = Field(description="Recipient responder name")
    action: NotificationAction = Field(description="Action executed")
    status: NotificationStatus = Field(description="Outcome status (e.g., SIMULATED)")
    mode: NotificationMode = Field(description="Mode of operation")
    escalation_type: EscalationType = Field(
        default=EscalationType.ADMIN_CONFIRMED,
        description="Escalation type that triggered this notification",
    )
    trigger_source: EscalationType | None = Field(
        default=None,
        description="Authoritative trigger source classification",
    )
    recipient_phone: str | None = Field(
        default=None, description="Destination phone number"
    )
    destination_masked: str | None = Field(
        default=None, description="Masked destination phone number"
    )
    correlation_id: str | None = Field(
        default=None, description="Correlation identifier for distributed tracing"
    )
    channels: list[ChannelResult] = Field(
        default_factory=list,
        description="Per-channel delivery results (SMS, WhatsApp)",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Execution timestamp",
    )
    message: str = Field(description="Human-readable status confirmation message")


class ResponseActivityRecord(BaseModel):
    """Historical audit record of an analyst or automatic response action."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    notification_id: str = Field(description="Notification identifier")
    event_id: str = Field(description="Thermal event ID")
    responder_id: str = Field(description="Responder ID")
    responder_name: str = Field(description="Responder name")
    responder_type: ResponderType = Field(description="Responder type")
    action: NotificationAction = Field(description="Action performed")
    status: NotificationStatus = Field(description="Execution status")
    mode: NotificationMode = Field(description="Operation mode")
    escalation_type: EscalationType = Field(
        default=EscalationType.ADMIN_CONFIRMED,
        description="Trigger source for the notification",
    )
    trigger_source: EscalationType | None = Field(
        default=None,
        description="Authoritative trigger source classification",
    )
    recipient_phone: str | None = Field(
        default=None, description="Recipient phone number"
    )
    destination_masked: str | None = Field(
        default=None, description="Masked destination phone number"
    )
    correlation_id: str | None = Field(
        default=None, description="Correlation identifier for distributed tracing"
    )
    channels: list[ChannelResult] = Field(
        default_factory=list,
        description="Per-channel delivery breakdown",
    )
    timestamp: datetime = Field(description="Record timestamp")
    analyst_notes: str | None = Field(default=None, description="Analyst notes")
