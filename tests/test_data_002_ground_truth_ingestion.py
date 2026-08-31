"""Comprehensive Test Suite for DATA-002: Multi-Region Backfill & Ground-Truth Ingestion.

Validates:
1. External ground-truth JSON parsing, field validation, and SHA-256 snapshot hashing.
2. Spatial (geodesic distance) and temporal matching tolerances.
3. Spatial rejection when distance exceeds threshold.
4. Temporal rejection when observation timestamp is out of tolerance.
5. Tier A authoritative ground truth precedence over Tier B contextual proximity.
6. Absolute anti-geographic auto-labeling (Punjab event with no evidence != non-industrial).
7. Absolute anti-geographic auto-labeling (Jamnagar event with no evidence != industrial).
8. Missing != negative (UNKNOWN events remain ineligible and are never converted to negative).
9. Conflicting evidence adjudication and ineligibility.
10. Anti-circularity provenance preservation (source type, record ID, snapshot hash).
11. Complete end-to-end pipeline compatibility (FIRMS -> Events -> GT -> Enriched -> Supervised).
12. Determinism of repeated matching and label synthesis.
"""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from packages.config.scientific import ScientificConfig
from packages.context.ground_truth import (
    ExternalReferenceRecord,
    GroundTruthIngestionService,
)
from packages.context.pipeline import RealContextLabelingService
from packages.data.firms.activation import FirmsDataActivationService
from packages.data.firms.schemas import FirmsProduct
from packages.events.pipeline import RealEventConstructionService
from packages.feasibility.candidates import JAMNAGAR_KUTCH, PUNJAB_AGRICULTURAL
from packages.schemas.common import Coordinate
from packages.schemas.enums import SourceRole
from packages.schemas.event import Event
from packages.schemas.ml import (
    DatasetRowStatus,
    ExclusionReason,
    LabelConflictPolicy,
    LabelProvenanceType,
    LabelTier,
    ReferenceEvidence,
)
from services.ml.labels.constructor import LabelConstructor
from services.ml.labels.dataset import SupervisedDatasetBuilder
from services.ml.training.gate import RealTrainingGateEvaluator


@pytest.fixture
def test_config() -> ScientificConfig:
    return ScientificConfig(
        version="v1.0-test",
        name="test_profile",
        description="Calibrated test profile",
        spatial_cluster_radius_meters=1000.0,
        temporal_window_hours=2.0,
        persistence_threshold_days=10.0,
        persistence_min_observations=3,
        attribution_radius_meters=1500.0,
        attribution_confidence_threshold=0.7,
        minimum_event_confidence=0.5,
        abstention_confidence_threshold=0.4,
    )


@pytest.fixture
def mock_punjab_event() -> Event:
    now = datetime(2026, 8, 1, 8, 30, tzinfo=UTC)
    return Event(
        event_id="ev_punjab_crop_001",
        detection_ids=["det_p1", "det_p2"],
        detection_count=2,
        started_at=now,
        ended_at=now + timedelta(minutes=30),
        centroid_geometry=Coordinate(latitude=30.8502, longitude=75.8005),
        formation_configuration_id="v1.0-test",
        formation_configuration_version="v1.0",
    )


@pytest.fixture
def mock_jamnagar_event() -> Event:
    now = datetime(2026, 8, 1, 8, 30, tzinfo=UTC)
    return Event(
        event_id="ev_jamnagar_ind_001",
        detection_ids=["det_j1", "det_j2", "det_j3"],
        detection_count=3,
        started_at=now,
        ended_at=now + timedelta(minutes=30),
        centroid_geometry=Coordinate(latitude=22.4501, longitude=70.0502),
        formation_configuration_id="v1.0-test",
        formation_configuration_version="v1.0",
    )


# =============================================================================
# 1. GROUND TRUTH JSON LOADING & PARSING
# =============================================================================


