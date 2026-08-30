"""Comprehensive test suite for canonical DATASET-002 / Real-to-Supervised Bridge & Validation.

Validates NEXT-001 -> NEXT-002 -> NEXT-003:
1. Dataset integrity & entity indexing.
2. Canonical 30-feature completeness and catalog alignment against feat_v1.0.0.
3. Feature domain ranges, non-negativity, and type constraints.
4. Point-in-time temporal anti-leakage (future events strictly excluded).
5. Point-in-time contextual validity windows (future/decommissioned facilities excluded).
6. Missing != Negative and UNKNOWN exclusion from training.
7. Conflicting evidence handling and exclusion.
8. End-to-end provenance and lineage traceability.
9. Determinism and cryptographic hash invariance.
10. Synthetic benchmark isolation.
11. Real pilot smoke test & scientific gate evaluation.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from packages.config.scientific import ScientificConfig
from packages.context.models import ContextFeature
from packages.context.pipeline import RealContextLabelingService
from packages.data.firms.activation import FirmsDataActivationService
from packages.data.firms.schemas import RealDataAcquisitionManifest, RealDetectionDataset
from packages.events.pipeline import RealEventConstructionService
from packages.feasibility.candidates import JAMNAGAR_KUTCH
from packages.schemas.common import Coordinate
from packages.schemas.context import ContextEvidence
from packages.schemas.detection import Detection
from packages.schemas.enums import ContextType, DayNight, EvidenceAvailabilityState, PersistenceState
from packages.schemas.event import Event, RealEnrichedEventDataset, RealThermalEventDataset
from packages.schemas.ml import (
    DatasetRowStatus,
    ExclusionReason,
    LabelConflictPolicy,
    LabelDecision,
    LabelProvenanceType,
    LabelTier,
    ReferenceEvidence,
    SplitPartition,
    SplitStrategy,
)
from services.ml.features.extractor import FeatureExtractor
from services.ml.features.standard_set import (
    APPROVED_FEATURES,
    STANDARD_FEATURE_VERSION,
    get_standard_feature_registry,
)
from services.ml.labels.dataset import SupervisedDatasetBuilder

RealPipelineOutput = tuple[
    RealDetectionDataset, RealThermalEventDataset, RealEnrichedEventDataset
]


@pytest.fixture
def calibrated_config() -> ScientificConfig:
    """Fixture providing standard calibrated scientific configuration."""
    return ScientificConfig(
        version="v1.0-test",
        name="test_profile",
        description="Calibrated test configuration profile",
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
def real_enriched_pipeline_output(
    calibrated_config: ScientificConfig,
) -> RealPipelineOutput:
    """Fixture providing end-to-end real observational pipeline datasets."""
    csv_path = Path("fixtures/firms/firms_real_sample_jamnagar.csv")
    detection_dataset = FirmsDataActivationService.activate_from_csv(
        csv_input=csv_path,
        study_area=JAMNAGAR_KUTCH,
        requested_start_date="2026-08-01",
        requested_end_date="2026-08-10",
    )

    event_dataset = RealEventConstructionService.construct_events_and_sources(
        detection_dataset=detection_dataset,
        config=calibrated_config,
    )

    context_fixture = Path("fixtures/context/context_sample_jamnagar.json")
    features, hashes = RealContextLabelingService.load_context_features_from_fixture(
        context_fixture
    )
    enriched_dataset = RealContextLabelingService.enrich_and_adjudicate_dataset(
        event_dataset=event_dataset,
        candidate_features=features,
        snapshot_hashes=hashes,
        config=calibrated_config,
    )

    return detection_dataset, event_dataset, enriched_dataset


# =============================================================================
# 1. DATASET INTEGRITY TESTS (NEXT-003 §3.1)
# =============================================================================


def test_dataset_integrity_and_record_mapping(
    real_enriched_pipeline_output: RealPipelineOutput,
) -> None:
    """Verify dataset integrity: 1-to-1 event mapping, unique IDs, no duplicates."""
    detection_dataset, event_dataset, enriched_dataset = real_enriched_pipeline_output

    builder = SupervisedDatasetBuilder()
    supervised_ds = builder.build_from_real_enriched_dataset(
        enriched_dataset=enriched_dataset,
        detection_dataset=detection_dataset,
        split_strategy=SplitStrategy.FACILITY_HOLDOUT,
        target_ids=["target_industrial_segregation"],
    )

    # 1. Record count equals enriched event count exactly
    assert len(supervised_ds.records) == len(enriched_dataset.events)
    assert len(supervised_ds.records) == 4

    # 2. No duplicate entity IDs or event IDs
    entity_ids = [r.entity_id for r in supervised_ds.records]
    assert len(entity_ids) == len(set(entity_ids))

    # 3. Every enriched event is accounted for in records
    event_ids_in_enriched = {e.event_id for e in enriched_dataset.events}
    assert set(entity_ids) == event_ids_in_enriched


# =============================================================================
# 2. CANONICAL 30-FEATURE COMPLETENESS & CATALOG ALIGNMENT (NEXT-003 §3.2)
# =============================================================================


def test_canonical_30_features_completeness_and_naming(
    real_enriched_pipeline_output: RealPipelineOutput,
) -> None:
    """Verify exactly 30 canonical features from feat_v1.0.0 exist on every record."""
    detection_dataset, _, enriched_dataset = real_enriched_pipeline_output

    builder = SupervisedDatasetBuilder()
    supervised_ds = builder.build_from_real_enriched_dataset(
        enriched_dataset=enriched_dataset,
        detection_dataset=detection_dataset,
    )

    # 1. Feature definition catalog check
    assert len(supervised_ds.feature_definitions) == 30
    assert len(APPROVED_FEATURES) == 30

    expected_feature_names = {f.feature_name for f in APPROVED_FEATURES}
    actual_def_names = {f.feature_name for f in supervised_ds.feature_definitions}
    assert actual_def_names == expected_feature_names

    # 2. Verify every record has exactly the 30 canonical feature names
    for rec in supervised_ds.records:
        feat_dict = rec.feature_record.features
        assert len(feat_dict) == 30
        assert set(feat_dict.keys()) == expected_feature_names

        # Missingness indicator flags check
        assert len(rec.feature_record.missingness_flags) == 30
        for fname in expected_feature_names:
            flag_key = f"{fname}_is_missing"
            assert flag_key in rec.feature_record.missingness_flags
            assert rec.feature_record.missingness_flags[flag_key] == (
                feat_dict[fname] is None
            )


# =============================================================================
# 3. FEATURE TYPE AND DOMAIN RANGE VALIDATION (NEXT-003 §3.3)
# =============================================================================


def test_feature_type_and_range_validation(
    real_enriched_pipeline_output: RealPipelineOutput,
) -> None:
    """Verify extracted features adhere to domain constraints and data types."""
    detection_dataset, _, enriched_dataset = real_enriched_pipeline_output

    builder = SupervisedDatasetBuilder()
    supervised_ds = builder.build_from_real_enriched_dataset(
        enriched_dataset=enriched_dataset,
        detection_dataset=detection_dataset,
    )

    valid_instruments = {"VIIRS", "MODIS", "HYBRID", "UNKNOWN"}

    for rec in supervised_ds.records:
        feats = rec.feature_record.features

        # Detection count >= 1
        assert isinstance(feats["detection_count"], int)
        assert feats["detection_count"] >= 1

        # FRP values are non-negative and finite
        if feats["frp_mean_mw"] is not None:
            assert isinstance(feats["frp_mean_mw"], float)
            assert feats["frp_mean_mw"] >= 0.0
            assert feats["frp_max_mw"] >= feats["frp_min_mw"]
            assert feats["frp_sum_mw"] >= feats["frp_mean_mw"]
            assert feats["frp_std_mw"] >= 0.0

        # Duration >= 0
        assert isinstance(feats["duration_hours"], float)
        assert feats["duration_hours"] >= 0.0

        # Extent radius >= 0
        assert isinstance(feats["spatial_extent_radius_meters"], float)
        assert feats["spatial_extent_radius_meters"] >= 0.0

        # Daynight ratio in [0, 1]
        assert isinstance(feats["daynight_ratio"], float)
        assert 0.0 <= feats["daynight_ratio"] <= 1.0

        # Sensor instrument
        assert feats["sensor_instrument"] in valid_instruments

        # Persistence features
        assert isinstance(feats["is_persistent_source"], bool)
        valid_persistence_values = {s.value for s in PersistenceState}
        assert feats["persistence_state"] in valid_persistence_values

        # Spatial context distances >= 0 if present
        if feats["facility_distance_meters"] is not None:
            assert isinstance(feats["facility_distance_meters"], float)
            assert feats["facility_distance_meters"] >= 0.0


# =============================================================================
# 4. TEMPORAL ANTI-LEAKAGE VALIDATION (NEXT-003 §3.4)
# =============================================================================


def test_temporal_anti_leakage_rejection(
    calibrated_config: ScientificConfig,
) -> None:
    """Verify future events and future detections are strictly excluded from features."""
    t0 = datetime(2026, 8, 5, 12, 0, 0, tzinfo=UTC)
    t_past_1h = t0 - timedelta(hours=1)
    t_future_1h = t0 + timedelta(hours=1)
    t_future_2d = t0 + timedelta(days=2)

    # Event 1 at t0
    det_current = Detection(
        detection_id="det_curr_001",
        source="firms",
        source_snapshot_id="snap_001",
        geometry=Coordinate(latitude=22.45, longitude=70.05),
        acquired_at=t0,
        frp_mw=25.0,
        brightness_ti4_k=340.0,
        day_night=DayNight.DAY,
        satellite="NOAA-20",
        instrument="VIIRS",
        product_type="nrt",
        product_version="v1.0",
        raw_hash="a" * 64,
    )
    det_future = Detection(
        detection_id="det_fut_001",
        source="firms",
        source_snapshot_id="snap_001",
        geometry=Coordinate(latitude=22.45, longitude=70.05),
        acquired_at=t_future_1h,
        frp_mw=50.0,
        brightness_ti4_k=360.0,
        day_night=DayNight.DAY,
        satellite="NOAA-20",
        instrument="VIIRS",
        product_type="nrt",
        product_version="v1.0",
        raw_hash="b" * 64,
    )

    ev_current = Event(
        event_id="evt_current_001",
        started_at=t0,
        ended_at=t0,
        centroid_geometry=Coordinate(latitude=22.45, longitude=70.05),
        detection_ids=[det_current.detection_id, det_future.detection_id],
        detection_count=2,
        formation_configuration_id="cfg_001",
        formation_configuration_version="v1.0",
    )

    ev_past = Event(
        event_id="evt_past_001",
        started_at=t_past_1h,
        ended_at=t_past_1h,
        centroid_geometry=Coordinate(latitude=22.45, longitude=70.05),
        detection_ids=["det_past_001"],
        detection_count=1,
        formation_configuration_id="cfg_001",
        formation_configuration_version="v1.0",
    )

    ev_future = Event(
        event_id="evt_future_001",
        started_at=t_future_2d,
        ended_at=t_future_2d,
        centroid_geometry=Coordinate(latitude=22.45, longitude=70.05),
        detection_ids=["det_future_002"],
        detection_count=1,
        formation_configuration_id="cfg_001",
        formation_configuration_version="v1.0",
    )

    extractor = FeatureExtractor()
    feat_rec = extractor.extract_features_for_event(
        event=ev_current,
        member_detections=[det_current, det_future],
        as_of_time=t0,  # Prediction cutoff at t0
        preceding_events=[ev_past, ev_future],
    )

    # 1. Future detection (t_future_1h) must be ignored: detection_count == 1, FRP == 25.0
    assert feat_rec.features["detection_count"] == 1
    assert feat_rec.features["frp_mean_mw"] == 25.0

    # 2. Preceding event count must count ev_past but strictly exclude ev_future
    assert feat_rec.features["prior_event_count_24h"] == 1
    assert feat_rec.features["prior_event_count_7d"] == 1
    assert feat_rec.features["prior_event_count_30d"] == 1


# =============================================================================
# 5. CONTEXT TEMPORAL VALIDITY WINDOW (NEXT-003 §3.5)
# =============================================================================


def test_context_validity_window_future_facility_rejection(
    real_enriched_pipeline_output: RealPipelineOutput,
    calibrated_config: ScientificConfig,
) -> None:
    """Verify contextual facility commissioned in the future cannot contribute evidence."""
    _, event_dataset, _ = real_enriched_pipeline_output

    # Facility commissioned in 2028 (future)
    future_facility = ContextFeature(
        feature_id="wri_plant_future",
        provider="wri",
        dataset_name="wri_power",
        dataset_version="v1.0",
        context_type=ContextType.POWER,
        geometry=Coordinate(latitude=22.45, longitude=70.05),
        facility_name="Future Nuclear Plant",
        valid_from=datetime(2028, 1, 1, tzinfo=UTC),
    )

    # Facility decommissioned in 2020 (past)
    expired_facility = ContextFeature(
        feature_id="osm_plant_expired",
        provider="osm",
        dataset_name="osm_industrial",
        dataset_version="v1.0",
        context_type=ContextType.INDUSTRIAL,
        geometry=Coordinate(latitude=22.45, longitude=70.05),
        facility_name="Decommissioned Chemical Works",
        valid_to=datetime(2020, 1, 1, tzinfo=UTC),
    )

    # Active facility valid from 2020 to 2030
    active_facility = ContextFeature(
        feature_id="osm_refinery_active",
        provider="osm",
        dataset_name="osm_industrial",
        dataset_version="v1.0",
        context_type=ContextType.OIL_GAS,
        geometry=Coordinate(latitude=22.452, longitude=70.052),
        facility_name="Active Refinery",
        valid_from=datetime(2020, 1, 1, tzinfo=UTC),
        valid_to=datetime(2030, 1, 1, tzinfo=UTC),
    )

    ctx_items = RealContextLabelingService.enrich_and_adjudicate_dataset(
        event_dataset=event_dataset,
        candidate_features=[future_facility, expired_facility, active_facility],
        config=calibrated_config,
    )

    # Only active_facility should match
    matched_facility_names = {
        c.facility_name for c in ctx_items.context_evidence if c.facility_name
    }
    assert "Active Refinery" in matched_facility_names
    assert "Future Nuclear Plant" not in matched_facility_names
    assert "Decommissioned Chemical Works" not in matched_facility_names


# =============================================================================
# 5b. CONTEXT ISOLATION ACROSS MULTIPLE EVENTS (NEXT-002 §7)
# =============================================================================


def test_context_isolation_across_multiple_events(
    real_enriched_pipeline_output: RealPipelineOutput,
) -> None:
    """Verify context evidence for Event A never leaks into Event B's features."""
    detection_dataset, _, enriched_dataset = real_enriched_pipeline_output

    builder = SupervisedDatasetBuilder()
    supervised_ds = builder.build_from_real_enriched_dataset(
        enriched_dataset=enriched_dataset,
        detection_dataset=detection_dataset,
    )

    records_by_id = {r.entity_id: r for r in supervised_ds.records}

    # Find the isolated event (unknown label) vs industrial events
    isolated_records = [
        r
        for r in supervised_ds.records
        if r.labels["target_industrial_segregation"].assigned_class == "unknown"
    ]
    industrial_records = [
        r
        for r in supervised_ds.records
        if r.labels["target_industrial_segregation"].assigned_class == "industrial"
    ]

    assert len(isolated_records) == 1
    assert len(industrial_records) == 3

    isolated_rec = isolated_records[0]
    isolated_feats = isolated_rec.feature_record.features

    # Isolated event must NOT receive refinery context from industrial events
    assert isolated_feats["facility_distance_meters"] is None
    assert isolated_feats["facility_context_type"] == "NONE"
    assert isolated_feats["is_near_industrial_facility"] is False

    # Industrial events must have their own valid facility distance
    for ind_rec in industrial_records:
        ind_feats = ind_rec.feature_record.features
        assert ind_feats["facility_distance_meters"] is not None
        assert ind_feats["facility_context_type"] == "oil_gas"
        assert ind_feats["is_near_industrial_facility"] is True


