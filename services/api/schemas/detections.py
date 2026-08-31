"""Detection endpoint request and response contracts."""

from pydantic import BaseModel, ConfigDict, Field

from packages.schemas.detection import Detection


class DetectionPagination(BaseModel):
    """Pagination metadata for detection queries."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    total_count: int = Field(
        ...,
        ge=0,
        description="Total count of matching detection records before pagination",
    )
    limit: int = Field(
        ...,
        ge=1,
        description="Maximum page limit applied to query",
    )
    offset: int = Field(
        ...,
        ge=0,
        description="Number of matching records skipped",
    )
    has_next: bool = Field(
        ...,
        description="Whether additional records exist beyond current page",
    )


class DetectionsResponse(BaseModel):
    """Canonical response envelope for GET /detections."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    service: str = Field(
        default="sih26162-api",
        description="Canonical service identifier",
    )
    pagination: DetectionPagination = Field(
        ...,
        description="Pagination metadata for current query result",
    )
    detections: list[Detection] = Field(
        ...,
        description="List of canonical remote sensing detection observations",
    )