def test_ground_truth_loading_from_json() -> None:
    """Verify loading from fixture captures metadata, fields, and SHA-256 hash."""
    fixture_path = Path("fixtures/reference/agricultural_ground_truth_sample.json")
    records, file_hash = GroundTruthIngestionService.load_ground_truth_from_json(fixture_path)

    assert len(records) == 3
    assert len(file_hash) == 64
    assert records[0].source_id == "icar_pau_crop_burn_registry_2026"
    assert records[0].tier == LabelTier.TIER_A_AUTHORITATIVE
    assert records[0].claim_class == "crop_residue"
    assert records[0].geometry.latitude == 30.8500
    assert records[0].geometry.longitude == 75.8000


# =============================================================================
# 2. SPATIAL & TEMPORAL MATCHING TOLERANCE
# =============================================================================


def test_event_ground_truth_matching_success(mock_punjab_event: Event) -> None:
    """Verify event matching within 2000m and 24h produces Tier A ReferenceEvidence."""
    fixture_path = Path("fixtures/reference/agricultural_ground_truth_sample.json")
    records, _ = GroundTruthIngestionService.load_ground_truth_from_json(fixture_path)

    matched = GroundTruthIngestionService.match_events_to_ground_truth(
        events=[mock_punjab_event],
        ground_truth_records=records,
        max_distance_meters=2000.0,
        max_temporal_delta_hours=24.0,
    )

    assert len(matched) == 1
    ev = matched[0]
    assert ev.entity_id == "ev_punjab_crop_001"
    assert ev.claim_class == "non_industrial"
    assert ev.tier == LabelTier.TIER_A_AUTHORITATIVE
    assert ev.provenance_type == LabelProvenanceType.GROUND_TRUTH
    assert ev.evidence_payload["source_record_id"] == "PAU_LUD_2026_001"
    assert ev.evidence_payload["distance_meters"] < 200.0


# =============================================================================
# 3. SPATIAL MATCHING REJECTION
# =============================================================================


def test_event_ground_truth_matching_spatial_rejection(mock_jamnagar_event: Event) -> None:
    """Verify event located far away (>2000m) from reference points is rejected."""
    fixture_path = Path("fixtures/reference/agricultural_ground_truth_sample.json")
    records, _ = GroundTruthIngestionService.load_ground_truth_from_json(fixture_path)

    matched = GroundTruthIngestionService.match_events_to_ground_truth(
        events=[mock_jamnagar_event],  # Located in Gujarat, ground truth in Punjab
        ground_truth_records=records,
        max_distance_meters=2000.0,
        max_temporal_delta_hours=24.0,
    )

    assert len(matched) == 0


# =============================================================================
# 4. TEMPORAL MATCHING REJECTION
# =============================================================================


def test_event_ground_truth_matching_temporal_rejection() -> None:
    """Verify event at the same coordinate but days later is rejected."""
    late_event = Event(
        event_id="ev_punjab_late_001",
        detection_ids=["det_late1"],
        detection_count=1,
        started_at=datetime(2026, 8, 15, 8, 30, tzinfo=UTC),  # 14 days later
        ended_at=datetime(2026, 8, 15, 9, 0, tzinfo=UTC),
        centroid_geometry=Coordinate(latitude=30.8500, longitude=75.8000),
        formation_configuration_id="v1.0-test",
        formation_configuration_version="v1.0",
    )

    fixture_path = Path("fixtures/reference/agricultural_ground_truth_sample.json")
    records, _ = GroundTruthIngestionService.load_ground_truth_from_json(fixture_path)

    matched = GroundTruthIngestionService.match_events_to_ground_truth(
        events=[late_event],
        ground_truth_records=records,
        max_distance_meters=2000.0,
        max_temporal_delta_hours=24.0,
    )

    assert len(matched) == 0


# =============================================================================
# 5. TIER A AUTHORITATIVE PRECEDENCE OVER TIER B
# =============================================================================