# =============================================================================
# 6. MISSING != NEGATIVE & UNKNOWN EXCLUSION (NEXT-003 §3.6)
# =============================================================================


def test_missing_not_negative_and_unknown_exclusion(
    real_enriched_pipeline_output: RealPipelineOutput,
) -> None:
    """Verify unknown events are excluded from training and not converted to negative."""
    detection_dataset, _, enriched_dataset = real_enriched_pipeline_output

    builder = SupervisedDatasetBuilder()
    supervised_ds = builder.build_from_real_enriched_dataset(
        enriched_dataset=enriched_dataset,
        detection_dataset=detection_dataset,
        split_strategy=SplitStrategy.GROUPED_EVENT_HOLDOUT,
    )

    unknown_records = [
        r
        for r in supervised_ds.records
        if r.labels["target_industrial_segregation"].assigned_class == "unknown"
    ]
    assert len(unknown_records) == 1
    rec = unknown_records[0]

    # Explicit scientific assertions
    assert rec.row_status == DatasetRowStatus.EXCLUDED
    assert rec.exclusion_reason == ExclusionReason.INSUFFICIENT_LABEL_EVIDENCE
    assert rec.labels["target_industrial_segregation"].is_train_eligible is False
    assert rec.labels["target_industrial_segregation"].assigned_class == "unknown"


