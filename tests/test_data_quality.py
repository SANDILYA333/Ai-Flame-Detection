"""Unit, validation, determinism, and integration tests for DATA-005 Data Quality."""

import random
from datetime import UTC, datetime
from pathlib import Path

import pytest

from packages.config.scientific import ScientificConfig
from packages.data.context import parse_context_geojson
from packages.data.firms import parse_firms_csv
from packages.data.quality import (
    DatasetRejectedError,
    QualityAssessmentTier,
    QualityViolationCategory,
    QualityViolationSeverity,
    audit_context_dataset,
    audit_detection_dataset,
    clean_and_deduplicate_detections,
)
from packages.events.service import derive_thermal_events
from packages.schemas.common import BoundingBox, Coordinate
from packages.schemas.detection import Detection

_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "quality"
_DUP_FIXTURE = _FIXTURES_DIR / "duplicate_detections.csv"
_CONFLICT_FIXTURE = _FIXTURES_DIR / "conflicting_detections.csv"
_OSM_FIXTURE = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "context"
    / "osm_industrial_zones.geojson"
)


class TestDuplicateAndConflictingDetection:
    """Test duplicate detection, conflicting observation flagging, and multi-passes."""

    def test_exact_duplicates_are_isolated(self) -> None:
        """Exact duplicates are partitioned out while multi-temporal passes are kept."""
        detections = parse_firms_csv(_DUP_FIXTURE, source_snapshot_id="snap_dup_test")
        assert len(detections) == 4

        manifest = clean_and_deduplicate_detections(detections)

        assert manifest.audit.total_records == 4
        assert manifest.audit.unique_records == 3
        assert manifest.audit.duplicate_count == 1
        assert len(manifest.clean_detections) == 3
        assert len(manifest.duplicate_detections) == 1

        # Verify duplicate record matches the expected raw_hash
        dup_hash = manifest.duplicate_detections[0].raw_hash
        clean_hashes = [d.raw_hash for d in manifest.clean_detections]
        assert dup_hash in clean_hashes

    def test_conflicting_space_time_observations(self) -> None:
        """Observations at same coordinate and time with different FRP are flagged."""
        detections = parse_firms_csv(
            _CONFLICT_FIXTURE, source_snapshot_id="snap_conflict_test"
        )
        assert len(detections) == 2

        manifest = clean_and_deduplicate_detections(detections)

        assert manifest.audit.conflicting_count == 1
        assert len(manifest.conflicting_detections) == 1
        assert len(manifest.clean_detections) == 1

        conflict_violation = next(
            v
            for v in manifest.audit.violations
            if v.category == QualityViolationCategory.CONFLICTING_OBSERVATION
        )
        assert conflict_violation.severity == QualityViolationSeverity.WARNING