def test_tier_a_precedence_over_tier_b() -> None:
    """Verify Tier A ground truth takes precedence over Tier B contextual proximity."""
    now = datetime(2026, 8, 1, 8, 30, tzinfo=UTC)
    ev_id = "ev_contested_001"

    # Context says industrial (Tier B)
    tier_b_evidence = ReferenceEvidence(
        evidence_id="ref_ev_context_ind",
        source_name="OSM",
        source_role=SourceRole.GROUND_TRUTH_EVIDENCE,
        entity_id=ev_id,
        geometry=Coordinate(latitude=22.4500, longitude=70.0500),
        observed_at=now,
        claim_class="industrial",
        confidence_score=0.85,
        tier=LabelTier.TIER_B_STRONG_EVIDENCE,
        provenance_type=LabelProvenanceType.REFERENCE_LABEL,
    )

    # Authoritative ground truth survey says non_industrial (Tier A)
    tier_a_evidence = ReferenceEvidence(
        evidence_id="ref_gt_auth_non_ind",
        source_name="FIELD_SURVEY",
        source_role=SourceRole.GROUND_TRUTH_EVIDENCE,
        entity_id=ev_id,
        geometry=Coordinate(latitude=22.4500, longitude=70.0500),
        observed_at=now,
        claim_class="non_industrial",
        confidence_score=1.0,
        tier=LabelTier.TIER_A_AUTHORITATIVE,
        provenance_type=LabelProvenanceType.GROUND_TRUTH,
    )

    constructor = LabelConstructor(default_conflict_policy=LabelConflictPolicy.TIER_PRECEDENCE)
    decision = constructor.construct_label(
        target_id="target_industrial_segregation",
        entity_id=ev_id,
        evidence_items=[tier_b_evidence, tier_a_evidence],
    )

    assert decision.assigned_class == "non_industrial"
    assert decision.label_tier == LabelTier.TIER_A_AUTHORITATIVE
    assert decision.provenance_type == LabelProvenanceType.GROUND_TRUTH
    assert decision.is_train_eligible is True


# =============================================================================
# 6. ABSOLUTE ANTI-GEOGRAPHIC AUTO-LABELING (PUNJAB != NON-INDUSTRIAL WITHOUT EVIDENCE)
# =============================================================================


def test_punjab_without_evidence_is_unknown(mock_punjab_event: Event) -> None:
    """Verify Punjab event with no matched ground truth or context remains UNKNOWN."""
    constructor = LabelConstructor()
    decision = constructor.construct_label(
        target_id="target_industrial_segregation",
        entity_id=mock_punjab_event.event_id,
        evidence_items=[],  # No evidence
    )

    assert decision.assigned_class == "unknown"
    assert decision.label_tier == LabelTier.UNKNOWN
    assert decision.is_train_eligible is False
    assert decision.exclusion_reason == ExclusionReason.INSUFFICIENT_LABEL_EVIDENCE


# =============================================================================
# 7. ABSOLUTE ANTI-GEOGRAPHIC AUTO-LABELING (JAMNAGAR != INDUSTRIAL WITHOUT EVIDENCE)
# =============================================================================


def test_jamnagar_without_evidence_is_unknown(mock_jamnagar_event: Event) -> None:
    """Verify Jamnagar event with no matched evidence remains UNKNOWN."""
    constructor = LabelConstructor()
    decision = constructor.construct_label(
        target_id="target_industrial_segregation",
        entity_id=mock_jamnagar_event.event_id,
        evidence_items=[],  # No evidence
    )

    assert decision.assigned_class == "unknown"
    assert decision.label_tier == LabelTier.UNKNOWN
    assert decision.is_train_eligible is False
    assert decision.exclusion_reason == ExclusionReason.INSUFFICIENT_LABEL_EVIDENCE


# =============================================================================
# 8. CONFLICTING EVIDENCE PRODUCES UNKNOWN & INELIGIBLE
# =============================================================================


