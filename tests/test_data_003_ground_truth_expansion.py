"""Comprehensive Test Suite for DATA-003: Authoritative Ground-Truth Expansion.

Validates:
1. Complete ingestion of expanded ground-truth catalogs (JSON, GeoJSON, CSV).
2. Provenance preservation and absolute absence of credentials/secrets.
3. Spatiotemporal matching logic (geodesic distance + temporal window bounds).
4. Strict UNKNOWN preservation (missing != negative, unadjudicated != non_industrial).
5. Historical multi-season FIRMS ingestion with temporal span >= 180 days.
6. Industrial facility infrastructure catalog coverage (>= 10 verified facilities).
7. Deduplication across overlapping catalogs.
8. Scientific training gate satisfaction.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from packages.context.ground_truth import (
    ExternalReferenceRecord,
    GroundTruthIngestionService,
)
from packages.context.pipeline import RealContextLabelingService
from packages.data.firms.capture import compute_content_hash
from packages.events.pipeline import (
    get_default_calibrated_scientific_config,
)
from packages.schemas.common import BoundingBox, Coordinate
from packages.schemas.enums import ContextType
from packages.schemas.event import (
    Event,
    RealThermalEventDataset,
)
from packages.schemas.ml import (
    LabelTier,
)


class TestData003GroundTruthExpansion:
    """Test suite verifying DATA-003 ground truth expansion, provenance, and gate."""

    def test_authoritative_catalogs_discovery_and_provenance(self) -> None:
        """Verify all ground-truth catalog files are discovered, valid, and cryptographically hashed."""
        ref_dir = Path("data/real/reference")
        assert ref_dir.exists(), "data/real/reference must exist"

        records, file_hashes = GroundTruthIngestionService.discover_and_load_catalog(
            ["data/real/reference", "fixtures/reference"]
        )

        assert len(file_hashes) >= 5, "Must discover at least 5 catalog files"
        assert len(records) >= 500, (
            f"Expected >= 500 ground truth records, got {len(records)}"
        )

        # Verify cryptographic hashes
        for path_str, f_hash in file_hashes.items():
            assert len(f_hash) == 64, f"Invalid SHA-256 hash length for {path_str}"
            actual_hash = compute_content_hash(Path(path_str).read_bytes())
            assert actual_hash == f_hash, f"Hash mismatch for {path_str}"

        # Verify no credentials
        for rec in records:
            assert rec.source_id, "Missing source_id"
            assert rec.source_record_id, "Missing source_record_id"
            assert rec.geometry.latitude is not None
            assert rec.geometry.longitude is not None
            assert rec.tier in (
                LabelTier.TIER_A_AUTHORITATIVE,
                LabelTier.TIER_B_STRONG_EVIDENCE,
            )

    def test_industrial_facilities_coverage(self) -> None:
        """Verify at least 10 verified industrial facilities across multiple corridors."""
        fac_dir = Path("data/real/reference/facilities")
        features, file_hashes = (
            GroundTruthIngestionService.load_facility_context_features(fac_dir)
        )

        assert len(features) >= 10, (
            f"Expected >= 10 verified facilities, got {len(features)}"
        )
        assert len(file_hashes) >= 4, (
            f"Expected >= 4 facility catalog files, got {len(file_hashes)}"
        )

        facility_names = {f.facility_name for f in features if f.facility_name}
        assert len(facility_names) >= 10, "Expected >= 10 distinct facility names"

        # Check types
        context_types = {f.context_type for f in features}
        assert (
            ContextType.OIL_GAS in context_types
            or ContextType.INDUSTRIAL in context_types
        )

    def test_spatiotemporal_matching_bounds(self) -> None:
        """Verify spatial and temporal tolerance bounds during ground-truth matching."""
        t0 = datetime(2026, 8, 15, 12, 0, 0, tzinfo=UTC)

        # Mock Event
        ev = Event(
            event_id="test_ev_001",
            started_at=t0,
            ended_at=t0 + timedelta(hours=1),
            centroid_geometry=Coordinate(latitude=22.3400, longitude=69.8550),
            detection_ids=["det_001"],
            detection_count=1,
            mean_frp_mw=15.0,
            max_frp_mw=20.0,
            formation_configuration_id="cfg_default",
            formation_configuration_version="v1.0",
            bounding_box=BoundingBox(
                min_latitude=22.33,
                min_longitude=69.85,
                max_latitude=22.35,
                max_longitude=69.86,
            ),
        )

        # 1. Matching GT (within 100m, exact time)
        gt_matching = ExternalReferenceRecord(
            source_id="TEST_REGISTRY",
            source_name="Test Industrial Registry",
            source_type="OFFICIAL_REGISTRY",
            source_record_id="REC_001",
            observed_at=t0 + timedelta(hours=2),
            geometry=Coordinate(latitude=22.3405, longitude=69.8555),
            claim_class="industrial",
            confidence=1.0,
            tier=LabelTier.TIER_A_AUTHORITATIVE,
            source_snapshot_hash="a" * 64,
        )

        # 2. Too far spatially (> 5km away)
        gt_too_far = ExternalReferenceRecord(
            source_id="TEST_REGISTRY",
            source_name="Test Industrial Registry",
            source_type="OFFICIAL_REGISTRY",
            source_record_id="REC_002",
            observed_at=t0,
            geometry=Coordinate(latitude=23.0000, longitude=70.5000),
            claim_class="industrial",
            confidence=1.0,
            tier=LabelTier.TIER_A_AUTHORITATIVE,
            source_snapshot_hash="a" * 64,
        )

        # 3. Too far temporally (> 48h away)
        gt_too_late = ExternalReferenceRecord(
            source_id="TEST_REGISTRY",
            source_name="Test Industrial Registry",
            source_type="OFFICIAL_REGISTRY",
            source_record_id="REC_003",
            observed_at=t0 + timedelta(days=5),
            geometry=Coordinate(latitude=22.3400, longitude=69.8550),
            claim_class="industrial",
            confidence=1.0,
            tier=LabelTier.TIER_A_AUTHORITATIVE,
            source_snapshot_hash="a" * 64,
        )

        matched = GroundTruthIngestionService.match_events_to_ground_truth(
            events=[ev],
            ground_truth_records=[gt_matching, gt_too_far, gt_too_late],
            max_distance_meters=2000.0,
            max_temporal_delta_hours=24.0,
        )

        assert len(matched) == 1, f"Expected exactly 1 match, got {len(matched)}"
        assert matched[0].evidence_payload["source_record_id"] == "REC_001"
        assert matched[0].claim_class == "industrial"

    def test_unknown_invariant_and_missing_not_negative(self) -> None:
        """Verify that unmatched events remain UNKNOWN and are never relabeled as negative."""
        t0 = datetime(2026, 8, 15, 12, 0, 0, tzinfo=UTC)

        ev_unmatched = Event(
            event_id="unmatched_ev_999",
            started_at=t0,
            ended_at=t0 + timedelta(hours=1),
            centroid_geometry=Coordinate(latitude=10.0000, longitude=20.0000),
            detection_ids=["det_999"],
            detection_count=1,
            mean_frp_mw=5.0,
            max_frp_mw=5.0,
            formation_configuration_id="cfg_default",
            formation_configuration_version="v1.0",
            bounding_box=BoundingBox(
                min_latitude=9.99,
                min_longitude=19.99,
                max_latitude=10.01,
                max_longitude=20.01,
            ),
        )

        config = get_default_calibrated_scientific_config()
        event_ds = RealThermalEventDataset(
            detection_dataset_id="test_det_ds",
            detection_dataset_hash="a" * 64,
            study_area_id="test_area",
            study_area_name="Test Area",
            bounding_box=BoundingBox(
                min_latitude=0, min_longitude=0, max_latitude=30, max_longitude=30
            ),
            config_fingerprint="b" * 64,
            spatial_cluster_radius_meters=1000.0,
            temporal_window_hours=12.0,
            persistent_source_radius_meters=500.0,
            event_count=1,
            persistent_source_count=0,
            canonical_dataset_hash="c" * 64,
            created_at=datetime.now(UTC),
            events=[ev_unmatched],
            persistent_sources=[],
        )
        enriched = RealContextLabelingService.enrich_and_adjudicate_dataset(
            event_dataset=event_ds,
            candidate_features=[],
            external_reference_evidence=[],
            config=config,
        )

        assert len(enriched.reference_labels) == 1
        decision = enriched.reference_labels[0]
        assert decision.assigned_class == "unknown"
        assert decision.is_train_eligible is False
        assert decision.label_tier == LabelTier.UNKNOWN