class TestTemporalAndSpatialAudits:
    """Test temporal span calculation and spatial boundary audits."""

    def test_temporal_span_calculation(self) -> None:
        """Temporal earliest, latest, and duration span are calculated accurately."""
        detections = parse_firms_csv(_DUP_FIXTURE, source_snapshot_id="snap_time_test")
        audit = audit_detection_dataset(detections)

        assert audit.earliest_acquired_at == datetime(2026, 8, 1, 8, 30, tzinfo=UTC)
        assert audit.latest_acquired_at == datetime(2026, 8, 2, 19, 45, tzinfo=UTC)
        assert audit.temporal_span_hours is not None
        assert audit.temporal_span_hours == pytest.approx(35.25, abs=0.1)

    def test_null_island_anomaly_detected(self) -> None:
        """Null Island (0.0, 0.0) coordinate anomaly triggers CRITICAL violation."""
        det = Detection(
            detection_id="det_null_island",
            source="firms",
            source_snapshot_id="snap_null",
            acquired_at=datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
            geometry=Coordinate(latitude=0.0, longitude=0.0),
            satellite="NOAA-20",
            instrument="VIIRS",
            product_type="nrt",
            product_version="v2.0",
            raw_hash="a" * 64,
            frp_mw=10.0,
        )

        audit = audit_detection_dataset([det])
        assert audit.quality_tier == QualityAssessmentTier.REJECTED
        assert audit.quality_score == 0.0

        violation = next(
            v
            for v in audit.violations
            if v.category == QualityViolationCategory.COORDINATE_ANOMALY
        )
        assert violation.severity == QualityViolationSeverity.CRITICAL

    def test_spatial_bounding_box_and_out_of_bounds(self) -> None:
        """Bounding envelope computed and out-of-bounds observations flagged."""
        detections = parse_firms_csv(
            _DUP_FIXTURE, source_snapshot_id="snap_spatial_test"
        )
        # Bounding box covering only Jamnagar
        jamnagar_bbox = BoundingBox(
            min_latitude=22.0,
            max_latitude=23.0,
            min_longitude=70.0,
            max_longitude=71.0,
        )

        audit = audit_detection_dataset(detections, expected_bbox=jamnagar_bbox)

        assert audit.spatial_bounding_box is not None
        assert audit.spatial_bounding_box.min_latitude == pytest.approx(22.4502)
        assert audit.spatial_bounding_box.max_latitude == pytest.approx(24.1025)

        # Singrauli detection (lat=24.1025) is outside Jamnagar bbox
        out_of_bounds = [
            v
            for v in audit.violations
            if v.category == QualityViolationCategory.SPATIAL_OUT_OF_BOUNDS
        ]
        assert len(out_of_bounds) >= 1


class TestCompletenessAndMissingness:
    """Test missingness preservation and completeness ratio metrics."""

    def test_missing_frp_preserves_none_and_tracks_ratio(self) -> None:
        """Null FRP is preserved as None and measured in completeness ratio."""
        d1 = Detection(
            detection_id="det_with_frp",
            source="firms",
            source_snapshot_id="snap_1",
            acquired_at=datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
            geometry=Coordinate(latitude=22.45, longitude=70.05),
            satellite="NOAA-20",
            instrument="VIIRS",
            product_type="nrt",
            product_version="v2.0",
            raw_hash="1" * 64,
            frp_mw=25.0,
        )
        d2 = Detection(
            detection_id="det_without_frp",
            source="firms",
            source_snapshot_id="snap_1",
            acquired_at=datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
            geometry=Coordinate(latitude=22.46, longitude=70.06),
            satellite="NOAA-20",
            instrument="VIIRS",
            product_type="nrt",
            product_version="v2.0",
            raw_hash="2" * 64,
            frp_mw=None,  # Missing FRP
        )

        audit = audit_detection_dataset([d1, d2])

        assert d2.frp_mw is None
        assert audit.frp_completeness_ratio == 0.5


class TestProvenanceAudit:
    """Test provenance lineage and cryptographic hash validation."""

    def test_broken_provenance_triggers_critical_violation(self) -> None:
        """Short or missing raw hash triggers CRITICAL BROKEN_PROVENANCE violation."""
        d_bad_hash = Detection(
            detection_id="det_bad_hash",
            source="firms",
            source_snapshot_id="snap_1",
            acquired_at=datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
            geometry=Coordinate(latitude=22.45, longitude=70.05),
            satellite="NOAA-20",
            instrument="VIIRS",
            product_type="nrt",
            product_version="v2.0",
            raw_hash="invalid_short_hash",
            frp_mw=10.0,
        )

        audit = audit_detection_dataset([d_bad_hash])
        assert audit.provenance_valid_count == 0
        assert audit.provenance_valid_ratio == 0.0
        assert audit.quality_tier == QualityAssessmentTier.REJECTED