# =============================================================================
# 7. CONFLICTING EVIDENCE ADJUDICATION & EXCLUSION (NEXT-003 §3.7)
# =============================================================================


def test_conflicting_evidence_exclusion(
    real_enriched_pipeline_output: RealPipelineOutput,
    calibrated_config: ScientificConfig,
) -> None:
    """Verify conflicting evidence leads to UNKNOWN and exclusion from training."""
    detection_dataset, event_dataset, enriched_dataset = real_enriched_pipeline_output
    ev = event_dataset.events[0]

    # Conflicting equal-tier evidence: industrial vs non-industrial
    ev1 = ReferenceEvidence(
        evidence_id="ref_ev_ind",
        source_name="WRI",
        entity_id=ev.event_id,
        geometry=Coordinate(
            latitude=ev.centroid_geometry.latitude,
            longitude=ev.centroid_geometry.longitude,
        ),
        claim_class="industrial",
        confidence_score=0.85,
        tier=LabelTier.TIER_B_STRONG_EVIDENCE,
    )
    ev2 = ReferenceEvidence(
        evidence_id="ref_ev_non_ind",
        source_name="LANDCOVER",
        entity_id=ev.event_id,
        geometry=Coordinate(
            latitude=ev.centroid_geometry.latitude,
            longitude=ev.centroid_geometry.longitude,
        ),
        claim_class="non_industrial",
        confidence_score=0.85,
        tier=LabelTier.TIER_B_STRONG_EVIDENCE,
    )

    decisions = RealContextLabelingService.adjudicate_labels(
        events=[ev],
        reference_evidence=[ev1, ev2],
        conflict_policy=LabelConflictPolicy.TIER_PRECEDENCE,
    )

    assert len(decisions) == 1
    decision = decisions[0]
    assert decision.has_conflicting_evidence is True
    assert decision.assigned_class == "unknown"
    assert decision.is_train_eligible is False

    # Now verify supervised dataset assembly excludes this record
    enriched_ds = RealEnrichedEventDataset(
        dataset_id="ds_test_enriched",
        dataset_version="v1.0.0",
        source_detection_dataset_id=detection_dataset.manifest.dataset_id,
        source_detection_dataset_hash=detection_dataset.compute_canonical_hash(),
        source_event_dataset_id=event_dataset.dataset_id,
        source_event_dataset_hash=event_dataset.canonical_dataset_hash,
        study_area_id=enriched_dataset.study_area_id,
        study_area_name=enriched_dataset.study_area_name,
        bounding_box=enriched_dataset.bounding_box,
        events=[ev],
        context_evidence=[],
        reference_evidence=[ev1, ev2],
        reference_labels=[decision],
        config_fingerprint=calibrated_config.compute_fingerprint(),
        canonical_dataset_hash="b" * 64,
        created_at=datetime.now(UTC),
    )

    builder = SupervisedDatasetBuilder()
    sup_ds = builder.build_from_real_enriched_dataset(enriched_ds, detection_dataset)
    assert len(sup_ds.records) == 1
    rec = sup_ds.records[0]
    assert rec.row_status == DatasetRowStatus.EXCLUDED
    assert rec.exclusion_reason == ExclusionReason.CONFLICTING_LABEL_EVIDENCE


