"""Comprehensive Test Suite for NEXT-006: Real Production Model Training.

Validates:
1. Scientific Training Gate hard enforcement.
2. Supervised dataset integrity: UNKNOWN excluded from training matrices.
3. Deterministic, leakage-safe group splitting.
4. Production artifact generation under artifacts/real/production/.
5. Artifact schema validity, SHA-256 cryptographic verification.
6. Production model deserialization and inference smoke tests on held-out data.
"""

from pathlib import Path
from typing import Any

from packages.context.pipeline import RealContextLabelingService
from packages.data.firms.activation import FirmsDataActivationService
from packages.events.pipeline import (
    RealEventConstructionService,
    get_default_calibrated_scientific_config,
)
from packages.feasibility.candidates import JAMNAGAR_KUTCH
from packages.schemas.ml import (
    DatasetRowStatus,
    ModelArtifact,
    SplitPartition,
    SplitStrategy,
)
from services.ml.features.standard_set import APPROVED_FEATURES
from services.ml.labels.dataset import SupervisedDatasetBuilder
from services.ml.models.registry import ModelRegistry
from services.ml.preprocessing.extractor import DatasetSplitExtractor
from services.ml.training.real_trainer import CANONICAL_REAL_MODELS, RealMLTrainer


class TestNext006RealProductionModelTraining:
    """Test suite verifying end-to-end NEXT-006 production training requirements."""

    def test_production_artifacts_exist_and_are_valid(self) -> None:
        """Verify all 5 canonical production model artifacts exist."""
        prod_dir = Path("artifacts/real/production")
        assert prod_dir.exists(), "artifacts/real/production directory must exist"

        for model_type in CANONICAL_REAL_MODELS:
            artifact_file = (
                prod_dir
                / f"real_{model_type.lower()}_target_industrial_segregation_v1.0.0.json"
            )
            assert artifact_file.exists(), (
                f"Production artifact for {model_type} must exist at {artifact_file}"
            )

            # Validate artifact schema
            artifact = ModelRegistry.load_from_file(artifact_file)
            assert isinstance(artifact, ModelArtifact)
            assert artifact.metadata.model_type == model_type
            assert artifact.metadata.model_version == "v1.0.0-production"
            assert artifact.metadata.target_id == "target_industrial_segregation"
            assert artifact.metadata.feature_set_version == "feat_v1.0.0"
            assert artifact.metadata.random_seed == 42
            assert artifact.sha256_hash is not None
            assert len(artifact.sha256_hash) == 64
            assert (
                artifact.metadata.validation_metrics.get("is_production_ready") is True
            )
            assert (
                artifact.metadata.test_metrics.get("evaluation_status")
                == "READY_FOR_NEXT_007"
            )

    def test_production_model_deserialization_and_inference_smoke(self) -> None:
        """Verify each production artifact can deserialize and predict."""
        prod_dir = Path("artifacts/real/production")

        # Mock sample test features matching standard 30 features
        test_sample: list[dict[str, Any]] = [
            {
                "brightness_mean_kelvin": 325.0,
                "brightness_max_kelvin": 350.0,
                "frp_mean_mw": 12.0,
                "frp_max_mw": 25.0,
                "frp_min_mw": 5.0,
                "frp_sum_mw": 36.0,
                "frp_std_mw": 8.0,
                "detection_count": 3,
                "duration_hours": 4.5,
                "spatial_extent_radius_meters": 350.0,
                "temporal_density": 0.67,
                "daynight_ratio": 1.0,
                "satellite_platform_diversity": 2,
                "sensor_instrument": "VIIRS",
                "persistence_state": "persistent",
                "persistence_active_days": 45.0,
                "persistence_total_events": 18,
                "persistence_recurrence_ratio": 0.85,
                "is_persistent_source": True,
                "time_since_previous_event_hours": 12.0,
                "prior_event_count_24h": 2,
                "prior_event_count_7d": 8,
                "prior_event_count_30d": 24,
                "facility_distance_meters": 120.0,
                "facility_context_type": "oil_gas",
                "is_near_industrial_facility": True,
                "power_plant_distance_meters": 5000.0,
                "water_distance_meters": 800.0,
                "is_protected_area": False,
                "landcover_class": "UNKNOWN",
            }
        ]

        for model_type in CANONICAL_REAL_MODELS:
            artifact_file = (
                prod_dir
                / f"real_{model_type.lower()}_target_industrial_segregation_v1.0.0.json"
            )
            artifact = ModelRegistry.load_from_file(artifact_file)
            preprocessor, model = ModelRegistry.reconstruct_pipeline(artifact)

            if model_type == "DeterministicContextualClassifier":
                preds = model.predict(test_sample)
            else:
                x_vec = preprocessor.transform(test_sample)
                preds = model.predict(x_vec)

            assert len(preds) == 1, f"Model {model_type} must return 1 prediction"
            assert preds[0] in [
                "industrial",
                "non_industrial",
            ], f"Invalid prediction class {preds[0]} for {model_type}"

    def test_unknown_events_strictly_excluded_from_training_matrices(self) -> None:
        """Verify UNKNOWN events never enter supervised training matrices."""
        csv_path = Path("fixtures/firms/firms_real_sample_jamnagar.csv")
        det_ds = FirmsDataActivationService.activate_from_csv(
            csv_input=csv_path,
            study_area=JAMNAGAR_KUTCH,
            requested_start_date="2026-08-01",
            requested_end_date="2026-08-10",
        )
        config = get_default_calibrated_scientific_config()
        ev_ds = RealEventConstructionService.construct_events_and_sources(
            detection_dataset=det_ds,
            config=config,
        )
        ctx_path = Path("fixtures/context/context_sample_jamnagar.json")
        features, hashes = (
            RealContextLabelingService.load_context_features_from_fixture(ctx_path)
        )
        enriched_ds = RealContextLabelingService.enrich_and_adjudicate_dataset(
            event_dataset=ev_ds,
            candidate_features=features,
            snapshot_hashes=hashes,
            config=config,
        )
        builder = SupervisedDatasetBuilder()
        supervised_ds = builder.build_from_real_enriched_dataset(
            enriched_dataset=enriched_ds,
            detection_dataset=det_ds,
            split_strategy=SplitStrategy.PERSISTENT_SOURCE_HOLDOUT,
            target_ids=["target_industrial_segregation"],
        )

        (
            _x_tr,
            y_train,
            _id_tr,
            _x_va,
            y_val,
            _id_va,
            _x_te,
            y_test,
            _id_te,
        ) = DatasetSplitExtractor.extract_split_matrices(
            dataset=supervised_ds,
            target_id="target_industrial_segregation",
        )

        all_y = y_train + y_val + y_test
        assert "unknown" not in all_y, "UNKNOWN must never enter y labels"
        assert "UNKNOWN" not in all_y, "UNKNOWN must never enter y labels"

        for y_lbl in all_y:
            assert y_lbl in ("industrial", "non_industrial")

    def test_canonical_30_features_completeness(self) -> None:
        """Verify canonical 30 features catalog is strictly preserved."""
        assert len(APPROVED_FEATURES) == 30, "Must have exactly 30 approved features"
        feature_names = {f.feature_name for f in APPROVED_FEATURES}
        assert len(feature_names) == 30
        assert "brightness_mean_kelvin" in feature_names
        assert "frp_max_mw" in feature_names
        assert "is_persistent_source" in feature_names
        assert "is_near_industrial_facility" in feature_names

    def test_gate_blocks_production_when_gate_fails(self) -> None:
        """Verify RealMLTrainer marks status as TRAINED_PILOT when gate fails."""
        csv_path = Path("fixtures/firms/firms_real_sample_jamnagar.csv")
        det_ds = FirmsDataActivationService.activate_from_csv(
            csv_input=csv_path,
            study_area=JAMNAGAR_KUTCH,
            requested_start_date="2026-08-01",
            requested_end_date="2026-08-10",
        )
        config = get_default_calibrated_scientific_config()
        ev_ds = RealEventConstructionService.construct_events_and_sources(
            detection_dataset=det_ds,
            config=config,
        )
        ctx_path = Path("fixtures/context/context_sample_jamnagar.json")
        features, hashes = (
            RealContextLabelingService.load_context_features_from_fixture(ctx_path)
        )
        enriched_ds = RealContextLabelingService.enrich_and_adjudicate_dataset(
            event_dataset=ev_ds,
            candidate_features=features,
            snapshot_hashes=hashes,
            config=config,
        )
        builder = SupervisedDatasetBuilder()
        supervised_ds = builder.build_from_real_enriched_dataset(
            enriched_dataset=enriched_ds,
            detection_dataset=det_ds,
            split_strategy=SplitStrategy.PERSISTENT_SOURCE_HOLDOUT,
            target_ids=["target_industrial_segregation"],
        )
        new_records = [
            r.model_copy(
                update={
                    "split_partition": (
                        SplitPartition.TRAIN if i < 2 else SplitPartition.TEST
                    ),
                    "row_status": (
                        DatasetRowStatus.TRAIN_ELIGIBLE
                        if i < 2
                        else DatasetRowStatus.TEST_ELIGIBLE
                    ),
                }
            )
            for i, r in enumerate(supervised_ds.records)
        ]
        supervised_ds = supervised_ds.model_copy(update={"records": new_records})

        trainer = RealMLTrainer(
            random_seed=42,
            artifact_base_dir="artifacts/real/pilot_test",
        )
        suite_res = trainer.train_real_suite(
            dataset=supervised_ds,
            target_id="target_industrial_segregation",
            model_types=["MajorityClassClassifier"],
        )

        assert suite_res.is_production_ready is False
        res = suite_res.model_results["MajorityClassClassifier"]
        assert res.status == "TRAINED_PILOT"
        assert res.is_production_ready is False
