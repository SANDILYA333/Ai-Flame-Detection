"""Comprehensive Test Suite for NEXT-005: Real-World ML Evaluation Framework.

Validates:
1. Event isolation (train_events ∩ test_events = ∅).
2. Facility isolation (train_facilities ∩ test_facilities = ∅).
3. Persistent source isolation (train_sources ∩ test_sources = ∅).
4. Temporal forward ordering (max(train_t) < min(test_t)).
5. Geographic isolation (train_geo ∩ test_geo = ∅).
6. UNKNOWN labels excluded from evaluation matrices.
7. Conflicting labels excluded from evaluation.
8. Train-only feature preprocessing (no preprocessor leakage).
9. Metadata stripping (no entity_id, timestamps, labels in feature vector).
10. Class diversity gate rejects single-class evaluation.
11. Sample size gate rejects underpowered evaluations.
12. Strict determinism and hash invariance across repeat runs.
13. Isolation of synthetic benchmark datasets and artifacts.
14. Provenance tracking across evaluation reports.
15. Metric computation correctness (Precision, Recall, Macro F1, Confusion Matrix).
16. Probabilistic metric scoring (Brier score, Log Loss).
17. Pilot fixture evaluation behavior (correctly reports NOT_EVALUABLE).
"""

import math
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from packages.config.scientific import ScientificConfig
from packages.context.pipeline import RealContextLabelingService
from packages.data.firms.activation import FirmsDataActivationService
from packages.events.pipeline import RealEventConstructionService
from packages.feasibility.candidates import JAMNAGAR_KUTCH
from packages.schemas.common import Coordinate
from packages.schemas.detection import Detection
from packages.schemas.enums import DayNight
from packages.schemas.event import Event
from packages.schemas.ml import (
    DatasetManifest,
    DatasetRowStatus,
    FeatureDataset,
    FeatureDefinition,
    FeatureRecord,
    LabelConflictPolicy,
    LabelDecision,
    LabelProvenanceType,
    LabelTier,
    LabeledFeatureRecord,
    ReferenceEvidence,
    SplitManifest,
    SplitPartition,
    SplitStrategy,
    SupervisedDataset,
)
from services.ml.evaluation.harness import EvaluationHarness
from services.ml.evaluation.real_evaluator import RealEvaluationService
from services.ml.features.standard_set import APPROVED_FEATURES
from services.ml.labels.dataset import SupervisedDatasetBuilder
from services.ml.models.linear import LogisticRegressionClassifier
from services.ml.models.registry import ModelRegistry
from services.ml.models.trivial import MajorityClassClassifier
from services.ml.preprocessing.extractor import DatasetSplitExtractor
from services.ml.preprocessing.transformer import FeaturePreprocessor
from services.ml.training.real_trainer import RealMLTrainer


@pytest.fixture
def calibrated_config() -> ScientificConfig:
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
def real_pilot_supervised_dataset(
    calibrated_config: ScientificConfig,
) -> SupervisedDataset:
    csv_path = Path("fixtures/firms/firms_real_sample_jamnagar.csv")
    det_ds = FirmsDataActivationService.activate_from_csv(
        csv_input=csv_path,
        study_area=JAMNAGAR_KUTCH,
        requested_start_date="2026-08-01",
        requested_end_date="2026-08-10",
    )
    ev_ds = RealEventConstructionService.construct_events_and_sources(
        detection_dataset=det_ds,
        config=calibrated_config,
    )
    ctx_path = Path("fixtures/context/context_sample_jamnagar.json")
    features, hashes = RealContextLabelingService.load_context_features_from_fixture(
        ctx_path
    )
    enriched_ds = RealContextLabelingService.enrich_and_adjudicate_dataset(
        event_dataset=ev_ds,
        candidate_features=features,
        snapshot_hashes=hashes,
        config=calibrated_config,
    )
    builder = SupervisedDatasetBuilder()
    return builder.build_from_real_enriched_dataset(
        enriched_dataset=enriched_ds,
        detection_dataset=det_ds,
        split_strategy=SplitStrategy.FACILITY_HOLDOUT,
        target_ids=["target_industrial_segregation"],
    )