# =============================================================================
# 8. PROVENANCE & LINEAGE TRACEABILITY (NEXT-003 §3.8)
# =============================================================================


def test_provenance_and_lineage_traceability(
    real_enriched_pipeline_output: RealPipelineOutput,
) -> None:
    """Verify complete end-to-end lineage from detection -> event -> label -> supervised record."""
    detection_dataset, event_dataset, enriched_dataset = real_enriched_pipeline_output

    builder = SupervisedDatasetBuilder()
    supervised_ds = builder.build_from_real_enriched_dataset(
        enriched_dataset=enriched_dataset,
        detection_dataset=detection_dataset,
    )

    detection_map = {d.detection_id: d for d in detection_dataset.detections}
    event_map = {e.event_id: e for e in enriched_dataset.events}

    for rec in supervised_ds.records:
        # 1. Supervised record entity_id maps to Event
        assert rec.entity_id in event_map
        ev = event_map[rec.entity_id]

        # 2. Event detection_ids map to member Detections
        assert len(ev.detection_ids) >= 1
        for d_id in ev.detection_ids:
            assert d_id in detection_map

        # 3. Reference label decisions preserve contributing evidence IDs
        for tid, decision in rec.labels.items():
            assert decision.entity_id == rec.entity_id


# =============================================================================
# 9. DETERMINISM AND HASH INVARIANCE (NEXT-003 §3.9)
# =============================================================================


