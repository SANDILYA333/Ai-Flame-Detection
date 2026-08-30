"""Deterministic integrity rules, duplicate detection, and quality metrics."""

from collections.abc import Sequence
from datetime import datetime

from packages.data.quality.schemas import (
    QualityAssessmentTier,
    QualityViolation,
    QualityViolationCategory,
    QualityViolationSeverity,
)
from packages.geospatial.envelope import calculate_bounding_box
from packages.schemas.common import BoundingBox
from packages.schemas.detection import Detection


def audit_detection_duplicates(
    detections: Sequence[Detection],
) -> tuple[list[Detection], list[Detection], list[Detection], list[QualityViolation]]:
    """Partition detections into clean, exact duplicates, and conflicting observations.

    Args:
        detections: Sequence of canonical Detection objects.

    Returns:
        tuple containing:
            - clean_detections: Unique canonical records.
            - duplicate_detections: Duplicate instances.
            - conflicting_detections: Observations with conflicting measurements.
            - violations: QualityViolation audit records.
    """
    clean: list[Detection] = []
    duplicates: list[Detection] = []
    conflicting: list[Detection] = []
    violations: list[QualityViolation] = []

    seen_hashes: set[str] = set()
    # Map (lat, lon, acquired_at) -> first Detection for conflict detection
    seen_space_time: dict[tuple[float, float, datetime], Detection] = {}

    for det in detections:
        # 1. Exact Duplicate Check (content raw_hash)
        if det.raw_hash in seen_hashes:
            duplicates.append(det)
            violations.append(
                QualityViolation(
                    severity=QualityViolationSeverity.INFO,
                    category=QualityViolationCategory.DUPLICATE_RECORD,
                    message=f"Duplicate observation with hash '{det.raw_hash[:12]}'.",
                    record_id=det.detection_id,
                    details={"raw_hash": det.raw_hash},
                )
            )
            continue

        # 2. Conflicting Space-Time Observation Check
        st_key = (
            round(det.geometry.latitude, 4),
            round(det.geometry.longitude, 4),
            det.acquired_at,
        )
        if st_key in seen_space_time:
            prev = seen_space_time[st_key]
            # Check for conflict: different FRP or different satellite
            frp_diff = (
                abs((det.frp_mw or 0.0) - (prev.frp_mw or 0.0))
                if (det.frp_mw is not None and prev.frp_mw is not None)
                else None
            )
            is_conflicting = (frp_diff is not None and frp_diff > 0.5) or (
                det.satellite != prev.satellite and det.instrument == prev.instrument
            )

            if is_conflicting:
                conflicting.append(det)
                violations.append(
                    QualityViolation(
                        severity=QualityViolationSeverity.WARNING,
                        category=QualityViolationCategory.CONFLICTING_OBSERVATION,
                        message=(
                            f"Conflicting observation at ({st_key[0]}, {st_key[1]}) "
                            f"at {st_key[2].isoformat()}."
                        ),
                        record_id=det.detection_id,
                        details={
                            "conflicting_with": prev.detection_id,
                            "frp_mw": det.frp_mw,
                            "prev_frp_mw": prev.frp_mw,
                        },
                    )
                )
                continue

        seen_hashes.add(det.raw_hash)
        seen_space_time[st_key] = det
        clean.append(det)

    return clean, duplicates, conflicting, violations


def audit_temporal_integrity(
    detections: Sequence[Detection],
) -> tuple[datetime | None, datetime | None, float | None, list[QualityViolation]]:
    """Compute temporal span and validate timestamps.

    Returns:
        tuple[earliest_acquired_at, latest_acquired_at, span_hours, violations]
    """
    if not detections:
        return None, None, None, []

    violations: list[QualityViolation] = []
    timestamps: list[datetime] = []

    for det in detections:
        ts = det.acquired_at
        if ts.tzinfo is None:
            violations.append(
                QualityViolation(
                    severity=QualityViolationSeverity.CRITICAL,
                    category=QualityViolationCategory.TEMPORAL_INVERSION,
                    message="Observation timestamp is naive (missing UTC timezone).",
                    record_id=det.detection_id,
                )
            )
        timestamps.append(ts)

    timestamps.sort()
    earliest = timestamps[0]
    latest = timestamps[-1]
    span_hours = round((latest - earliest).total_seconds() / 3600.0, 2)

    return earliest, latest, span_hours, violations


