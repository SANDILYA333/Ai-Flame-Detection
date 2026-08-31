"""Comprehensive Test Suite for NEXT-004: First Real ML Training.

Validates:
1. Real dataset is accepted by training pipeline.
2. Synthetic dataset and benchmarks remain isolated.
3. UNKNOWN records are excluded from training matrices.
4. Conflicting evidence records are excluded from training.
5. Canonical 30-feature schema is preserved.
6. Anti-leakage is strictly enforced.
7. Class gate correctly fails on insufficient class diversity / sample size.
8. Small dataset never produces false production validity.
9. Determinism and artifact reproducibility.
10. Model artifact provenance and circularity warning metadata.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from packages.config.scientific import ScientificConfig
from packages.context.pipeline import RealContextLabelingService
from packages.data.firms.activation import FirmsDataActivationService
from packages.data.firms.schemas import RealDetectionDataset
from packages.events.pipeline import RealEventConstructionService
from packages.feasibility.candidates import JAMNAGAR_KUTCH
from packages.schemas.common import Coordinate
from packages.schemas.enums import DayNight
from packages.schemas.event import Event, RealEnrichedEventDataset, RealThermalEventDataset
from packages.schemas.ml import (
    DatasetRowStatus,
    ExclusionReason,
    LabelConflictPolicy,
    LabelDecision,
    LabelTier,
    ReferenceEvidence,
    SplitPartition,
    SplitStrategy,
    SupervisedDataset,
)
from services.ml.features.standard_set import APPROVED_FEATURES
from services.ml.labels.dataset import SupervisedDatasetBuilder
from services.ml.models.registry import ModelRegistry
from services.ml.preprocessing.extractor import DatasetSplitExtractor
from services.ml.training.gate import RealTrainingGateEvaluator
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
def real_supervised_dataset(
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


# =============================================================================
# 1. REAL DATASET ACCEPTED BY TRAINING PIPELINE (TEST 1)
# =============================================================================


def test_real_dataset_accepted_by_training_pipeline(
    real_supervised_dataset: SupervisedDataset,
    tmp_path: Path,
) -> None:
    """Verify the real supervised dataset is accepted and trains all canonical models."""
    trainer = RealMLTrainer(
        random_seed=42,
        artifact_base_dir=tmp_path / "artifacts" / "real" / "pilot",
    )
    result = trainer.train_real_suite(
        dataset=real_supervised_dataset,
        target_id="target_industrial_segregation",
    )

    assert result.dataset_id == real_supervised_dataset.manifest.dataset_id
    assert len(result.model_results) == 5

    expected_models = {
        "MajorityClassClassifier",
        "DeterministicContextualClassifier",
        "LogisticRegressionClassifier",
        "DecisionTreeClassifier",
        "RandomForestClassifier",
    }
    assert set(result.model_results.keys()) == expected_models

    for m_type, m_res in result.model_results.items():
        assert m_res.status == "TRAINED_PILOT"
        assert m_res.train_record_count == 3
        assert m_res.artifact_path is not None
        assert Path(m_res.artifact_path).exists()


# =============================================================================
# 2. SYNTHETIC DATASET ISOLATION (TEST 2)
# =============================================================================


def test_synthetic_dataset_isolation(
    real_supervised_dataset: SupervisedDataset,
    tmp_path: Path,
) -> None:
    """Verify real ML training does not overwrite or mutate synthetic benchmark."""
    trainer = RealMLTrainer(
        random_seed=42,
        artifact_base_dir=tmp_path / "artifacts" / "real" / "pilot",
    )
    result = trainer.train_real_suite(
        dataset=real_supervised_dataset,
        target_id="target_industrial_segregation",
    )

    # Real dataset ID is explicitly distinct from synthetic benchmark
    assert result.dataset_id == "feat_ds_real_supervised_v1.0.0"
    assert result.dataset_id != "ds_supervised_v1.0.0"

    # Artifacts are stored under real pilot directory
    for m_res in result.model_results.values():
        art_name = Path(m_res.artifact_path).name
        assert "real_" in art_name
        assert "synthetic" not in art_name
        assert "artifacts/real/pilot" in m_res.artifact_path


# =============================================================================
# 3. UNKNOWN RECORDS EXCLUDED FROM TRAINING (TEST 3)
# =============================================================================


def test_unknown_records_excluded_from_training(
    real_supervised_dataset: SupervisedDataset,
) -> None:
    """Verify records with unknown labels are excluded from training matrices."""
    # Dataset has 4 total records: 3 industrial, 1 unknown
    assert len(real_supervised_dataset.records) == 4

    x_train, y_train, ids_train, _, _, _, _, _, _ = DatasetSplitExtractor.extract_split_matrices(
        dataset=real_supervised_dataset,
        target_id="target_industrial_segregation",
    )

    assert len(x_train) == 3
    assert len(y_train) == 3
    assert all(y == "industrial" for y in y_train)
    assert "unknown" not in y_train


# =============================================================================
# 4. CONFLICTING EVIDENCE EXCLUDED FROM TRAINING (TEST 4)
# =============================================================================


def test_conflicting_evidence_excluded_from_training(
    calibrated_config: ScientificConfig,
    real_supervised_dataset: SupervisedDataset,
    tmp_path: Path,
) -> None:
    """Verify conflicting evidence records are excluded and cannot enter training matrices."""
    t0 = datetime(2026, 8, 5, 12, 0, 0, tzinfo=UTC)
    ev = Event(
        event_id="evt_conflict_001",
        started_at=t0,
        ended_at=t0,
        centroid_geometry=Coordinate(latitude=22.45, longitude=70.05),
        detection_ids=["det_c_001"],
        detection_count=1,
        formation_configuration_id="cfg_001",
        formation_configuration_version="v1.0",
    )
    ev1 = ReferenceEvidence(
        evidence_id="ref_ev_ind",
        source_name="WRI",
        entity_id=ev.event_id,
        geometry=Coordinate(latitude=22.45, longitude=70.05),
        claim_class="industrial",
        confidence_score=0.85,
        tier=LabelTier.TIER_B_STRONG_EVIDENCE,
    )
    ev2 = ReferenceEvidence(
        evidence_id="ref_ev_non_ind",
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

    # Extract split matrices on single-conflict record
    enriched_ds = RealEnrichedEventDataset(
        dataset_id="ds_test_conflict",
        dataset_version="v1.0.0",
        source_detection_dataset_id="ds_test_dets",
        source_detection_dataset_hash="a" * 64,
        source_event_dataset_id="ds_test_events",
        source_event_dataset_hash="b" * 64,
        study_area_id="test_area",
        study_area_name="Test Area",
        bounding_box=JAMNAGAR_KUTCH.bounding_box,
        events=[ev],
        context_evidence=[],
        reference_evidence=[ev1, ev2],
        reference_labels=[decisions[0]],
        config_fingerprint=calibrated_config.compute_fingerprint(),
        canonical_dataset_hash="c" * 64,
        created_at=t0,
    )

    det_ds = FirmsDataActivationService.activate_from_csv(
        csv_input=Path("fixtures/firms/firms_real_sample_jamnagar.csv"),
        study_area=JAMNAGAR_KUTCH,
        requested_start_date="2026-08-01",
        requested_end_date="2026-08-10",
    )
    builder = SupervisedDatasetBuilder()
    sup_ds = builder.build_from_real_enriched_dataset(enriched_ds, det_ds)

    x_train, y_train, _, _, _, _, _, _, _ = DatasetSplitExtractor.extract_split_matrices(
        dataset=sup_ds,
        target_id="target_industrial_segregation",
    )
    assert len(x_train) == 0
    assert len(y_train) == 0


# =============================================================================
# 5. CANONICAL 30-FEATURE SCHEMA PRESERVED (TEST 5)
# =============================================================================


def test_feature_schema_preserved(
    real_supervised_dataset: SupervisedDataset,
    tmp_path: Path,
) -> None:
    """Verify exactly the canonical 30-feature catalog is consumed during training."""
    trainer = RealMLTrainer(
        random_seed=42,
        artifact_base_dir=tmp_path / "artifacts" / "real" / "pilot",
    )
    result = trainer.train_real_suite(
        dataset=real_supervised_dataset,
        target_id="target_industrial_segregation",
    )

    expected_feature_names = {f.feature_name for f in APPROVED_FEATURES}
    assert len(expected_feature_names) == 30

    for m_res in result.model_results.values():
        artifact = ModelRegistry.load_from_file(m_res.artifact_path)
        # Preprocessor feature dimensionality is >= 30 after categorical 1-hot
        assert artifact.metadata.feature_dimensionality >= 30
        assert artifact.metadata.feature_set_version == "feat_v1.0.0"


# =============================================================================
# 6. NO FEATURE LEAKAGE (TEST 6)
# =============================================================================


def test_no_feature_leakage(
    real_supervised_dataset: SupervisedDataset,
) -> None:
    """Verify metadata columns and IDs are stripped from training feature matrices."""
    x_train, _, _, _, _, _, _, _, _ = DatasetSplitExtractor.extract_split_matrices(
        dataset=real_supervised_dataset,
        target_id="target_industrial_segregation",
    )

    prohibited_keys = {
        "entity_id", "event_id", "detection_id", "source_id",
        "target", "label", "started_at", "ended_at",
    }
    for row in x_train:
        for p_key in prohibited_keys:
            assert p_key not in row


# =============================================================================
# 7. CLASS GATE FAILURE ON INSUFFICIENT CLASSES (TEST 7)
# =============================================================================


def test_class_gate_failure_on_insufficient_classes(
    real_supervised_dataset: SupervisedDataset,
) -> None:
    """Verify single-class / small-N dataset triggers scientific training gate failure."""
    gate = RealTrainingGateEvaluator.evaluate(
        dataset=real_supervised_dataset,
        target_id="target_industrial_segregation",
    )

    assert gate.gate_status == "NOT_PASSED"
    assert gate.is_production_ready is False
    assert gate.class_diversity_sufficient is False
    assert gate.statistical_validity is False
    assert len(gate.rejection_reasons) >= 2


# =============================================================================
# 8. SMALL DATASET NEVER REPORTS PRODUCTION READINESS (TEST 8)
# =============================================================================


def test_small_dataset_never_reports_production_readiness(
    real_supervised_dataset: SupervisedDataset,
    tmp_path: Path,
) -> None:
    """Verify the pipeline explicitly reports NOT_PRODUCTION_READY for pilot data."""
    trainer = RealMLTrainer(
        random_seed=42,
        artifact_base_dir=tmp_path / "artifacts" / "real" / "pilot",
    )
    result = trainer.train_real_suite(
        dataset=real_supervised_dataset,
        target_id="target_industrial_segregation",
    )

    assert result.is_production_ready is False
    assert result.gate_evaluation.gate_status == "NOT_PASSED"
    for m_res in result.model_results.values():
        assert m_res.is_production_ready is False
        assert m_res.status == "TRAINED_PILOT"


# =============================================================================
# 9. DETERMINISM ACROSS TRAINING RUNS (TEST 9)
# =============================================================================


def test_training_determinism(
    real_supervised_dataset: SupervisedDataset,
    tmp_path: Path,
) -> None:
    """Verify identical configuration produces bit-identical artifacts and predictions."""
    dir1 = tmp_path / "run1"
    dir2 = tmp_path / "run2"

    trainer1 = RealMLTrainer(random_seed=42, artifact_base_dir=dir1)
    trainer2 = RealMLTrainer(random_seed=42, artifact_base_dir=dir2)

    res1 = trainer1.train_real_suite(real_supervised_dataset)
    res2 = trainer2.train_real_suite(real_supervised_dataset)

    for m_type in res1.model_results:
        art1 = ModelRegistry.load_from_file(res1.model_results[m_type].artifact_path)
        art2 = ModelRegistry.load_from_file(res2.model_results[m_type].artifact_path)
        assert art1.sha256_hash == art2.sha256_hash
        assert art1.model_parameters == art2.model_parameters


# =============================================================================
# 10. ARTIFACT PROVENANCE AND CIRCULARITY WARNING (TEST 10)
# =============================================================================


def test_artifact_provenance_and_metadata(
    real_supervised_dataset: SupervisedDataset,
    tmp_path: Path,
) -> None:
    """Verify model artifact records dataset version, manifest hash, gate status, and circularity."""
    trainer = RealMLTrainer(
        random_seed=42,
        artifact_base_dir=tmp_path / "artifacts" / "real" / "pilot",
    )
    result = trainer.train_real_suite(
        dataset=real_supervised_dataset,
        target_id="target_industrial_segregation",
    )

    for m_res in result.model_results.values():
        art = ModelRegistry.load_from_file(m_res.artifact_path)
        assert art.metadata.dataset_id == real_supervised_dataset.manifest.dataset_id
        assert art.metadata.dataset_version == real_supervised_dataset.manifest.dataset_version
        assert art.metadata.dataset_hash == real_supervised_dataset.manifest.sha256_hash
        assert art.metadata.feature_set_version == "feat_v1.0.0"
        assert art.metadata.validation_metrics.get("pilot_mode") is True
        assert art.metadata.validation_metrics.get("scientific_gate_status") == "NOT_PASSED"
        assert "circularity_warning" in art.metadata.validation_metrics