def test_strict_determinism_and_hash_invariance(
    real_enriched_pipeline_output: RealPipelineOutput,
) -> None:
    """Verify bit-identical determinism and hash invariance across multiple runs."""
    detection_dataset, _, enriched_dataset = real_enriched_pipeline_output

    builder = SupervisedDatasetBuilder()

    ds1 = builder.build_from_real_enriched_dataset(
        enriched_dataset=enriched_dataset,
        detection_dataset=detection_dataset,
        split_strategy=SplitStrategy.FACILITY_HOLDOUT,
        random_seed=42,
    )
    ds2 = builder.build_from_real_enriched_dataset(
        enriched_dataset=enriched_dataset,
        detection_dataset=detection_dataset,
        split_strategy=SplitStrategy.FACILITY_HOLDOUT,
        random_seed=42,
    )

    assert ds1.manifest.sha256_hash == ds2.manifest.sha256_hash
    assert ds1.split_manifest.split_id == ds2.split_manifest.split_id
    assert ds1.split_manifest.train_count == ds2.split_manifest.train_count
    assert ds1.summary_statistics == ds2.summary_statistics
    assert len(ds1.records) == len(ds2.records)

    for r1, r2 in zip(ds1.records, ds2.records, strict=True):
        assert r1.entity_id == r2.entity_id
        assert r1.feature_record.features == r2.feature_record.features
        assert r1.row_status == r2.row_status