def test_conflicting_same_tier_evidence_handling() -> None:
    """Verify conflicting evidence of equal tier produces UNKNOWN and marks ineligible."""
    now = datetime(2026, 8, 1, 8, 30, tzinfo=UTC)
    ev_id = "ev_conflict_same_tier"

    ev1 = ReferenceEvidence(
        evidence_id="ref_gt_1",
        source_name="SURVEY_A",
        source_role=SourceRole.GROUND_TRUTH_EVIDENCE,
        entity_id=ev_id,
        geometry=Coordinate(latitude=22.0, longitude=70.0),
        observed_at=now,
        claim_class="industrial",
        confidence_score=0.9,
        tier=LabelTier.TIER_A_AUTHORITATIVE,
        provenance_type=LabelProvenanceType.GROUND_TRUTH,
    )

    ev2 = ReferenceEvidence(
        evidence_id="ref_gt_2",
        source_name="SURVEY_B",
        source_role=SourceRole.GROUND_TRUTH_EVIDENCE,
        entity_id=ev_id,
        geometry=Coordinate(latitude=22.0, longitude=70.0),
        observed_at=now,
        claim_class="non_industrial",
        confidence_score=0.9,
        tier=LabelTier.TIER_A_AUTHORITATIVE,
        provenance_type=LabelProvenanceType.GROUND_TRUTH,
    )

    constructor = LabelConstructor(default_conflict_policy=LabelConflictPolicy.TIER_PRECEDENCE)
    decision = constructor.construct_label(
        target_id="target_industrial_segregation",
        entity_id=ev_id,
        evidence_items=[ev1, ev2],
    )

    assert decision.assigned_class == "unknown"
    assert decision.has_conflicting_evidence is True
    assert decision.is_train_eligible is False
    assert decision.exclusion_reason == ExclusionReason.CONFLICTING_LABEL_EVIDENCE


# =============================================================================
# 9. DETERMINISM OF REPEATED MATCHING & SYNTHESIS
# =============================================================================


def test_matching_determinism(mock_punjab_event: Event) -> None:
    """Verify repeated matching and label generation produce identical digests and decisions."""
    fixture_path = Path("fixtures/reference/agricultural_ground_truth_sample.json")
    records, _ = GroundTruthIngestionService.load_ground_truth_from_json(fixture_path)

    m1 = GroundTruthIngestionService.match_events_to_ground_truth(
        events=[mock_punjab_event],
        ground_truth_records=records,
    )
    m2 = GroundTruthIngestionService.match_events_to_ground_truth(
        events=[mock_punjab_event],
        ground_truth_records=records,
    )

    assert len(m1) == len(m2) == 1
    assert m1[0].evidence_id == m2[0].evidence_id
    assert m1[0].model_dump() == m2[0].model_dump()


# =============================================================================
# 10. END-TO-END PIPELINE WITH AGRICULTURAL LABELED EVENTS
# =============================================================================