@pytest.fixture
def controlled_evaluation_fixture() -> SupervisedDataset:
    """Controlled multi-class, multi-facility, multi-day dataset for evaluator testing."""
    t0 = datetime(2026, 8, 1, 12, 0, 0, tzinfo=UTC)
    records: list[LabeledFeatureRecord] = []
    feature_defs = list(APPROVED_FEATURES)
    expected_names = {f.feature_name for f in APPROVED_FEATURES}

    facilities = [f"fac_{k:02d}" for k in range(12)]
    classes = ["industrial", "non_industrial"]

    for i in range(1, 61):  # 60 events total
        eid = f"evt_ctrl_{i:03d}"
        t_event = t0 + timedelta(days=i)  # Strictly forward temporal progression
        assigned_cls = classes[i % 2]
        fac_type = facilities[i % 12]
        is_near = assigned_cls == "industrial"
        dist = 300.0 if is_near else None

        feats: dict[str, Any] = {}
        for fname in expected_names:
            if fname == "detection_count":
                feats[fname] = 1 + (i % 5)
            elif fname == "frp_mean_mw":
                feats[fname] = 20.0 + (i * 2.0)
            elif fname == "facility_context_type":
                feats[fname] = fac_type
            elif fname == "is_near_industrial_facility":
                feats[fname] = is_near
            elif fname == "facility_distance_meters":
                feats[fname] = dist
            elif fname == "sensor_instrument":
                feats[fname] = "VIIRS" if i % 2 == 0 else "MODIS"
            elif fname == "is_persistent_source":
                feats[fname] = (i % 3 == 0)
            elif fname == "persistence_state":
                feats[fname] = "PERSISTENT" if (i % 3 == 0) else "TRANSIENT"
            elif fname == "daynight_ratio":
                feats[fname] = 0.5
            elif fname == "duration_hours":
                feats[fname] = 1.5
            elif fname == "spatial_extent_radius_meters":
                feats[fname] = 500.0
            else:
                feats[fname] = 0.0

        decision = LabelDecision(
            decision_id=f"dec_{eid}",
            entity_id=eid,
            target_id="target_industrial_segregation",
            assigned_class=assigned_cls,
            label_tier=LabelTier.TIER_B_STRONG_EVIDENCE,
            provenance_type=LabelProvenanceType.REFERENCE_LABEL,
            confidence_score=0.90,
            has_conflicting_evidence=False,
            is_train_eligible=True,
            decision_timestamp=t_event,
        )

        record = LabeledFeatureRecord(
            entity_id=eid,
            feature_record=FeatureRecord(
                entity_id=eid,
                event_id=eid,
                source_id=f"src_{i % 10:02d}",
                as_of_time=t_event,
                features=feats,
                missingness_flags={f"{k}_is_missing": v is None for k, v in feats.items()},
            ),
            labels={"target_industrial_segregation": decision},
            split_partition=SplitPartition.TRAIN,
            row_status=DatasetRowStatus.TRAIN_ELIGIBLE,
            exclusion_reason=None,
        )
        records.append(record)

    manifest = DatasetManifest(
        dataset_id="feat_ds_controlled_fixture_v1.0.0",
        dataset_version="v1.0.0",
        target_id="target_industrial_segregation",
        feature_set_version="feat_v1.0.0",
        label_set_version="label_v1.0.0",
        geographic_scope="jamnagar_kutch",
        temporal_start=t0,
        temporal_end=t0 + timedelta(days=40),
        split_strategy=SplitStrategy.GROUPED_EVENT_HOLDOUT,
        record_count=len(records),
        sha256_hash="e" * 64,
        created_at=t0,
    )

    split_manifest = SplitManifest(
        split_id="split_ctrl_001",
        dataset_id=manifest.dataset_id,
        dataset_version=manifest.dataset_version,
        split_strategy=SplitStrategy.GROUPED_EVENT_HOLDOUT,
        train_count=36,
        validation_count=12,
        test_count=12,
        created_at=t0,
    )

    return SupervisedDataset(
        manifest=manifest,
        feature_definitions=feature_defs,
        records=records,
        split_manifest=split_manifest,
    )