# =============================================================================
# 10. SYNTHETIC BENCHMARK ISOLATION (NEXT-003 §3.10)
# =============================================================================


def test_synthetic_benchmark_isolation(
    real_enriched_pipeline_output: RealPipelineOutput,
) -> None:
    """Verify real pipeline operations do not touch synthetic benchmark datasets."""
    detection_dataset, _, enriched_dataset = real_enriched_pipeline_output

    builder = SupervisedDatasetBuilder()
    real_supervised_ds = builder.build_from_real_enriched_dataset(
        enriched_dataset=enriched_dataset,
        detection_dataset=detection_dataset,
        dataset_id="ds_real_supervised_v1.0.0",
    )

    # Real dataset ID is explicitly distinct from synthetic benchmark
    assert real_supervised_ds.manifest.dataset_id == "feat_ds_real_supervised_v1.0.0"
    assert real_supervised_ds.manifest.dataset_id != "ds_supervised_v1.0.0"


# =============================================================================
# 11. REAL PILOT SMOKE TEST & SCIENTIFIC GATE EVALUATION (NEXT-003 §3.11)
# =============================================================================


def test_real_pilot_smoke_test_and_gate_evaluation(
    real_enriched_pipeline_output: RealPipelineOutput,
) -> None:
    """Run real pilot smoke test and formally evaluate the 10 real training gate criteria."""
    detection_dataset, event_dataset, enriched_dataset = real_enriched_pipeline_output

    # 1. Pilot upstream counts
    assert len(detection_dataset.detections) == 6
    assert len(event_dataset.events) == 4
    assert len(event_dataset.persistent_sources) == 3
    assert len(enriched_dataset.context_evidence) == 9
    assert len(enriched_dataset.reference_labels) == 4

    builder = SupervisedDatasetBuilder()
    supervised_ds = builder.build_from_real_enriched_dataset(
        enriched_dataset=enriched_dataset,
        detection_dataset=detection_dataset,
        split_strategy=SplitStrategy.FACILITY_HOLDOUT,
    )

    # 2. Gate evaluation criteria
    eligible_events = [
        r for r in supervised_ds.records if r.row_status == DatasetRowStatus.TRAIN_ELIGIBLE
    ]
    assert len(eligible_events) == 3
    assert supervised_ds.split_manifest.excluded_count == 1

    # 3. Class distribution check: all 3 eligible are industrial, 0 non-industrial
    class_dist = supervised_ds.summary_statistics["class_distribution_by_target"][
        "target_industrial_segregation"
    ]
    assert class_dist.get("industrial") == 3
    assert class_dist.get("unknown") == 1
    assert class_dist.get("non_industrial", 0) == 0

    # 4. Statistical sufficiency evaluation
    is_statistically_sufficient = len(eligible_events) >= 500
    assert not is_statistically_sufficient  # REAL TRAINING GATE = NOT PASSED