def test_end_to_end_data_002_pipeline_with_agricultural_events(
    test_config: ScientificConfig,
) -> None:
    """Verify complete pipeline ingests FIRMS, constructs events, matches GT, and builds SupervisedDataset."""
    # 1. FIRMS detections in Punjab
    punjab_csv = (
        "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_ti5,frp,daynight\n"
        "30.8501,75.8002,345.2,0.38,0.37,2026-08-01,0830,N,VIIRS,nominal,2.0NRT,295.4,18.5,D\n"
        "30.8505,75.8008,350.8,0.38,0.37,2026-08-01,0830,N,VIIRS,nominal,2.0NRT,296.1,24.2,D\n"
    )

    det_ds = FirmsDataActivationService.activate_from_csv(
        csv_input=punjab_csv.encode("utf-8"),
        study_area=PUNJAB_AGRICULTURAL,
        requested_start_date="2026-08-01",
        requested_end_date="2026-08-10",
        source_product="VIIRS_SNPP_NRT",
        sensor="VIIRS",
    )

    # 2. Events
    ev_ds = RealEventConstructionService.construct_events_and_sources(
        detection_dataset=det_ds,
        config=test_config,
    )
    assert len(ev_ds.events) > 0

    # 3. Ground Truth Matching
    fixture_path = Path("fixtures/reference/agricultural_ground_truth_sample.json")
    records, _ = GroundTruthIngestionService.load_ground_truth_from_json(fixture_path)
    gt_evidence = GroundTruthIngestionService.match_events_to_ground_truth(
        events=ev_ds.events,
        ground_truth_records=records,
    )
    assert len(gt_evidence) > 0

    # 4. Context Enrichment with External Evidence
    enriched_ds = RealContextLabelingService.enrich_and_adjudicate_dataset(
        event_dataset=ev_ds,
        candidate_features=[],  # No OSM industrial features in rural Punjab
        config=test_config,
        external_reference_evidence=gt_evidence,
    )
    assert len(enriched_ds.reference_labels) > 0
    assert enriched_ds.reference_labels[0].assigned_class == "non_industrial"
    assert enriched_ds.reference_labels[0].label_tier == LabelTier.TIER_A_AUTHORITATIVE
    assert enriched_ds.reference_labels[0].is_train_eligible is True

    # 5. SupervisedDataset Synthesis
    builder = SupervisedDatasetBuilder()
    supervised_ds = builder.build_from_real_enriched_dataset(
        enriched_dataset=enriched_ds,
        detection_dataset=det_ds,
        target_ids=["target_industrial_segregation"],
    )

    assert len(supervised_ds.records) > 0
    record = supervised_ds.records[0]
    assert record.row_status in (
        DatasetRowStatus.TRAIN_ELIGIBLE,
        DatasetRowStatus.VALIDATION_ELIGIBLE,
        DatasetRowStatus.TEST_ELIGIBLE,
    )
    assert record.labels["target_industrial_segregation"].assigned_class == "non_industrial"
    assert len(record.feature_record.features) == 30


# =============================================================================
# 11. MULTI-FORMAT LOADERS (CSV, GEOJSON, CATALOG DISCOVERY, FACILITIES)
# =============================================================================


def test_load_ground_truth_from_csv(tmp_path: Path) -> None:
    """Verify CSV ground truth ingestion with custom fields and header normalization."""
    csv_file = tmp_path / "crop_burns.csv"
    csv_file.write_text(
        "source_record_id,observed_at,latitude,longitude,claim_class,confidence,country,region,fire_regime,tier\n"
        "BURN_001,2026-08-01T10:00:00Z,30.8500,75.8000,crop_residue,0.95,India,Punjab,agricultural,TIER_A_AUTHORITATIVE\n"
        "BURN_002,2026-08-02T14:30:00Z,30.2400,75.8400,agricultural,0.90,India,Punjab,agricultural,TIER_B_STRONG_EVIDENCE\n"
    )

    records, fhash = GroundTruthIngestionService.load_ground_truth_from_csv(csv_file)
    assert len(records) == 2
    assert len(fhash) == 64
    assert records[0].source_record_id == "BURN_001"
    assert records[0].claim_class == "crop_residue"
    assert records[0].tier == LabelTier.TIER_A_AUTHORITATIVE
    assert records[1].tier == LabelTier.TIER_B_STRONG_EVIDENCE


