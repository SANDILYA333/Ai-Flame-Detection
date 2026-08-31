"""Readiness endpoint request and response contracts."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DependencyStatus(StrEnum):
    """Categorical status of a system dependency."""

    READY = "ready"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"


class DependencyHealth(BaseModel):
    """Health and readiness diagnostic info for an individual dependency."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: DependencyStatus = Field(
        ...,
        description="Operational readiness state of the dependency",
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Non-secret diagnostic metadata",
    )


class ReadinessResponse(BaseModel):
    """Canonical response model for the /ready dependency readiness endpoint."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: DependencyStatus = Field(
        ...,
        description="Overall service readiness state",
    )
    service: str = Field(
        default="sih26162-api",
        description="Canonical service identifier",
    )
    version: str = Field(
        default="0.1.0",
        description="Application package version",
    )
    environment: str = Field(
        ...,
        description="Active runtime environment mode",
    )
    dependencies: dict[str, DependencyHealth] = Field(
        ...,
        description="Health and connectivity breakdown by dependency",
    )
