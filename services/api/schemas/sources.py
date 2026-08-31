"""Source status endpoint request and response contracts."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from packages.schemas.enums import SourceRole


class SourceOperationalMode(StrEnum):
    """Operational mode of the data source."""

    LIVE = "live"
    OFFLINE = "offline"
    HYBRID = "hybrid"


class SourceAvailabilityState(StrEnum):
    """Operational availability state of the data source."""

    CONFIGURED = "configured"
    OFFLINE_ONLY = "offline_only"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class SourceStatusItem(BaseModel):
    """Status metadata for an individual data source provider."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: str = Field(
        ...,
        description="Unique canonical source identifier",
    )
    name: str = Field(
        ...,
        description="Human-readable data source name",
    )
    provider: str = Field(
        ...,
        description="Providing organization or platform (e.g. NASA FIRMS, OSM)",
    )
    role: SourceRole = Field(
        ...,
        description="Canonical role in data processing or intelligence",
    )
    mode: SourceOperationalMode = Field(
        ...,
        description="Live, offline, or hybrid operating mode",
    )
    status: SourceAvailabilityState = Field(
        ...,
        description="Current operational availability state",
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Safe, non-secret diagnostic and capability metadata",
    )


class SourcesStatusResponse(BaseModel):
    """Canonical response model for GET /sources/status."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    service: str = Field(
        default="sih26162-api",
        description="Canonical service identifier",
    )
    environment: str = Field(
        ...,
        description="Active runtime environment mode",
    )
    sources: list[SourceStatusItem] = Field(
        ...,
        description="List of registered data sources and their operational status",
    )
