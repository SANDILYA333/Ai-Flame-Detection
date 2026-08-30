"""Health endpoint response contracts."""

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """Canonical response model for the /health liveness endpoint."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: str = Field(
        default="ok",
        description="Current health status of the API service",
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
        description="Active runtime environment mode (e.g. development, test)",
    )