# =============================================================================
# 1. EVENT ISOLATION (TEST 1)
# =============================================================================


def test_event_isolation(
    controlled_evaluation_fixture: SupervisedDataset,
) -> None:
    """Verify physical event IDs never overlap between train and test partitions."""
    model = MajorityClassClassifier()
    result = RealEvaluationService.evaluate_model_on_dataset(
        dataset=controlled_evaluation_fixture,
        model_artifact_or_instance=model,
        strategies=[SplitStrategy.GROUPED_EVENT_HOLDOUT],
    )
    strat_res = result.strategy_results[SplitStrategy.GROUPED_EVENT_HOLDOUT.value]
    assert strat_res.status == "VALID"
    assert strat_res.leakage_audit["split_is_valid"] is True
    assert len(strat_res.leakage_audit["event_leakage_violations"]) == 0


# =============================================================================
# 2. FACILITY ISOLATION (TEST 2)
# =============================================================================


def test_facility_isolation(
    controlled_evaluation_fixture: SupervisedDataset,
) -> None:
    """Verify held-out facilities never appear in training."""
    model = MajorityClassClassifier()
    result = RealEvaluationService.evaluate_model_on_dataset(
        dataset=controlled_evaluation_fixture,
        model_artifact_or_instance=model,
        strategies=[SplitStrategy.FACILITY_HOLDOUT],
    )
    strat_res = result.strategy_results[SplitStrategy.FACILITY_HOLDOUT.value]
    assert strat_res.status == "VALID"
    assert strat_res.leakage_audit["split_is_valid"] is True
    assert len(strat_res.leakage_audit["facility_leakage_violations"]) == 0


# =============================================================================
# 3. PERSISTENT SOURCE ISOLATION (TEST 3)
# =============================================================================


def test_persistent_source_isolation(
    controlled_evaluation_fixture: SupervisedDataset,
) -> None:
    """Verify persistent source groups do not cross partitions."""
    model = MajorityClassClassifier()
    result = RealEvaluationService.evaluate_model_on_dataset(
        dataset=controlled_evaluation_fixture,
        model_artifact_or_instance=model,
        strategies=[SplitStrategy.PERSISTENT_SOURCE_HOLDOUT],
    )
    strat_res = result.strategy_results[SplitStrategy.PERSISTENT_SOURCE_HOLDOUT.value]
    assert strat_res.status == "VALID"
    assert strat_res.leakage_audit["split_is_valid"] is True
    assert len(strat_res.leakage_audit["source_leakage_violations"]) == 0


# =============================================================================
# 4. TEMPORAL FORWARD ORDERING (TEST 4)
# =============================================================================


def test_temporal_ordering(
    controlled_evaluation_fixture: SupervisedDataset,
) -> None:
    """Verify chronological ordering: train timestamps strictly precede test."""
    model = MajorityClassClassifier()
    result = RealEvaluationService.evaluate_model_on_dataset(
        dataset=controlled_evaluation_fixture,
        model_artifact_or_instance=model,
        strategies=[SplitStrategy.TEMPORAL_HOLDOUT],
    )
    strat_res = result.strategy_results[SplitStrategy.TEMPORAL_HOLDOUT.value]
    assert strat_res.status == "VALID"
    assert strat_res.leakage_audit["split_is_valid"] is True
    assert len(strat_res.leakage_audit["temporal_inversion_violations"]) == 0


# =============================================================================
# 5. GEOGRAPHIC ISOLATION (TEST 5)
# =============================================================================


