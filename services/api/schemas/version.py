"""Version endpoint request and response contracts."""

from pydantic import BaseModel, ConfigDict, Field


class VersionContracts(BaseModel):
    """Canonical data and ML contract versions."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    features: str = Field(
        ...,
        description="Active feature catalog contract version",
    )
    targets: str = Field(
        ...,
        description="Active target catalog contract version",
    )


class VersionResponse(BaseModel):
    """Canonical response model for the /version contract endpoint."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    service: str = Field(
        default="sih26162-api",
        description="Canonical service identifier",
    )
    version: str = Field(
        default="0.1.0",
        description="Application package version",
    )
    api_version: str = Field(
        default="v1",
        description="API semantic version interface",
    )
    environment: str = Field(
        ...,
        description="Active runtime environment mode",
    )
    contracts: VersionContracts = Field(
        ...,
        description="Domain and machine learning contract versions",
    )