class TestQualityScoreAndTiers:
    """Test deterministic scoring and strict mode error enforcement."""

    def test_high_quality_tier_classification(self) -> None:
        """Complete, unique dataset achieves HIGH_QUALITY tier."""
        d1 = Detection(
            detection_id="det_1",
            source="firms",
            source_snapshot_id="snap_1",
            acquired_at=datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
            geometry=Coordinate(latitude=22.45, longitude=70.05),
            satellite="NOAA-20",
            instrument="VIIRS",
            product_type="nrt",
            product_version="v2.0",
            raw_hash="a" * 64,
            frp_mw=25.0,
            brightness_ti4_k=350.0,
            confidence="nominal",
        )
        audit = audit_detection_dataset([d1])

        assert audit.quality_tier == QualityAssessmentTier.HIGH_QUALITY
        assert audit.quality_score >= 0.85

    def test_strict_mode_raises_on_rejected_dataset(self) -> None:
        """Strict clean service raises DatasetRejectedError on REJECTED dataset."""
        with pytest.raises(DatasetRejectedError) as exc_info:
            clean_and_deduplicate_detections([], strict=True)

        assert "dataset rejected" in str(exc_info.value).lower()


class TestContextQualityAudit:
    """Test context feature dataset quality auditing."""

    def test_context_quality_audit(self) -> None:
        """OSM context fixture is audited for completeness and quality."""
        features = parse_context_geojson(
            geojson_input=_OSM_FIXTURE,
            provider="osm",
            dataset_name="osm_industrial",
        )
        assert len(features) == 5

        audit = audit_context_dataset(features)

        assert audit.total_features == 5
        assert audit.unique_features == 5
        assert audit.duplicate_count == 0
        assert audit.named_facility_ratio >= 0.6  # 4 out of 5 named
        assert audit.polygonal_envelope_ratio == 0.8  # 4 polygons, 1 point
        assert audit.quality_tier == QualityAssessmentTier.HIGH_QUALITY
        assert audit.quality_score >= 0.80


class TestPermutationDeterminism:
    """Test ordering determinism and permutation invariance across 20 trials."""

    def test_detection_audit_permutation_invariance_20_trials(self) -> None:
        """Randomly shuffled detection batches produce identical audit scores."""
        detections = parse_firms_csv(_DUP_FIXTURE, source_snapshot_id="snap_perm_test")
        baseline = clean_and_deduplicate_detections(detections)
        baseline_ids = [d.detection_id for d in baseline.clean_detections]
        baseline_score = baseline.audit.quality_score

        rng = random.Random(42)
        for trial in range(20):
            shuffled = list(detections)
            rng.shuffle(shuffled)

            trial_manifest = clean_and_deduplicate_detections(shuffled)
            trial_ids = [d.detection_id for d in trial_manifest.clean_detections]
            trial_score = trial_manifest.audit.quality_score

            assert trial_ids == baseline_ids, f"Clean IDs mismatch at trial {trial + 1}"
            assert trial_score == baseline_score, f"Score mismatch at trial {trial + 1}"


class TestPhase3IntegrationHandover:
    """Verify clean detections flow into Phase 3 scientific derivation."""

    def test_clean_detections_into_event_clustering(self) -> None:
        """Clean detections from DATA-005 are clustered by Phase 3 service."""
        detections = parse_firms_csv(
            _DUP_FIXTURE, source_snapshot_id="snap_phase3_test"
        )
        manifest = clean_and_deduplicate_detections(detections)

        config = ScientificConfig(
            version="v1.0-test",
            name="test_profile",
            description="Calibrated test config",
            spatial_cluster_radius_meters=1000.0,
            temporal_window_hours=2.0,
            persistence_threshold_days=30.0,
            persistence_min_observations=3,
            attribution_radius_meters=5000.0,
            attribution_confidence_threshold=0.6,
            minimum_event_confidence=0.5,
            abstention_confidence_threshold=0.3,
        )

        events = derive_thermal_events(manifest.clean_detections, config)

        assert len(events) >= 1
        for evt in events:
            assert evt.event_id.startswith("evt_")
            assert evt.detection_count >= 1
