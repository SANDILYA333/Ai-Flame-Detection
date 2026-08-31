"""API schemas for ML inference endpoints."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PredictionRequestBody(BaseModel):
    """Payload for point-in-time single feature inference request."""

    entity_id: str = Field(
        default="entity_inference",
        description="Identifier of the entity or event being evaluated.",
    )
    features: dict[str, Any] = Field(
        ...,
        description="Canonical feat_v1.0.0 feature key-value mapping.",
    )
    operating_mode: str = Field(
        default="HIGH_PRECISION",
        description="Target operating mode (HIGH_PRECISION, HIGH_RECALL, SELECTIVE).",
    )


class BatchPredictionRequestBody(BaseModel):
    """Payload for multi-sample batch inference request."""

    items: list[dict[str, Any]] = Field(
        ...,
        description="List of feature dictionaries.",
    )
    entity_ids: list[str] | None = Field(
        default=None,
        description="Optional list of corresponding entity identifiers.",
    )
    operating_mode: str = Field(
        default="HIGH_PRECISION",
        description="Target operating mode for all batch items.",
    )


class PredictionResponseBody(BaseModel):
    """Structured production prediction response."""

    entity_id: str = Field(..., description="Evaluated entity identifier.")
    operating_mode: str = Field(..., description="Operating mode applied.")
    model_name: str = Field(..., description="Underlying model architecture.")
    model_version: str = Field(..., description="Production model version.")
    feature_schema_version: str = Field(..., description="Feature schema version.")
    predicted_class: str = Field(..., description="Model predicted class.")
    assigned_class: str = Field(
        ..., description="Policy-authorized assigned class ('unknown' if abstained)."
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Model prediction confidence score."
    )
    threshold: float = Field(
        ..., ge=0.0, le=1.0, description="Abstention cutoff threshold."
    )
    class_probabilities: dict[str, float] = Field(
        default_factory=dict, description="Class probability distribution."
    )
    is_abstained: bool = Field(..., description="True if prediction was abstained.")
    review_required: bool = Field(..., description="True if manual review is required.")
    abstention_reason: str | None = Field(
        None, description="Reason code if abstention was triggered."
    )
    feature_count: int = Field(..., ge=0, description="Number of features evaluated.")
    inference_timestamp: datetime = Field(
        ..., description="UTC timestamp of inference."
    )
    latency_ms: float = Field(..., ge=0.0, description="Inference execution latency.")


class BatchPredictionResponseBody(BaseModel):
    """Response container for batch predictions."""

    predictions: list[PredictionResponseBody] = Field(
        ..., description="Ordered list of prediction results."
    )
    total_count: int = Field(..., ge=0, description="Total evaluated items.")
    abstained_count: int = Field(..., ge=0, description="Count of abstained items.")
    operating_mode: str = Field(..., description="Operating mode used.")
