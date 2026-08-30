"""High-level dataset quality audit and deduplication services."""

import logging
from collections.abc import Sequence

from packages.context.models import ContextFeature
from packages.data.quality.errors import DatasetRejectedError
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
from packages.geospatial.envelope import calculate_bounding_box
from packages.schemas.common import BoundingBox
from packages.schemas.detection import Detection

logger = logging.getLogger(__name__)


def audit_detection_dataset(
    detections: Sequence[Detection],
    expected_bbox: BoundingBox | None = None,
) -> DetectionQualityAudit:
    """Perform comprehensive data quality and integrity audit on a Detection dataset.

    Args:
        detections: Sequence of canonical Detection objects.
        expected_bbox: Optional expected geographic envelope for bounds validation.

    Returns:
        DetectionQualityAudit: Comprehensive diagnostic audit report.
    """
    total = len(detections)
    if total == 0:
        return DetectionQualityAudit(
            total_records=0,
            unique_records=0,
            duplicate_count=0,
            conflicting_count=0,
            frp_completeness_ratio=0.0,
            brightness_completeness_ratio=0.0,
            confidence_completeness_ratio=0.0,
            earliest_acquired_at=None,
            latest_acquired_at=None,
            temporal_span_hours=None,
            spatial_bounding_box=None,
            provenance_valid_count=0,
            provenance_valid_ratio=0.0,
            quality_score=0.0,
            quality_tier=QualityAssessmentTier.REJECTED,
            violations=[
                QualityViolation(
                    severity=QualityViolationSeverity.CRITICAL,
                    category=QualityViolationCategory.BROKEN_PROVENANCE,
                    message="Detection dataset is empty (zero records).",
                )
            ],
        )

    # 1. Duplicate & Conflict Audit
    clean, dups, conflicts, dup_violations = audit_detection_duplicates(detections)

    # 2. Temporal Audit
    earliest, latest, span_hours, time_violations = audit_temporal_integrity(detections)

    # 3. Spatial Audit
    bbox, spatial_violations = audit_spatial_integrity(detections, expected_bbox)

    # 4. Provenance Audit
    prov_count, prov_ratio, prov_violations = audit_provenance_integrity(detections)

    # 5. Completeness Metrics (missing is preserved as missing, not coerced)
    frp_count = sum(1 for d in detections if d.frp_mw is not None)
    frp_ratio = round(frp_count / total, 4)

    brightness_count = sum(
        1
        for d in detections
        if (d.brightness_ti4_k is not None or d.brightness_ti5_k is not None)
    )
    brightness_ratio = round(brightness_count / total, 4)

    conf_count = sum(1 for d in detections if d.confidence is not None)
    conf_ratio = round(conf_count / total, 4)

    all_violations = (
        dup_violations + time_violations + spatial_violations + prov_violations
    )
    has_critical = any(
        v.severity == QualityViolationSeverity.CRITICAL for v in all_violations
    )

    score, tier = calculate_detection_quality_score(
        total=total,
        unique=len(clean),
        prov_valid_ratio=prov_ratio,
        frp_ratio=frp_ratio,
        brightness_ratio=brightness_ratio,
        has_critical_violations=has_critical,
    )

    logger.info(
        "Detection dataset audited: %d total, %d unique, score=%.4f, tier=%s",
        total,
        len(clean),
        score,
        tier.value,
    )

    return DetectionQualityAudit(
        total_records=total,
        unique_records=len(clean),
        duplicate_count=len(dups),
        conflicting_count=len(conflicts),
        frp_completeness_ratio=frp_ratio,
        brightness_completeness_ratio=brightness_ratio,
        confidence_completeness_ratio=conf_ratio,
        earliest_acquired_at=earliest,
        latest_acquired_at=latest,
        temporal_span_hours=span_hours,
        spatial_bounding_box=bbox,
        provenance_valid_count=prov_count,
        provenance_valid_ratio=prov_ratio,
        quality_score=score,
        quality_tier=tier,
        violations=all_violations,
    )


