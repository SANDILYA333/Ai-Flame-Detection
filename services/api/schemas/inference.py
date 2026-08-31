"""API schemas for ML inference and FIRMS integration endpoints."""

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


class FirmsCsvPredictionRequestBody(BaseModel):
    """Payload for evaluating raw NASA FIRMS CSV data end-to-end."""

    csv_content: str = Field(
        ...,
        description="Raw NASA FIRMS CSV content containing satellite detections.",
    )
    operating_mode: str = Field(
        default="HIGH_PRECISION",
        description="Target operating mode (HIGH_PRECISION, HIGH_RECALL, SELECTIVE).",
    )


class FirmsMLPredictionResponseBody(BaseModel):
    """Structured response for a FIRMS thermal event prediction."""

    event_id: str = Field(..., description="Canonical event identifier.")
    source: str = Field(default="NASA_FIRMS", description="Data source name.")
    event_timestamp: datetime = Field(
        ..., description="Timestamp of the event started_at in UTC."
    )
    centroid_latitude: float = Field(..., description="Event centroid latitude.")
    centroid_longitude: float = Field(..., description="Event centroid longitude.")
    detection_count: int = Field(..., ge=1, description="Number of member detections.")
    max_frp_mw: float | None = Field(
        None, description="Max Fire Radiative Power across detections in MW."
    )
    operating_mode: str = Field(..., description="Operating mode applied.")
    feature_schema_version: str = Field(..., description="Feature schema version.")
    feature_count: int = Field(..., ge=0, description="Number of features extracted.")
    model_name: str = Field(..., description="Underlying model architecture.")
    model_version: str = Field(..., description="Production model version.")
    predicted_class: str = Field(..., description="Raw model predicted class.")
    assigned_class: str = Field(
        ..., description="Policy-authorized assigned class ('unknown' if abstained)."
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score.")
    threshold: float = Field(..., ge=0.0, le=1.0, description="Abstention threshold.")
    class_probabilities: dict[str, float] = Field(
        default_factory=dict, description="Class probability distribution."
    )
    is_abstained: bool = Field(..., description="True if prediction was abstained.")
    review_required: bool = Field(..., description="True if human review is required.")
    abstention_reason: str | None = Field(None, description="Reason code if abstained.")
    feature_extraction_latency_ms: float = Field(
        ..., ge=0.0, description="Feature extraction latency in ms."
    )
    inference_latency_ms: float = Field(
        ..., ge=0.0, description="Model inference latency in ms."
    )
    total_latency_ms: float = Field(
        ..., ge=0.0, description="Total pipeline latency in ms."
    )


class FirmsCsvPredictionResponseBody(BaseModel):
    """Response container for FIRMS CSV evaluation."""

    results: list[FirmsMLPredictionResponseBody] = Field(
        ..., description="List of event predictions."
    )
    total_events: int = Field(..., ge=0, description="Total events derived.")
    abstained_events: int = Field(..., ge=0, description="Total abstained events.")
    operating_mode: str = Field(..., description="Operating mode applied.")
