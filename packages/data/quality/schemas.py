"""Domain models and audit schemas for data quality and integrity validation."""

from enum import StrEnum
from typing import Any

from pydantic import Field, field_validator

from packages.schemas.common import BaseDomainModel, BoundingBox, UtcDatetime
from packages.schemas.detection import Detection


class QualityViolationSeverity(StrEnum):
    """Severity tier for a data quality violation."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class QualityViolationCategory(StrEnum):
    """Categorization of data quality and dataset integrity anomalies."""

    DUPLICATE_RECORD = "duplicate_record"
    CONFLICTING_OBSERVATION = "conflicting_observation"
    TEMPORAL_INVERSION = "temporal_inversion"
    SPATIAL_OUT_OF_BOUNDS = "spatial_out_of_bounds"
    COORDINATE_ANOMALY = "coordinate_anomaly"
    BROKEN_PROVENANCE = "broken_provenance"
    MISSING_PHYSICAL_METRIC = "missing_physical_metric"


class QualityAssessmentTier(StrEnum):
    """Overall dataset quality health tier."""

    HIGH_QUALITY = "high_quality"
    ACCEPTABLE = "acceptable"
    DEGRADED = "degraded"
    REJECTED = "rejected"


class QualityViolation(BaseDomainModel):
    """Structured diagnostic representation of a specific quality violation."""

    severity: QualityViolationSeverity = Field(
        ...,
        description="Severity level of the quality violation.",
    )
    category: QualityViolationCategory = Field(
        ...,
        description="Category of the data quality anomaly.",
    )
    message: str = Field(
        ...,
        min_length=1,
        description="Human-readable diagnostic description of the issue.",
    )
    record_id: str | None = Field(
        None,
        description="Identifier of the record associated with violation.",
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Supporting structured diagnostic metadata.",
    )


class DetectionQualityAudit(BaseDomainModel):
    """Comprehensive quality and integrity audit report for Detection datasets."""

    total_records: int = Field(..., ge=0)
    unique_records: int = Field(..., ge=0)
    duplicate_count: int = Field(..., ge=0)
    conflicting_count: int = Field(..., ge=0)
    frp_completeness_ratio: float = Field(..., ge=0.0, le=1.0)
    brightness_completeness_ratio: float = Field(..., ge=0.0, le=1.0)
    confidence_completeness_ratio: float = Field(..., ge=0.0, le=1.0)
    earliest_acquired_at: UtcDatetime | None = Field(None)
    latest_acquired_at: UtcDatetime | None = Field(None)
    temporal_span_hours: float | None = Field(None, ge=0.0)
    spatial_bounding_box: BoundingBox | None = Field(None)
    provenance_valid_count: int = Field(..., ge=0)
    provenance_valid_ratio: float = Field(..., ge=0.0, le=1.0)
    quality_score: float = Field(..., ge=0.0, le=1.0)
    quality_tier: QualityAssessmentTier = Field(...)
    violations: list[QualityViolation] = Field(default_factory=list)

    @field_validator("quality_score", mode="after")
    @classmethod
    def _round_score(cls, v: float) -> float:
        return round(v, 4)


class ContextQualityAudit(BaseDomainModel):
    """Comprehensive quality and integrity audit report for ContextFeature datasets."""

    total_features: int = Field(..., ge=0)
    unique_features: int = Field(..., ge=0)
    duplicate_count: int = Field(..., ge=0)
    named_facility_ratio: float = Field(..., ge=0.0, le=1.0)
    polygonal_envelope_ratio: float = Field(..., ge=0.0, le=1.0)
    temporal_validity_ratio: float = Field(..., ge=0.0, le=1.0)
    spatial_bounding_box: BoundingBox | None = Field(None)
    quality_score: float = Field(..., ge=0.0, le=1.0)
    quality_tier: QualityAssessmentTier = Field(...)
    violations: list[QualityViolation] = Field(default_factory=list)

    @field_validator("quality_score", mode="after")
    @classmethod
    def _round_score(cls, v: float) -> float:
        return round(v, 4)


class CleanedDetectionManifest(BaseDomainModel):
    """Manifest containing the quality audit and partitioned detection collections."""

    audit: DetectionQualityAudit = Field(...)
    clean_detections: list[Detection] = Field(default_factory=list)
    duplicate_detections: list[Detection] = Field(default_factory=list)
    conflicting_detections: list[Detection] = Field(default_factory=list)