def audit_spatial_integrity(
    detections: Sequence[Detection],
    expected_bbox: BoundingBox | None = None,
) -> tuple[BoundingBox | None, list[QualityViolation]]:
    """Compute dataset bounding envelope and flag spatial coordinate anomalies.

    Returns:
        tuple[spatial_bounding_box, violations]
    """
    if not detections:
        return None, []

    violations: list[QualityViolation] = []
    points: list[tuple[float, float]] = []

    for det in detections:
        lat = det.geometry.latitude
        lon = det.geometry.longitude

        # Check for Null Island coordinate (0.0, 0.0)
        if abs(lat) < 1e-6 and abs(lon) < 1e-6:
            violations.append(
                QualityViolation(
                    severity=QualityViolationSeverity.CRITICAL,
                    category=QualityViolationCategory.COORDINATE_ANOMALY,
                    message="Null Island (0.0, 0.0) coordinate anomaly detected.",
                    record_id=det.detection_id,
                )
            )

        # Check expected bounding envelope
        if expected_bbox is not None and not (
            expected_bbox.min_latitude <= lat <= expected_bbox.max_latitude
            and expected_bbox.min_longitude <= lon <= expected_bbox.max_longitude
        ):
            violations.append(
                QualityViolation(
                    severity=QualityViolationSeverity.WARNING,
                    category=QualityViolationCategory.SPATIAL_OUT_OF_BOUNDS,
                    message=f"Coord ({lat}, {lon}) outside expected study bounds.",
                    record_id=det.detection_id,
                    details={
                        "latitude": lat,
                        "longitude": lon,
                        "expected_bbox": expected_bbox.model_dump(),
                    },
                )
            )

        points.append((lat, lon))

    bbox = calculate_bounding_box(points)
    return bbox, violations


def audit_provenance_integrity(
    detections: Sequence[Detection],
) -> tuple[int, float, list[QualityViolation]]:
    """Audit completeness of source provenance and cryptographic hashes.

    Returns:
        tuple[provenance_valid_count, provenance_valid_ratio, violations]
    """
    if not detections:
        return 0, 0.0, []

    violations: list[QualityViolation] = []
    valid_count = 0

    for det in detections:
        has_snapshot = bool(det.source_snapshot_id and det.source_snapshot_id.strip())
        has_hash = bool(det.raw_hash and len(det.raw_hash) == 64)
        has_source = bool(det.source and det.source.strip())

        if has_snapshot and has_hash and has_source:
            valid_count += 1
        else:
            violations.append(
                QualityViolation(
                    severity=QualityViolationSeverity.CRITICAL,
                    category=QualityViolationCategory.BROKEN_PROVENANCE,
                    message="Detection record has incomplete/broken provenance.",
                    record_id=det.detection_id,
                    details={
                        "has_snapshot": has_snapshot,
                        "has_hash": has_hash,
                        "has_source": has_source,
                    },
                )
            )

    ratio = round(valid_count / len(detections), 4)
    return valid_count, ratio, violations


def calculate_detection_quality_score(
    total: int,
    unique: int,
    prov_valid_ratio: float,
    frp_ratio: float,
    brightness_ratio: float,
    has_critical_violations: bool,
) -> tuple[float, QualityAssessmentTier]:
    """Calculate deterministic, explainable data quality score and health tier."""
    if total == 0 or has_critical_violations:
        return 0.0, QualityAssessmentTier.REJECTED

    uniqueness_ratio = unique / total

    # Deterministic weighted formula:
    # 35% uniqueness + 35% provenance + 15% FRP coverage + 15% brightness coverage
    score = (
        0.35 * uniqueness_ratio
        + 0.35 * prov_valid_ratio
        + 0.15 * frp_ratio
        + 0.15 * brightness_ratio
    )
    score_clamped = max(0.0, min(1.0, round(score, 4)))

    if score_clamped >= 0.85 and uniqueness_ratio >= 0.95:
        tier = QualityAssessmentTier.HIGH_QUALITY
    elif score_clamped >= 0.65:
        tier = QualityAssessmentTier.ACCEPTABLE
    elif score_clamped >= 0.30:
        tier = QualityAssessmentTier.DEGRADED
    else:
        tier = QualityAssessmentTier.REJECTED

    return score_clamped, tier