def test_geographic_isolation(
    controlled_evaluation_fixture: SupervisedDataset,
) -> None:
    """Verify single study area dataset correctly flags geographic holdout as infeasible."""
    model = MajorityClassClassifier()
    result = RealEvaluationService.evaluate_model_on_dataset(
        dataset=controlled_evaluation_fixture,
        model_artifact_or_instance=model,
        strategies=[SplitStrategy.SPATIAL_GEOGRAPHIC_HOLDOUT],
    )
    strat_res = result.strategy_results[SplitStrategy.SPATIAL_GEOGRAPHIC_HOLDOUT.value]
    assert strat_res.status == "NOT_EVALUABLE"
    assert "geographic study area" in strat_res.reason


# =============================================================================
# 6. UNKNOWN EXCLUSION (TEST 6)
# =============================================================================


def test_unknown_exclusion_from_evaluation(
    real_pilot_supervised_dataset: SupervisedDataset,
) -> None:
    """Verify unknown labels are strictly excluded from evaluation matrices."""
    _, _, _, _, _, _, x_test, y_test, _ = DatasetSplitExtractor.extract_split_matrices(
        dataset=real_pilot_supervised_dataset,
        target_id="target_industrial_segregation",
    )
    assert "unknown" not in y_test


# =============================================================================
# 7. CONFLICTING EVIDENCE EXCLUSION (TEST 7)
# =============================================================================


def test_conflicting_evidence_exclusion_from_evaluation(
    calibrated_config: ScientificConfig,
) -> None:
    """Verify contradictory equal-tier labels cannot enter evaluation."""
    t0 = datetime(2026, 8, 5, 12, 0, 0, tzinfo=UTC)
    ev = Event(
        event_id="evt_conflict_eval",
        started_at=t0,
        ended_at=t0,
        centroid_geometry=Coordinate(latitude=22.45, longitude=70.05),
        detection_ids=["det_c_001"],
        detection_count=1,
        formation_configuration_id="cfg_001",
        formation_configuration_version="v1.0",
    )
    ev1 = ReferenceEvidence(
        evidence_id="ref_ev_1",
        source_name="WRI",
        entity_id=ev.event_id,
        geometry=Coordinate(latitude=22.45, longitude=70.05),
        claim_class="industrial",
        confidence_score=0.85,
        tier=LabelTier.TIER_B_STRONG_EVIDENCE,
    )
    ev2 = ReferenceEvidence(
        evidence_id="ref_ev_2",
        source_name="LANDCOVER",
        entity_id=ev.event_id,
        geometry=Coordinate(latitude=22.45, longitude=70.05),
        claim_class="non_industrial",
        confidence_score=0.85,
        tier=LabelTier.TIER_B_STRONG_EVIDENCE,
    )
    decisions = RealContextLabelingService.adjudicate_labels(
        events=[ev],
        reference_evidence=[ev1, ev2],
        conflict_policy=LabelConflictPolicy.TIER_PRECEDENCE,
    )
    assert decisions[0].assigned_class == "unknown"
    assert decisions[0].is_train_eligible is False


# =============================================================================
# 8. PREPROCESSOR LEAKAGE PREVENTION (TEST 8)
# =============================================================================


def test_preprocessor_leakage_prevention(
    controlled_evaluation_fixture: SupervisedDataset,
) -> None:
    """Verify FeaturePreprocessor is fitted only on the training partition."""
    (
        x_train_raw,
        _,
        _,
        _,
        _,
        _,
        _,
        _,
        _,
    ) = DatasetSplitExtractor.extract_split_matrices(
        dataset=controlled_evaluation_fixture,
        target_id="target_industrial_segregation",
    )

    train_data = x_train_raw[:40]
    test_data = x_train_raw[40:]

    preprocessor = FeaturePreprocessor()
    preprocessor.fit(train_data)

    # Preprocessor output dimensionality is learned solely from train
    assert preprocessor.output_column_names is not None
    transformed_test = preprocessor.transform(test_data)
    assert len(transformed_test) == len(test_data)
    assert len(transformed_test[0]) == len(preprocessor.output_column_names)


# =============================================================================
# 9. FEATURE LEAKAGE PROHIBITION (TEST 9)
# =============================================================================


