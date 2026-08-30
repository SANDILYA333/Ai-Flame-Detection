"""Tests for canonical DATASET-002: Supervised Dataset Assembly on Real Data."""

from pathlib import Path

import pytest

from packages.config.scientific import ScientificConfig
from packages.context.pipeline import RealContextLabelingService
from packages.data.firms.activation import FirmsDataActivationService
from packages.data.firms.schemas import RealDetectionDataset
from packages.events.pipeline import RealEventConstructionService
from packages.feasibility.candidates import JAMNAGAR_KUTCH
from packages.schemas.event import RealEnrichedEventDataset, RealThermalEventDataset
from packages.schemas.ml import (
    DatasetRowStatus,
    ExclusionReason,
    SplitPartition,
    SplitStrategy,
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


def test_dataset_002_real_supervised_dataset_assembly(
    real_enriched_pipeline_output: RealPipelineOutput,
) -> None:
    """Verify DATASET-002 bridges real enriched events with 30 features."""
    detection_dataset, _, enriched_dataset = real_enriched_pipeline_output

    builder = SupervisedDatasetBuilder()
    supervised_ds = builder.build_from_real_enriched_dataset(
        enriched_dataset=enriched_dataset,
        detection_dataset=detection_dataset,
        split_strategy=SplitStrategy.FACILITY_HOLDOUT,
        target_ids=["target_industrial_segregation"],
    )

    # 1. Total event records check
    assert len(supervised_ds.records) == 4

    # 2. Exactly 30 canonical features present
    assert len(supervised_ds.feature_definitions) == 30

    # 3. Verify feature values on real records
    for rec in supervised_ds.records:
        feat_dict = rec.feature_record.features
        assert "detection_count" in feat_dict
        assert "frp_mean_mw" in feat_dict
        assert "duration_hours" in feat_dict
        assert "brightness_mean_kelvin" in feat_dict
        assert "spatial_extent_radius_meters" in feat_dict
        assert "facility_distance_meters" in feat_dict

    # 4. Reference labels attached correctly
    train_eligible_count = 0
    excluded_count = 0
    valid_partitions = (
        SplitPartition.TRAIN,
        SplitPartition.VALIDATION,
        SplitPartition.TEST,
    )
    for rec in supervised_ds.records:
        lbl = rec.labels.get("target_industrial_segregation")
        assert lbl is not None
        if lbl.is_train_eligible:
            train_eligible_count += 1
            assert rec.exclusion_reason is None
            assert rec.row_status == DatasetRowStatus.TRAIN_ELIGIBLE
            assert rec.split_partition in valid_partitions
        else:
            excluded_count += 1
            assert (
                rec.exclusion_reason
                == ExclusionReason.INSUFFICIENT_LABEL_EVIDENCE
            )
            assert rec.row_status == DatasetRowStatus.EXCLUDED

    assert train_eligible_count == 3
    assert excluded_count == 1


def test_dataset_002_missing_not_negative_enforcement(
    real_enriched_pipeline_output: RealPipelineOutput,
) -> None:
    """Verify unknown context events are excluded and never treated negative."""
    detection_dataset, _, enriched_dataset = real_enriched_pipeline_output

    builder = SupervisedDatasetBuilder()
    supervised_ds = builder.build_from_real_enriched_dataset(
        enriched_dataset=enriched_dataset,
        detection_dataset=detection_dataset,
        split_strategy=SplitStrategy.GROUPED_EVENT_HOLDOUT,
    )

    # Find the isolated event (>50km from facilities)
    unknown_records = [
        r
        for r in supervised_ds.records
        if r.labels["target_industrial_segregation"].assigned_class == "unknown"
    ]
    assert len(unknown_records) == 1
    rec = unknown_records[0]

    # Must be excluded from training partition
    assert rec.row_status == DatasetRowStatus.EXCLUDED
    assert rec.exclusion_reason == ExclusionReason.INSUFFICIENT_LABEL_EVIDENCE
    assert rec.labels["target_industrial_segregation"].is_train_eligible is False


def test_dataset_002_reproducibility_and_hashing(
    real_enriched_pipeline_output: RealPipelineOutput,
) -> None:
    """Verify dataset creation is 100% deterministic with matching hashes."""
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
