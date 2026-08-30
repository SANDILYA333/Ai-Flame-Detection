"""Data quality, validation, and ingestion integrity layer (DATA-005)."""

from packages.data.quality.auditor import (
    audit_context_dataset,
    audit_detection_dataset,
    clean_and_deduplicate_detections,
)
from packages.data.quality.errors import (
    BrokenProvenanceError,
    DatasetRejectedError,
    QualityIntegrityError,
)
from packages.data.quality.rules import (
    audit_detection_duplicates,
    audit_provenance_integrity,
    audit_spatial_integrity,
    audit_temporal_integrity,
    calculate_detection_quality_score,
)
from packages.data.quality.schemas import (
    CleanedDetectionManifest,
    ContextQualityAudit,
    DetectionQualityAudit,
    QualityAssessmentTier,
    QualityViolation,
    QualityViolationCategory,
    QualityViolationSeverity,
)

__all__ = [
    "BrokenProvenanceError",
    "CleanedDetectionManifest",
    "ContextQualityAudit",
    "DatasetRejectedError",
    "DetectionQualityAudit",
    "QualityAssessmentTier",
    "QualityIntegrityError",
    "QualityViolation",
    "QualityViolationCategory",
    "QualityViolationSeverity",
    "audit_context_dataset",
    "audit_detection_dataset",
    "audit_detection_duplicates",
    "audit_provenance_integrity",
    "audit_spatial_integrity",
    "audit_temporal_integrity",
    "calculate_detection_quality_score",
    "clean_and_deduplicate_detections",
]
