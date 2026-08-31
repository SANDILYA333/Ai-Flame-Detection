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


class ContextAssessmentResponseBody(BaseModel):
    """Structured response for contextual evidence assessment."""

    context_label: str = Field(
        ...,
        description="Adjudicated label ('industrial', 'non_industrial', 'unknown').",
    )
    context_confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Context evidence confidence score."
    )
    evidence_count: int = Field(
        ..., ge=0, description="Number of matched context evidence items."
    )
    primary_facility_name: str | None = Field(
        None, description="Name of nearest matched industrial/environmental facility."
    )
    primary_context_type: str | None = Field(
        None, description="Contextual type of closest matched facility."
    )
    primary_distance_meters: float | None = Field(
        None, ge=0.0, description="Distance to nearest facility in meters."
    )
    has_conflicting_context: bool = Field(
        ..., description="True if contradictory context features were matched."
    )
    evidence_summary: list[dict[str, Any]] = Field(
        default_factory=list, description="Summary list of matched context evidence."
    )


class EventIntelligenceResponseBody(BaseModel):
    """Structured response for unified Event Intelligence (ML + Context)."""

    intelligence_id: str = Field(..., description="Canonical intelligence identifier.")
    event_id: str = Field(..., description="Canonical event identifier.")
    event_timestamp: datetime = Field(..., description="Observation timestamp in UTC.")
    centroid_latitude: float = Field(
        ..., description="Centroid latitude in EPSG:4326."
    )
    centroid_longitude: float = Field(
        ..., description="Centroid longitude in EPSG:4326."
    )
    detection_count: int = Field(..., ge=1, description="Number of member detections.")
    max_frp_mw: float | None = Field(None, description="Maximum FRP in MW.")
    operating_mode: str = Field(..., description="Operating mode applied.")

    # ML Assessment
    model_name: str = Field(..., description="Production model architecture.")
    model_version: str = Field(..., description="Production model version.")
    ml_predicted_class: str = Field(..., description="Raw model predicted class.")
    ml_assigned_class: str = Field(
        ..., description="Policy-authorized ML assigned class."
    )
    ml_confidence: float = Field(
        ..., ge=0.0, le=1.0, description="ML confidence score."
    )
    ml_threshold: float = Field(
        ..., ge=0.0, le=1.0, description="ML abstention threshold."
    )
    ml_class_probabilities: dict[str, float] = Field(
        default_factory=dict, description="Class probabilities."
    )
    ml_is_abstained: bool = Field(
        ..., description="True if ML prediction was abstained."
    )
    ml_abstention_reason: str | None = Field(None, description="ML abstention reason.")

    # Context Assessment
    context_assessment: ContextAssessmentResponseBody = Field(
        ..., description="Contextual evidence evaluation."
    )

    # Intelligence Decision
    agreement_status: str = Field(
        ...,
        description="Status: AGREE, CONFLICT, ML_ONLY, CONTEXT_ONLY, UNCERTAIN.",
    )
    final_classification: str = Field(
        ..., description="Final unified intelligence classification."
    )
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Composite intelligence confidence score."
    )
    review_required: bool = Field(
        ..., description="True if human operator verification is required."
    )
    review_reasons: list[str] = Field(
        default_factory=list,
        description="List of reasons triggering review requirement.",
    )

    # Provenance & Latency
    feature_schema_version: str = Field(..., description="Feature schema version.")
    feature_count: int = Field(..., ge=0, description="Feature count.")
    event_schema_version: str = Field(..., description="Event schema version.")
    context_schema_version: str = Field(..., description="Context schema version.")
    context_enrichment_latency_ms: float = Field(
        ..., ge=0.0, description="Context latency in ms."
    )
    feature_extraction_latency_ms: float = Field(
        ..., ge=0.0, description="Feature latency in ms."
    )
    inference_latency_ms: float = Field(
        ..., ge=0.0, description="Inference latency in ms."
    )
    total_latency_ms: float = Field(
        ..., ge=0.0, description="Total pipeline latency in ms."
    )


class FirmsIntelligenceCsvRequestBody(BaseModel):
    """Payload for evaluating raw NASA FIRMS CSV through intelligence pipeline."""

    csv_content: str = Field(
        ..., description="Raw NASA FIRMS CSV payload."
    )
    operating_mode: str = Field(
        default="HIGH_PRECISION",
        description="Target operating mode (HIGH_PRECISION, HIGH_RECALL, SELECTIVE).",
    )


class FirmsIntelligenceCsvResponseBody(BaseModel):
    """Response container for FIRMS CSV intelligence evaluation."""

    results: list[EventIntelligenceResponseBody] = Field(
        ..., description="List of event intelligence results."
    )
    total_events: int = Field(..., ge=0, description="Total evaluated events.")
    review_required_events: int = Field(
        ..., ge=0, description="Count of events requiring review."
    )
    operating_mode: str = Field(..., description="Operating mode used.")