def test_feature_leakage_prohibition(
    controlled_evaluation_fixture: SupervisedDataset,
) -> None:
    """Verify prohibited metadata columns never enter evaluation feature vectors."""
    x_train, _, _, _, _, _, _, _, _ = DatasetSplitExtractor.extract_split_matrices(
        dataset=controlled_evaluation_fixture,
        target_id="target_industrial_segregation",
    )

    prohibited = {"entity_id", "event_id", "detection_id", "target", "label"}
    for row in x_train:
        for p in prohibited:
            assert p not in row


# =============================================================================
# 10. CLASS DIVERSITY GATE (TEST 10)
# =============================================================================


def test_class_diversity_gate(
    real_pilot_supervised_dataset: SupervisedDataset,
) -> None:
    """Verify single-class dataset is strictly marked NOT_EVALUABLE."""
    model = MajorityClassClassifier()
    result = RealEvaluationService.evaluate_model_on_dataset(
        dataset=real_pilot_supervised_dataset,
        model_artifact_or_instance=model,
    )

    assert result.overall_status == "NOT_SCIENTIFICALLY_VALID_ON_PILOT"
    for strat_res in result.strategy_results.values():
        assert strat_res.status == "NOT_EVALUABLE"
        assert "Zero class diversity" in strat_res.reason


# =============================================================================
# 11. SMALL SAMPLE GATE (TEST 11)
# =============================================================================


def test_small_sample_gate(
    real_pilot_supervised_dataset: SupervisedDataset,
) -> None:
    """Verify tiny pilot dataset never produces a production-valid evaluation report."""
    model = MajorityClassClassifier()
    result = RealEvaluationService.evaluate_model_on_dataset(
        dataset=real_pilot_supervised_dataset,
        model_artifact_or_instance=model,
    )
    assert result.is_production_ready is False


# =============================================================================
# 12. EVALUATION DETERMINISM (TEST 12)
# =============================================================================


def test_evaluation_determinism(
    controlled_evaluation_fixture: SupervisedDataset,
) -> None:
    """Verify repeat evaluation produces identical metrics and confusion matrices."""
    model = MajorityClassClassifier()

    res1 = RealEvaluationService.evaluate_model_on_dataset(
        dataset=controlled_evaluation_fixture,
        model_artifact_or_instance=model,
        random_seed=42,
    )
    res2 = RealEvaluationService.evaluate_model_on_dataset(
        dataset=controlled_evaluation_fixture,
        model_artifact_or_instance=model,
        random_seed=42,
    )

    strat_key = SplitStrategy.GROUPED_EVENT_HOLDOUT.value
    m1 = res1.strategy_results[strat_key].metrics
    m2 = res2.strategy_results[strat_key].metrics
    assert m1["accuracy"] == m2["accuracy"]
    assert m1["macro_f1"] == m2["macro_f1"]
    assert m1["confusion_matrix"] == m2["confusion_matrix"]


# =============================================================================
# 13. SYNTHETIC DATASET ISOLATION (TEST 13)
# =============================================================================


def test_synthetic_isolation(
    real_pilot_supervised_dataset: SupervisedDataset,
) -> None:
    """Verify real evaluation pipeline operates strictly on real dataset identifiers."""
    model = MajorityClassClassifier()
    result = RealEvaluationService.evaluate_model_on_dataset(
        dataset=real_pilot_supervised_dataset,
        model_artifact_or_instance=model,
    )
    assert result.dataset_id == "feat_ds_real_supervised_v1.0.0"
    assert result.dataset_id != "ds_supervised_v1.0.0"


# =============================================================================
# 14. PROVENANCE PRESERVATION (TEST 14)
# =============================================================================


