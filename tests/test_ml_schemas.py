"""Unit tests for Phase 4 ML domain schemas and enumerations."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.ml import (
    CalibrationContract,
    CalibrationMethod,
    DatasetManifest,
    FeatureDefinition,
    FeatureMissingnessHandling,
    FeatureType,
    LabelMetadata,
    LabelProvenanceType,
    LabelTier,
    LeakageRisk,
    SplitPartition,
    SplitStrategy,
    TargetDefinition,
    TargetType,
    TargetUnit,
)


class TestMLSchemas:
    """Test suite validating canonical ML domain models and constraints."""

    def test_target_definition_valid(self) -> None:
        """TargetDefinition instantiation and validation."""
        target = TargetDefinition(
            target_id="target_phenomenon_v1",
            name="Thermal Phenomenon Multiclass",
            target_type=TargetType.MULTICLASS_CLASSIFICATION,
            unit_of_prediction=TargetUnit.EVENT,
            class_vocabulary=["flare", "fire", "industrial_thermal_source", "unknown"],
            is_approved=False,
            unresolved_reason="Taxonomy awaiting scientific team review.",
        )
        assert target.target_id == "target_phenomenon_v1"
        assert target.is_approved is False
        assert len(target.class_vocabulary) == 4

    def test_label_metadata_ground_truth_property(self) -> None:
        """Only Tier A with GROUND_TRUTH provenance can be ground truth."""
        tier_a_label = LabelMetadata(
            label_id="lbl_001",
            target_id="target_phenomenon_v1",
            entity_id="evt_123",
            label_value="flare",
            label_tier=LabelTier.TIER_A_AUTHORITATIVE,
            provenance_type=LabelProvenanceType.GROUND_TRUTH,
            source_name="Refinery Ground Station Log",
            confidence_score=0.99,
        )
        assert tier_a_label.is_authoritative_ground_truth is True

        tier_c_label = LabelMetadata(
            label_id="lbl_002",
            target_id="target_phenomenon_v1",
            entity_id="evt_124",
            label_value="fire",
            label_tier=LabelTier.TIER_C_PROXY_WEAK,
            provenance_type=LabelProvenanceType.WEAK_LABEL,
            source_name="OSM Landuse Heuristic",
            confidence_score=0.60,
        )
        assert tier_c_label.is_authoritative_ground_truth is False

    def test_label_metadata_rejects_invalid_confidence(self) -> None:
        """Confidence score must be between 0.0 and 1.0."""
        with pytest.raises(ValidationError):
            LabelMetadata(
                label_id="lbl_003",
                target_id="target_phenomenon_v1",
                entity_id="evt_125",
                label_value="flare",
                label_tier=LabelTier.TIER_A_AUTHORITATIVE,
                provenance_type=LabelProvenanceType.GROUND_TRUTH,
                source_name="Test",
                confidence_score=1.5,  # Invalid
            )

    def test_feature_definition_valid(self) -> None:
        """FeatureDefinition creation and constraints."""
        feat = FeatureDefinition(
            feature_name="frp_mean_mw",
            feature_type=FeatureType.NUMERIC,
            source_entity="Event",
            derivation_description="Mean FRP in MW across event detections.",
            physical_unit="MW",
            availability_lag_seconds=300.0,
            missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
            allowed_for_training=True,
            leakage_risk=LeakageRisk.SAFE,
            version="v1.0",
        )
        assert feat.feature_name == "frp_mean_mw"
        assert feat.availability_lag_seconds == 300.0
        assert feat.leakage_risk == LeakageRisk.SAFE

    def test_dataset_manifest_temporal_validation(self) -> None:
        """DatasetManifest rejects temporal_start > temporal_end."""
        t_start = datetime(2025, 1, 1, tzinfo=UTC)
        t_end = datetime(2025, 6, 1, tzinfo=UTC)

        valid_manifest = DatasetManifest(
            dataset_id="ds_jamnagar_v1",
            dataset_version="v1.0.0",
            target_id="target_phenomenon_v1",
            feature_set_version="feat_v1",
            label_set_version="lbl_v1",
            geographic_scope="jamnagar_kutch",
            temporal_start=t_start,
            temporal_end=t_end,
            split_strategy=SplitStrategy.GROUPED_EVENT_HOLDOUT,
            record_count=150,
            sha256_hash="a" * 64,
            created_at=datetime.now(UTC),
        )
        assert valid_manifest.record_count == 150

        with pytest.raises(ValidationError):
            DatasetManifest(
                dataset_id="ds_invalid",
                dataset_version="v1.0.0",
                target_id="target_phenomenon_v1",
                feature_set_version="feat_v1",
                label_set_version="lbl_v1",
                geographic_scope="jamnagar_kutch",
                temporal_start=t_end,
                temporal_end=t_start,  # Inverted
                split_strategy=SplitStrategy.GROUPED_EVENT_HOLDOUT,
                record_count=100,
                sha256_hash="b" * 64,
                created_at=datetime.now(UTC),
            )

    def test_calibration_contract_forbids_test_split(self) -> None:
        """CalibrationContract rejects fitting on the TEST partition."""
        with pytest.raises(ValidationError):
            CalibrationContract(
                calibration_id="cal_001",
                method=CalibrationMethod.PLATT_SCALING,
                fitting_dataset_id="ds_jamnagar_v1",
                fitting_split_partition=SplitPartition.TEST,  # Disallowed
            )

        valid_cal = CalibrationContract(
            calibration_id="cal_001",
            method=CalibrationMethod.ISOTONIC_REGRESSION,
            fitting_dataset_id="ds_jamnagar_v1",
            fitting_split_partition=SplitPartition.VALIDATION,
        )
        assert valid_cal.fitting_split_partition == SplitPartition.VALIDATION