def clean_and_deduplicate_detections(
    detections: Sequence[Detection],
    expected_bbox: BoundingBox | None = None,
    strict: bool = False,
) -> CleanedDetectionManifest:
    """Audit and filter a Detection dataset into clean, deduplicated records.

    Args:
        detections: Sequence of canonical Detection objects.
        expected_bbox: Optional bounding envelope for bounds checking.
        strict: If True, raises DatasetRejectedError if quality tier is REJECTED.

    Returns:
        CleanedDetectionManifest: Manifest containing audit report and clean records.

    Raises:
        DatasetRejectedError: In strict mode if dataset fails quality gates.
    """
    audit = audit_detection_dataset(detections, expected_bbox)

    if strict and audit.quality_tier == QualityAssessmentTier.REJECTED:
        critical_msgs = [
            v.message
            for v in audit.violations
            if v.severity == QualityViolationSeverity.CRITICAL
        ]
        raise DatasetRejectedError(
            f"Dataset rejected during strict audit (score: {audit.quality_score}).",
            critical_violations=critical_msgs,
            details={"audit": audit.model_dump()},
        )

    clean, dups, conflicts, _ = audit_detection_duplicates(detections)

    # Sort clean records deterministically: (acquired_at, latitude, longitude, raw_hash)
    clean.sort(
        key=lambda d: (
            d.acquired_at,
            d.geometry.latitude,
            d.geometry.longitude,
            d.raw_hash,
        )
    )

    return CleanedDetectionManifest(
        audit=audit,
        clean_detections=clean,
        duplicate_detections=dups,
        conflicting_detections=conflicts,
    )


def audit_context_dataset(
    features: Sequence[ContextFeature],
    expected_bbox: BoundingBox | None = None,
) -> ContextQualityAudit:
    """Perform quality and integrity audit on a ContextFeature dataset."""
    total = len(features)
    if total == 0:
        return ContextQualityAudit(
            total_features=0,
            unique_features=0,
            duplicate_count=0,
            named_facility_ratio=0.0,
            polygonal_envelope_ratio=0.0,
            temporal_validity_ratio=0.0,
            spatial_bounding_box=None,
            quality_score=0.0,
            quality_tier=QualityAssessmentTier.REJECTED,
            violations=[
                QualityViolation(
                    severity=QualityViolationSeverity.CRITICAL,
                    category=QualityViolationCategory.BROKEN_PROVENANCE,
                    message="Context dataset is empty (zero features).",
                )
            ],
        )

    seen_ids: set[str] = set()
    duplicates: list[ContextFeature] = []
    points: list[tuple[float, float]] = []
    violations: list[QualityViolation] = []

    named_count = 0
    polygon_count = 0
    temporal_count = 0

    for feat in features:
        if feat.feature_id in seen_ids:
            duplicates.append(feat)
            violations.append(
                QualityViolation(
                    severity=QualityViolationSeverity.WARNING,
                    category=QualityViolationCategory.DUPLICATE_RECORD,
                    message=f"Duplicate context feature_id '{feat.feature_id}'.",
                    record_id=feat.feature_id,
                )
            )
        seen_ids.add(feat.feature_id)

        if feat.facility_name and feat.facility_name.strip():
            named_count += 1
        if feat.bounding_box is not None:
            polygon_count += 1
        if feat.valid_from is not None or feat.valid_to is not None:
            temporal_count += 1

        lat = feat.geometry.latitude
        lon = feat.geometry.longitude
        points.append((lat, lon))

        if expected_bbox is not None and not (
            expected_bbox.min_latitude <= lat <= expected_bbox.max_latitude
            and expected_bbox.min_longitude <= lon <= expected_bbox.max_longitude
        ):
            violations.append(
                QualityViolation(
                    severity=QualityViolationSeverity.WARNING,
                    category=QualityViolationCategory.SPATIAL_OUT_OF_BOUNDS,
                    message=f"Feature ({lat}, {lon}) outside expected study bounds.",
                    record_id=feat.feature_id,
                )
            )

    bbox = calculate_bounding_box(points)
    unique_count = len(seen_ids)
    named_ratio = round(named_count / total, 4)
    polygon_ratio = round(polygon_count / total, 4)
    temporal_ratio = round(temporal_count / total, 4)
    uniqueness_ratio = unique_count / total

    # Context score: 50% unique + 25% named facilities + 25% polygon geometry
    score = 0.50 * uniqueness_ratio + 0.25 * named_ratio + 0.25 * polygon_ratio
    score_clamped = max(0.0, min(1.0, round(score, 4)))

    if score_clamped >= 0.80:
        tier = QualityAssessmentTier.HIGH_QUALITY
    elif score_clamped >= 0.50:
        tier = QualityAssessmentTier.ACCEPTABLE
    elif score_clamped >= 0.25:
        tier = QualityAssessmentTier.DEGRADED
    else:
        tier = QualityAssessmentTier.REJECTED

    return ContextQualityAudit(
        total_features=total,
        unique_features=unique_count,
        duplicate_count=len(duplicates),
        named_facility_ratio=named_ratio,
        polygonal_envelope_ratio=polygon_ratio,
        temporal_validity_ratio=temporal_ratio,
        spatial_bounding_box=bbox,
        quality_score=score_clamped,
        quality_tier=tier,
        violations=violations,
    )