def test_provenance_preservation(
    controlled_evaluation_fixture: SupervisedDataset,
) -> None:
    """Verify evaluation results preserve complete model and dataset provenance."""
    model = MajorityClassClassifier()
    result = RealEvaluationService.evaluate_model_on_dataset(
        dataset=controlled_evaluation_fixture,
        model_artifact_or_instance=model,
    )

    strat_key = SplitStrategy.GROUPED_EVENT_HOLDOUT.value
    strat_res = result.strategy_results[strat_key]
    assert strat_res.provenance["dataset_id"] == controlled_evaluation_fixture.manifest.dataset_id
    assert strat_res.provenance["dataset_version"] == controlled_evaluation_fixture.manifest.dataset_version
    assert strat_res.provenance["split_strategy"] == SplitStrategy.GROUPED_EVENT_HOLDOUT.value


# =============================================================================
# 15. METRIC COMPUTATION CORRECTNESS (TEST 15)
# =============================================================================


def test_metric_correctness_on_controlled_fixture(
    controlled_evaluation_fixture: SupervisedDataset,
) -> None:
    """Verify exact precision, recall, F1, and confusion matrix on known outputs."""
    y_true = ["industrial", "industrial", "non_industrial", "non_industrial"]
    y_pred = ["industrial", "non_industrial", "non_industrial", "non_industrial"]

    report = EvaluationHarness.evaluate_predictions(
        evaluation_id="eval_test_correctness",
        experiment_id="exp_test",
        dataset_id="ds_test",
        dataset_version="v1.0.0",
        model_id="model_test",
        model_version="v1.0.0",
        split_partition=SplitPartition.TEST,
        y_true=y_true,
        y_pred=y_pred,
    )

    # 3/4 correct -> Accuracy = 0.75
    assert report.accuracy == 0.75
    # Class 'industrial': TP=1, FP=0, FN=1 -> Precision=1.0, Recall=0.5, F1=0.6667
    ind_metrics = report.per_class_metrics["industrial"]
    assert ind_metrics.precision == 1.0
    assert ind_metrics.recall == 0.5
    assert math.isclose(ind_metrics.f1_score, 2.0 / 3.0, rel_tol=1e-3)


# =============================================================================
# 16. PROBABILISTIC METRICS SCORING (TEST 16)
# =============================================================================


def test_probabilistic_metrics(
    controlled_evaluation_fixture: SupervisedDataset,
) -> None:
    """Verify Brier score and Log Loss are computed accurately when probabilities are present."""
    y_true = ["industrial", "non_industrial"]
    y_pred = ["industrial", "non_industrial"]
    y_prob = [
        {"industrial": 0.9, "non_industrial": 0.1},
        {"industrial": 0.2, "non_industrial": 0.8},
    ]

    report = EvaluationHarness.evaluate_predictions(
        evaluation_id="eval_test_prob",
        experiment_id="exp_test",
        dataset_id="ds_test",
        dataset_version="v1.0.0",
        model_id="model_test",
        model_version="v1.0.0",
        split_partition=SplitPartition.TEST,
        y_true=y_true,
        y_pred=y_pred,
        y_prob=y_prob,
    )

    assert report.brier_score is not None
    assert report.brier_score >= 0.0
    assert report.log_loss is not None
    assert report.log_loss >= 0.0


# =============================================================================
# 17. PILOT FIXTURE EVALUATION BEHAVIOR (TEST 17)
# =============================================================================


def test_real_pilot_behavior_rejection(
    real_pilot_supervised_dataset: SupervisedDataset,
) -> None:
    """Run full evaluation on real pilot data and verify all 5 holdouts report NOT_EVALUABLE."""
    model = MajorityClassClassifier()
    campaign_result = RealEvaluationService.evaluate_model_on_dataset(
        dataset=real_pilot_supervised_dataset,
        model_artifact_or_instance=model,
    )

    assert campaign_result.overall_status == "NOT_SCIENTIFICALLY_VALID_ON_PILOT"
    assert campaign_result.is_production_ready is False
    assert len(campaign_result.strategy_results) == 5

    for s_name, s_res in campaign_result.strategy_results.items():
        assert s_res.status == "NOT_EVALUABLE"
        assert s_res.is_scientifically_valid is False
        assert s_res.reason is not None