def test_load_ground_truth_from_geojson(tmp_path: Path) -> None:
    """Verify GeoJSON ground truth ingestion for Point and Polygon features."""
    geojson_file = tmp_path / "wildfires.geojson"
    geojson_file.write_text(
        json.dumps({
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [-119.82, 37.54]},
                    "properties": {
                        "source_record_id": "WF_001",
                        "observed_at": "2026-08-02T16:00:00Z",
                        "claim_class": "wildfire",
                        "confidence": 1.0,
                        "country": "USA",
                        "region": "California",
                        "fire_regime": "forest_natural",
                        "tier": "TIER_A_AUTHORITATIVE",
                    },
                },
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [-119.83, 37.53],
                            [-119.81, 37.53],
                            [-119.81, 37.55],
                            [-119.83, 37.55],
                            [-119.83, 37.53],
                        ]],
                    },
                    "properties": {
                        "source_record_id": "WF_POLY_002",
                        "observed_at": "2026-08-02T18:00:00Z",
                        "claim_class": "wildfire",
                        "country": "USA",
                        "region": "California",
                        "fire_regime": "forest_natural",
                    },
                },
            ],
        })
    )

    records, fhash = GroundTruthIngestionService.load_ground_truth_from_geojson(geojson_file)
    assert len(records) == 2
    assert records[0].source_record_id == "WF_001"
    assert records[0].geometry.latitude == 37.54
    assert records[1].source_record_id == "WF_POLY_002"
    assert round(records[1].geometry.latitude, 2) == 37.54


def test_discover_and_load_catalog() -> None:
    """Verify recursive catalog discovery across JSON, CSV, and GeoJSON files."""
    records, hashes = GroundTruthIngestionService.discover_and_load_catalog(
        ["data/real/reference", "fixtures/reference"]
    )
    assert len(records) >= 20
    assert len(hashes) >= 5


def test_load_facility_context_features() -> None:
    """Verify loading industrial facility context features."""
    features, hashes = GroundTruthIngestionService.load_facility_context_features(
        "data/real/reference/facilities"
    )
    assert len(features) >= 15
    assert len(hashes) >= 3
    assert any("Jamnagar" in (f.facility_name or "") for f in features)
    assert any("Singrauli" in (f.facility_name or "") for f in features)


def test_spatial_and_temporal_boundary_matching() -> None:
    """Verify exact 2000m and 24h boundary behavior."""
    ev_time = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)
    event = Event(
        event_id="ev_boundary_test",
        detection_ids=["d1"],
        detection_count=1,
        started_at=ev_time,
        ended_at=ev_time + timedelta(minutes=10),
        centroid_geometry=Coordinate(latitude=22.0000, longitude=70.0000),
        formation_configuration_id="v1.0-test",
        formation_configuration_version="v1.0",
    )

    # Within spatial & temporal thresholds (~1100m, 23.5h delta)
    gt_match = ExternalReferenceRecord(
        source_id="TEST_SRC",
        source_name="Test Reference",
        source_type="REGISTRY",
        source_record_id="REC_PASS",
        observed_at=ev_time + timedelta(hours=23, minutes=30),
        geometry=Coordinate(latitude=22.0100, longitude=70.0000),
        claim_class="industrial",
        confidence=1.0,
        source_snapshot_hash="hashpass",
    )

    # Exceeds spatial threshold (~3300m)
    gt_fail_dist = ExternalReferenceRecord(
        source_id="TEST_SRC",
        source_name="Test Reference",
        source_type="REGISTRY",
        source_record_id="REC_FAIL_DIST",
        observed_at=ev_time,
        geometry=Coordinate(latitude=22.0300, longitude=70.0000),
        claim_class="industrial",
        confidence=1.0,
        source_snapshot_hash="hashfaildist",
    )

    # Exceeds temporal threshold (24.5h)
    gt_fail_time = ExternalReferenceRecord(
        source_id="TEST_SRC",
        source_name="Test Reference",
        source_type="REGISTRY",
        source_record_id="REC_FAIL_TIME",
        observed_at=ev_time + timedelta(hours=24, minutes=30),
        geometry=Coordinate(latitude=22.0000, longitude=70.0000),
        claim_class="industrial",
        confidence=1.0,
        source_snapshot_hash="hashfailtime",
    )

    matches = GroundTruthIngestionService.match_events_to_ground_truth(
        events=[event],
        ground_truth_records=[gt_match, gt_fail_dist, gt_fail_time],
        max_distance_meters=2000.0,
        max_temporal_delta_hours=24.0,
    )

    assert len(matches) == 1
    assert matches[0].evidence_payload["source_record_id"] == "REC_PASS"
    assert matches[0].claim_class == "industrial"

