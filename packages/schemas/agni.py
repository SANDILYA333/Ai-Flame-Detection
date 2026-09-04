"""Canonical domain models and validation schemas for AGNI Voice Intelligence (Phase 2)."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AgniIntent(StrEnum):
    """Categorical intent for AGNI natural language voice commands (Phases 3-5)."""

    FILTER_THERMAL_EVENTS = "FILTER_THERMAL_EVENTS"
    FILTER_THERMAL_ANOMALIES = "FILTER_THERMAL_ANOMALIES"
    FILTER_SEVERITY = "FILTER_SEVERITY"
    FILTER_CATEGORY = "FILTER_CATEGORY"
    FILTER_STATE = "FILTER_STATE"
    FILTER_SECTOR = "FILTER_SECTOR"
    SEARCH = "SEARCH"
    SEARCH_INCIDENTS = "SEARCH_INCIDENTS"
    SELECT_INCIDENT = "SELECT_INCIDENT"
    MAP_ACTION = "MAP_ACTION"
    TOGGLE_LAYER = "TOGGLE_LAYER"
    SHOW_LAYER = "SHOW_LAYER"
    HIDE_LAYER = "HIDE_LAYER"
    OPEN_XAI = "OPEN_XAI"
    SHOW_RESPONDERS = "SHOW_RESPONDERS"
    SHOW_HAZARD = "SHOW_HAZARD"
    OPEN_DOSSIER = "OPEN_DOSSIER"
    CLEAR_FILTERS = "CLEAR_FILTERS"
    OPEN_SIMULATION_LAB = "OPEN_SIMULATION_LAB"
    MULTI_STEP = "MULTI_STEP"
    DISPATCH_PREVIEW = "DISPATCH_PREVIEW"
    CONFIRM_ACTION = "CONFIRM_ACTION"
    CANCEL_ACTION = "CANCEL_ACTION"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
    UNKNOWN = "UNKNOWN"



class AgniFilters(BaseModel):
    """Structured criteria for application filtering state."""

    model_config = ConfigDict(extra="ignore")

    classification: str | None = Field(
        default=None,
        description="Target classification: ALL, INDUSTRIAL, NON_INDUSTRIAL, UNKNOWN, REVIEW_REQUIRED",
    )
    priority: str | None = Field(
        default=None,
        description="Target operational priority: ALL, CRITICAL, HIGH, MEDIUM, LOW, REVIEW_REQUIRED",
    )
    severity: str | None = Field(
        default=None,
        description="Alias for priority / severity level (critical, high, medium, low)",
    )
    timeRange: str | None = Field(
        default=None,
        description="Target temporal window: 1h, 6h, 24h, 48h, 7d, All / 1H, 6H, 24H, 48H, 7D, ALL",
    )
    searchQuery: str | None = Field(
        default=None,
        description="Full-text search query string",
    )
    state: str | None = Field(
        default=None,
        description="Geographic region/state in India",
    )
    sector: str | None = Field(
        default=None,
        description="Industrial sector (e.g., Refinery & Petrochemicals, Iron & Steel, Coal Mining)",
    )
    category: str | None = Field(
        default=None,
        description="Specific anomaly category: accidental, routine, wildfire, crop, coal, glint, industrial",
    )
    industrial: bool | None = Field(
        default=None,
        description="Convenience boolean flag indicating industrial segregation",
    )


class AgniStructuredCommand(BaseModel):
    """Validated structured command output produced from voice transcript interpretation."""

    model_config = ConfigDict(extra="ignore")

    intent: AgniIntent = Field(
        description="Determined operational intent for the command",
    )
    filters: AgniFilters = Field(
        default_factory=AgniFilters,
        description="Structured filters to apply to application state",
    )
    selectedEventId: str | None = Field(
        default=None,
        description="Optional specific event ID to select",
    )
    incidentId: str | None = Field(
        default=None,
        description="Alias for selectedEventId",
    )
    targetCriterion: str | None = Field(
        default=None,
        description="Target selection heuristic: most_severe, highest_frp, nearest, first",
    )
    layerId: str | None = Field(
        default=None,
        description="Optional GIS layer ID to toggle/show/hide",
    )
    enabled: bool | None = Field(
        default=None,
        description="Whether layer is enabled or disabled when toggling",
    )
    basemap: str | None = Field(
        default=None,
        description="Target basemap style: satellite, dark, osm",
    )
    mapAction: str | None = Field(
        default=None,
        description="Map control action: RECENTER_INDIA, FIT_RESULTS, SET_BASEMAP, SET_VIEW_MODE, ZOOM_IN, ZOOM_OUT",
    )
    action: str | None = Field(
        default=None,
        description="Generic action identifier matching mapAction or command action",
    )
    viewMode: str | None = Field(
        default=None,
        description="Spatial view mode: 2D, 3D",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Model confidence score for the semantic interpretation",
    )
    requiresConfirmation: bool = Field(
        default=False,
        description="Whether ambiguous or consequential command requires operator confirmation",
    )
    isConsequential: bool = Field(
        default=False,
        description="Whether action triggers external workflow requiring preview and confirmation",
    )
    response: str | None = Field(
        default=None,
        description="Optional suggested verbal response text from interpreter",
    )
    entities: list[str] = Field(
        default_factory=list,
        description="Named entities recognized from natural language command",
    )
    steps: list["AgniStructuredCommand"] = Field(
        default_factory=list,
        description="Ordered sequence of sub-commands for multi-step execution",
    )
    executionTrace: list[str] = Field(
        default_factory=list,
        description="Operational step trace badges (e.g. Category -> Industrial)",
    )


class AgniContextPayload(BaseModel):
    """Compact snapshot of active application context provided to AGNI."""

    model_config = ConfigDict(extra="ignore")

    selectedEventId: str | None = None
    lastCommand: dict[str, Any] | None = None
    lastIntent: str | None = None
    lastFilters: dict[str, Any] | None = None
    activeFilters: dict[str, Any] = Field(default_factory=dict)
    activeLayers: dict[str, bool] = Field(default_factory=dict)
    visibleEventCount: int = 0
    totalEventCount: int = 0


class AgniCommandRequest(BaseModel):
    """Input payload for natural language voice command interpretation."""

    model_config = ConfigDict(extra="forbid")

    transcript: str = Field(
        min_length=1,
        max_length=500,
        description="Recognized voice transcript or typed natural language command",
    )
    context: AgniContextPayload | None = Field(
        default=None,
        description="Optional current application state context snapshot",
    )


class AgniCommandResponse(BaseModel):
    """Normalized response containing structured command and operational message."""

    model_config = ConfigDict(extra="forbid")

    command: AgniStructuredCommand
    message: str = Field(
        description="Concise operational confirmation or clarification message",
    )
    executionLatencyMs: float = Field(
        default=0.0,
        ge=0.0,
        description="Interpretation latency in milliseconds",
    )
    status: str = Field(
        default="interpreted",
        description="Execution status: interpreted, ambiguous, unsupported, fallback, error",
    )

