"""Canonical domain models for emergency responders and notification workflows."""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ResponderType(StrEnum):
    """Categorical type of emergency responder resource."""

    FIRE_STATION = "FIRE_STATION"
    CHEMICAL_FIRE_STATION = "CHEMICAL_FIRE_STATION"
    HOSPITAL = "HOSPITAL"
    BURN_ICU = "BURN_ICU"
    NDRF = "NDRF"
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
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class NotificationMode(StrEnum):
    """Execution environment mode for notification actions."""

    SIMULATED = "SIMULATED"
    LIVE = "LIVE"


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
    estimated_eta_minutes: int = Field(
        description=(
            "Modeled estimated arrival time in minutes based on ~45 km/h "
            "emergency response speed"
        ),
        ge=0,
    )
    formatted_eta: str = Field(
        description="Human-readable ETA string (e.g., '~8 min')"
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
    is_routine_flare: bool = Field(
        default=False,
        description="Whether event is classified as routine operational flaring",
    )
    is_abstained_or_unknown: bool = Field(
        default=False,
        description="Whether event classification is unknown or abstained",
    )
    responders: list[EmergencyResponder] = Field(
        default_factory=list,
        description="Ranked list of relevant emergency responders",
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
    """Payload sent by an analyst to initiate a confirmed notification."""

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
    status: NotificationStatus = Field(
        description="Outcome status (e.g., SIMULATED)"
    )
    mode: NotificationMode = Field(description="Mode of operation")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Execution timestamp",
    )
    message: str = Field(
        description="Human-readable status confirmation message"
    )


class ResponseActivityRecord(BaseModel):
    """Historical audit record of an analyst emergency response action."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    notification_id: str = Field(description="Notification identifier")
    event_id: str = Field(description="Thermal event ID")
    responder_id: str = Field(description="Responder ID")
    responder_name: str = Field(description="Responder name")
    responder_type: ResponderType = Field(description="Responder type")
    action: NotificationAction = Field(description="Action performed")
    status: NotificationStatus = Field(description="Execution status")
    mode: NotificationMode = Field(description="Operation mode")
    timestamp: datetime = Field(description="Record timestamp")
    analyst_notes: str | None = Field(default=None, description="Analyst notes")
