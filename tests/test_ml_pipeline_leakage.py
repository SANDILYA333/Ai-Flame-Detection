"""Adversarial leakage tests and secret audit tests for ML training pipeline."""

from datetime import UTC, datetime

import pytest

from packages.schemas.ml import (
    DatasetManifest,
    FeatureDefinition,
    FeatureEligibilityStatus,
    FeatureGroup,
    FeatureMissingnessHandling,
    FeatureRecord,
    FeatureType,
    LabelDecision,
    LabeledFeatureRecord,
    LabelProvenanceType,
    LabelTier,
    ModelArtifact,
    ModelMetadata,
    SplitManifest,
    SplitPartition,
    SplitStrategy,
    SupervisedDataset,
)
from services.ml.models.registry import ModelRegistry
from services.ml.preprocessing.extractor import (
    PROHIBITED_METADATA_COLUMNS,
    DatasetSplitExtractor,
)
from services.ml.preprocessing.transformer import FeaturePreprocessor


class TestMLPipelineLeakage:
    """Adversarial test suite preventing data leakage and secret exposure."""

    def test_prohibited_metadata_and_id_stripping(self) -> None:
        """Adversarial test: non-feature columns and IDs are completely stripped."""
        t0 = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)

        # Create record with adversarial metadata injected into features
        poisoned_features: dict[str, float | int | str | bool | None] = {
            "core_frp_mw": 55.0,
            "event_id": "evt_leak_999",
            "source_id": "src_leak_888",
            "facility_id": "fac_leak_777",
            "target": "industrial",
            "label_tier": "TIER_A_AUTHORITATIVE",
            "provenance": "poisoned_lineage",
            "as_of_time": t0.isoformat(),
        }

        feat_rec = FeatureRecord(
            entity_id="evt_001",
            as_of_time=t0,
            features=poisoned_features,
        )

        label_dec = LabelDecision(
            decision_id="dec_001",
            target_id="target_industrial_segregation",
            entity_id="evt_001",
            assigned_class="industrial",
            label_tier=LabelTier.TIER_A_AUTHORITATIVE,
            provenance_type=LabelProvenanceType.GROUND_TRUTH,
            decision_timestamp=t0,
        )

        labeled_rec = LabeledFeatureRecord(
            entity_id="evt_001",
            feature_record=feat_rec,
            labels={"target_industrial_segregation": label_dec},
            split_partition=SplitPartition.TRAIN,
        )

        manifest = DatasetManifest(
            dataset_id="ds_leak_test",
            dataset_version="v1.0.0",
            target_id="target_industrial_segregation",
            feature_set_version="feat_v1.0.0",
            label_set_version="label_v1.0.0",
            geographic_scope="IND_GUJARAT",
            temporal_start=t0,
            temporal_end=t0,
            split_strategy=SplitStrategy.GROUPED_EVENT_HOLDOUT,
            record_count=1,
            sha256_hash="0" * 64,
            created_at=t0,
        )

        split_manifest = SplitManifest(
            split_id="split_leak_test",
            dataset_id="ds_leak_test",
            dataset_version="v1.0.0",
            split_strategy=SplitStrategy.GROUPED_EVENT_HOLDOUT,
            created_at=t0,
        )

        dataset = SupervisedDataset(
            manifest=manifest,
            split_manifest=split_manifest,
            records=[labeled_rec],
            feature_definitions=[
                FeatureDefinition(
                    feature_name="core_frp_mw",
                    feature_type=FeatureType.NUMERIC,
                    feature_group=FeatureGroup.THERMAL_CORE,
                    eligibility_status=FeatureEligibilityStatus.APPROVED,
                    source_entity="Event",
                    derivation_description="Event peak FRP",
                    is_model_input=True,
                    missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
                    version="v1.0.0",
                )
            ],
        )

        (
            x_train,
            _y_train,
            _ids_train,
            _x_val,
            _y_val,
            _ids_val,
            _x_test,
            _y_test,
            _ids_test,
        ) = DatasetSplitExtractor.extract_split_matrices(
            dataset=dataset,
            target_id="target_industrial_segregation",
        )

        assert len(x_train) == 1
        clean_row = x_train[0]

        # Only approved features must exist
        assert "core_frp_mw" in clean_row
        assert clean_row["core_frp_mw"] == 55.0

        for col in PROHIBITED_METADATA_COLUMNS:
            assert col not in clean_row

    def test_preprocessor_training_state_invariance(self) -> None:
        """FeaturePreprocessor on TRAIN is invariant to val/test distributions."""
        train_data = [{"val": 10.0}, {"val": 20.0}, {"val": 30.0}]
        val_data = [{"val": 1000.0}, {"val": 2000.0}]

        prep = FeaturePreprocessor().fit(train_data)
        initial_mean = prep.numeric_means["val"]
        initial_std = prep.numeric_stds["val"]

        # Transform validation data with extreme values
        prep.transform(val_data)

        # Verify TRAIN statistics did not mutate
        assert prep.numeric_means["val"] == initial_mean
        assert prep.numeric_stds["val"] == initial_std

    def test_model_registry_secret_leak_detection(self) -> None:
        """ModelRegistry raises ValueError if sensitive tokens/keys are in metadata."""
        meta = ModelMetadata(
            model_id="test_model_leak",
            model_type="MajorityClassClassifier",
            model_version="v1.0.0",
            target_id="target_industrial_segregation",
            dataset_version="v1.0.0",
            feature_set_version="feat_v1.0.0",
            label_set_version="label_v1.0.0",
            split_version="GROUPED_EVENT_HOLDOUT",
            training_timestamp=datetime.now(UTC),
            train_record_count=1,
            hyperparameters={"firms_map_key": "secret_abc123"},
        )

        artifact = ModelArtifact(metadata=meta)

        with pytest.raises(ValueError, match="Prohibited sensitive key"):
            ModelRegistry.serialize_artifact(artifact)
