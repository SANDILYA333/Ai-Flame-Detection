"""Comprehensive unit and integration test suite for ML-009 Model Artifacts.

Validates:
- Canonical schema validation and training provenance metadata.
- Preprocessor state serialization and transformation invariance.
- Model serialization, hashing, and reload invariance across B0, B2, B3, B4-DT, B4-RF.
- Feature schema contract validation and missing feature rejection.
- Artifact integrity validation, corruption detection, and tamper detection.
- Secret security scanner (rejection of API keys, tokens, credentials).
- End-to-end inference runtime execution (single, batch, event-level, abstention).
"""

import tempfile
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from packages.schemas.common import Coordinate
from packages.schemas.detection import Detection
from packages.schemas.enums import DayNight
from packages.schemas.event import Event
from packages.schemas.ml import (
    AbstentionContract,
    FeatureDataset,
    LabelDecision,
    LabelProvenanceType,
    LabelTier,
    ModelArtifact,
    ModelMetadata,
    SplitStrategy,
    TrainingRunManifest,
)
from services.ml.features.builder import FeatureDatasetBuilder
from services.ml.inference.engine import MLInferenceEngine
from services.ml.labels.dataset import SupervisedDatasetBuilder
from services.ml.models.contextual import DeterministicContextualClassifier
from services.ml.models.linear import LogisticRegressionClassifier
from services.ml.models.registry import ModelRegistry
from services.ml.models.tree import DecisionTreeClassifier, RandomForestClassifier
from services.ml.models.trivial import MajorityClassClassifier
from services.ml.preprocessing.transformer import FeaturePreprocessor
from services.ml.training.pipeline import MLTrainingPipeline


def _create_detection(
    det_id: str,
    t: datetime,
    lat: float = 22.48,
    lon: float = 70.06,
    frp: float = 35.0,
    sensor: str = "VIIRS",
) -> Detection:
    return Detection(
        detection_id=det_id,
        source="firms",
        source_snapshot_id="snap_1",
        geometry=Coordinate(latitude=lat, longitude=lon),
        acquired_at=t,
        satellite="SNPP" if sensor == "VIIRS" else "AQUA",
        instrument=sensor,
        product_type="nrt",
        product_version="v1.0",
        raw_hash=f"hash_{det_id}",
        frp_mw=frp,
        brightness_ti4_k=350.0,
        confidence="nominal",
        day_night=DayNight.NIGHT,
    )


def _create_event(
    event_id: str,
    det_id: str,
    t: datetime,
    lat: float = 22.48,
    lon: float = 70.06,
) -> Event:
    return Event(
        event_id=event_id,
        detection_ids=[det_id],
        detection_count=1,
        started_at=t,
        ended_at=t,
        centroid_geometry=Coordinate(latitude=lat, longitude=lon),
        formation_configuration_id="cfg_v1",
        formation_configuration_version="v1.0",
    )


@pytest.fixture
def benchmark_dataset_fixture() -> tuple[
    FeatureDataset, dict[str, Sequence[LabelDecision]]
]:
    """Fixture providing a deterministic multi-sample benchmark dataset."""
    t0 = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
    event_tuples = []
    labels = []

    for i in range(1, 41):
        is_ind = i % 2 == 1
        lat = 22.48 if is_ind else 25.00
        lon = 70.06 if is_ind else 75.00
        frp = 60.0 if is_ind else 10.0
        eid = f"evt_{i:03d}"
        t = t0 + timedelta(hours=i)

        det = _create_detection(f"det_{i:03d}", t, lat=lat, lon=lon, frp=frp)
        evt = _create_event(eid, f"det_{i:03d}", t, lat=lat, lon=lon)
        event_tuples.append((evt, [det], t + timedelta(hours=1), None, None, None))

        labels.append(
            LabelDecision(
                decision_id=f"dec_{eid}",
                target_id="target_industrial_segregation",
                entity_id=eid,
                assigned_class="industrial" if is_ind else "non_industrial",
                label_tier=LabelTier.TIER_A_AUTHORITATIVE,
                provenance_type=LabelProvenanceType.GROUND_TRUTH,
                decision_timestamp=t0,
            )
        )

    builder = FeatureDatasetBuilder()
    feat_ds = builder.extract_and_build_dataset(
        dataset_id="ds_supervised_v1.0.0",
        dataset_version="v1.0.0",
        target_id="target_industrial_segregation",
        geographic_scope="IND_MULTI_REGION",
        temporal_start=t0,
        temporal_end=t0 + timedelta(days=5),
        split_strategy=SplitStrategy.GROUPED_EVENT_HOLDOUT,
        event_tuples=event_tuples,
    )

    return feat_ds, {"target_industrial_segregation": labels}


class TestML009ModelArtifacts:
    """Test suite for ML-009 Model Artifacts & Inference Contract."""

    def test_preprocessor_state_serialization_and_invariance(self) -> None:
        """FeaturePreprocessor serializes state and reproduces identical matrices."""
        train_data: list[dict[str, Any]] = [
            {"frp_mean": 50.0, "day_night": "night", "is_persistent": True},
            {"frp_mean": 20.0, "day_night": "day", "is_persistent": False},
            {"frp_mean": 80.0, "day_night": "night", "is_persistent": True},
        ]
        test_data: list[dict[str, Any]] = [
            {"frp_mean": 45.0, "day_night": "night", "is_persistent": True},
            {"frp_mean": None, "day_night": "day", "is_persistent": False},
        ]

        prep = FeaturePreprocessor()
        prep.fit(train_data)
        out_orig = prep.transform(test_data)

        # Serialize and reconstruct
        state = prep.to_dict()
        prep_recon = FeaturePreprocessor.from_dict(state)
        out_recon = prep_recon.transform(test_data)

        assert prep_recon.is_fitted is True
        assert prep_recon.feature_names == prep.feature_names
        assert prep_recon.output_column_names == prep.output_column_names
        assert out_orig == out_recon

    @pytest.mark.parametrize(
        "model_cls,model_type",
        [
            (MajorityClassClassifier, "MajorityClassClassifier"),
            (DeterministicContextualClassifier, "DeterministicContextualClassifier"),
            (LogisticRegressionClassifier, "LogisticRegressionClassifier"),
            (DecisionTreeClassifier, "DecisionTreeClassifier"),
            (RandomForestClassifier, "RandomForestClassifier"),
        ],
    )
    def test_model_artifact_reload_invariance_all_architectures(
        self,
        model_cls: type[Any],
        model_type: str,
    ) -> None:
        """All 5 models survive serialization roundtrip with identical output."""
        train_data = [
            {"frp_mean": 60.0, "facility_distance_m": 50.0},
            {"frp_mean": 10.0, "facility_distance_m": 5000.0},
            {"frp_mean": 80.0, "facility_distance_m": 20.0},
            {"frp_mean": 15.0, "facility_distance_m": 8000.0},
        ]
        y_train = ["industrial", "non_industrial", "industrial", "non_industrial"]

        prep = FeaturePreprocessor()
        prep.fit(train_data)

        model = model_cls(random_seed=42)
        if model_type == "DeterministicContextualClassifier":
            model.fit(train_data, y_train)
        else:
            x_vec = prep.transform(train_data)
            model.fit(x_vec, y_train)

        now = datetime.now(UTC)
        meta = ModelMetadata(
            model_id=f"test_{model_type.lower()}",
            model_type=model_type,
            model_version="v1.0.0",
            target_id="target_industrial_segregation",
            dataset_version="v1.0.0",
            feature_set_version="feat_v1.0.0",
            label_set_version="label_v1.0.0",
            split_version="GROUPED_EVENT_HOLDOUT",
            training_timestamp=now,
            train_record_count=len(train_data),
            feature_names=prep.feature_names,
            feature_dimensionality=len(prep.output_column_names),
        )
        artifact = ModelArtifact(
            metadata=meta,
            preprocessor_state=prep.to_dict(),
            model_parameters=model.get_parameters(),
            class_vocabulary=model.class_vocabulary,
        )
        content_hash = artifact.compute_content_hash()
        artifact = artifact.model_copy(update={"sha256_hash": content_hash})

        with tempfile.TemporaryDirectory() as tmp:
            fpath = Path(tmp) / "artifact.json"
            ModelRegistry.save_to_file(artifact, fpath)
            reloaded_art = ModelRegistry.load_from_file(fpath)

            recon_prep, recon_model = ModelRegistry.reconstruct_pipeline(reloaded_art)

            test_sample = [
                {"frp_mean": 70.0, "facility_distance_m": 40.0},
                {"frp_mean": 12.0, "facility_distance_m": 9000.0},
            ]

            if model_type == "DeterministicContextualClassifier":
                orig_preds = model.predict(test_sample)
                orig_probs = model.predict_proba(test_sample)
                recon_preds = recon_model.predict(test_sample)
                recon_probs = recon_model.predict_proba(test_sample)
            else:
                x_test_vec = prep.transform(test_sample)
                recon_x_vec = recon_prep.transform(test_sample)
                orig_preds = model.predict(x_test_vec)
                orig_probs = model.predict_proba(x_test_vec)
                recon_preds = recon_model.predict(recon_x_vec)
                recon_probs = recon_model.predict_proba(recon_x_vec)

            assert orig_preds == recon_preds
            assert orig_probs == recon_probs

    def test_feature_contract_validation_rejects_missing_features(self) -> None:
        """MLInferenceEngine rejects feature inputs with missing required keys."""
        train_data = [
            {"frp_mean": 50.0, "brightness_mean": 350.0, "confidence": 1.0},
            {"frp_mean": 10.0, "brightness_mean": 310.0, "confidence": 0.5},
        ]
        prep = FeaturePreprocessor()
        prep.fit(train_data)
        model = LogisticRegressionClassifier(random_seed=42)
        model.fit(prep.transform(train_data), ["industrial", "non_industrial"])

        meta = ModelMetadata(
            model_id="test_model",
            model_type="LogisticRegressionClassifier",
            model_version="v1.0.0",
            target_id="target_industrial_segregation",
            dataset_version="v1.0.0",
            feature_set_version="feat_v1.0.0",
            label_set_version="label_v1.0.0",
            split_version="GROUPED_EVENT_HOLDOUT",
            training_timestamp=datetime.now(UTC),
            train_record_count=2,
            feature_names=prep.feature_names,
        )
        artifact = ModelArtifact(
            metadata=meta,
            preprocessor_state=prep.to_dict(),
            model_parameters=model.get_parameters(),
            class_vocabulary=model.class_vocabulary,
        )

        engine = MLInferenceEngine(artifact)

        # Valid input passes
        valid_input = {
            "frp_mean": 45.0,
            "brightness_mean": 340.0,
            "confidence": 1.0,
        }
        res = engine.predict_features(valid_input)
        assert res.predicted_class in ("industrial", "non_industrial")

        # Missing 'confidence' feature must raise ValueError
        invalid_input = {"frp_mean": 45.0, "brightness_mean": 340.0}
        with pytest.raises(ValueError, match="Feature schema mismatch"):
            engine.predict_features(invalid_input)

        # Empty dictionary must raise ValueError
        with pytest.raises(ValueError, match="cannot be empty"):
            engine.predict_features({})

    def test_artifact_tamper_detection(self) -> None:
        """Altering model weights or parameters invalidates SHA-256 hash."""
        meta = ModelMetadata(
            model_id="test_model",
            model_type="LogisticRegressionClassifier",
            model_version="v1.0.0",
            target_id="target_industrial_segregation",
            dataset_version="v1.0.0",
            feature_set_version="feat_v1.0.0",
            label_set_version="label_v1.0.0",
            split_version="GROUPED_EVENT_HOLDOUT",
            training_timestamp=datetime.now(UTC),
            train_record_count=1,
        )
        artifact = ModelArtifact(
            metadata=meta,
            preprocessor_state={"is_fitted": True, "feature_names": ["f1"]},
            model_parameters={"weights": [0.5], "bias": 0.1},
            class_vocabulary=["industrial", "non_industrial"],
        )
        valid_hash = artifact.compute_content_hash()
        artifact_with_hash = artifact.model_copy(update={"sha256_hash": valid_hash})

        # Valid artifact passes integrity check
        assert ModelRegistry.verify_artifact_integrity(artifact_with_hash) is True

        # Tampered weights fail integrity check
        tampered_artifact = artifact_with_hash.model_copy(
            update={"model_parameters": {"weights": [999.9], "bias": 0.1}}
        )
        with pytest.raises(ValueError, match="content hash mismatch"):
            ModelRegistry.verify_artifact_integrity(tampered_artifact)

    def test_secret_security_scanner_rejects_credentials(self) -> None:
        """ModelRegistry rejects any artifact metadata containing API keys or tokens."""
        meta = ModelMetadata(
            model_id="test_model",
            model_type="LogisticRegressionClassifier",
            model_version="v1.0.0",
            target_id="target_industrial_segregation",
            dataset_version="v1.0.0",
            feature_set_version="feat_v1.0.0",
            label_set_version="label_v1.0.0",
            split_version="GROUPED_EVENT_HOLDOUT",
            training_timestamp=datetime.now(UTC),
            train_record_count=1,
            hyperparameters={"firms_map_key": "TEST_SECRET_VALUE"},
        )
        artifact = ModelArtifact(
            metadata=meta,
            preprocessor_state={},
            model_parameters={},
            class_vocabulary=["industrial", "non_industrial"],
        )

        with pytest.raises(ValueError, match="Prohibited sensitive key"):
            ModelRegistry.serialize_artifact(artifact)

    def test_end_to_end_training_manifest_and_inference_execution(
        self,
        benchmark_dataset_fixture: tuple[
            FeatureDataset, dict[str, Sequence[LabelDecision]]
        ],
    ) -> None:
        """Execute full training pipeline and evaluate inference with abstention."""
        feat_ds, label_map = benchmark_dataset_fixture
        sup_builder = SupervisedDatasetBuilder()
        sup_ds = sup_builder.build_supervised_dataset(
            feature_dataset=feat_ds,
            label_decisions_by_target=label_map,
            split_strategy=SplitStrategy.GROUPED_EVENT_HOLDOUT,
        )

        pipeline = MLTrainingPipeline(random_seed=42)
        result = pipeline.run_training_and_evaluation(
            dataset=sup_ds,
            target_id="target_industrial_segregation",
            model_type="RandomForestClassifier",
            hyperparameters={"n_estimators": 5, "max_depth": 3},
        )

        artifact = result["artifact"]
        manifest = result["run_manifest"]

        assert isinstance(artifact, ModelArtifact)
        assert isinstance(manifest, TrainingRunManifest)
        assert artifact.sha256_hash is not None
        assert manifest.artifact_hash == artifact.sha256_hash
        assert manifest.train_record_count > 0

        # Run MLInferenceEngine
        engine = MLInferenceEngine(
            artifact=artifact,
            abstention_contract=AbstentionContract(
                abstention_id="abs_high_confidence",
                confidence_threshold=0.999,  # High threshold triggers abstention
                allow_abstention=True,
            ),
        )

        sample_features = feat_ds.records[0].features
        pred_res = engine.predict_features(sample_features)

        assert pred_res.target_id == "target_industrial_segregation"
        assert pred_res.model_type == "RandomForestClassifier"
        assert pred_res.predicted_class in ("industrial", "non_industrial")
        assert pred_res.confidence >= 0.0
        assert pred_res.is_abstained is True
        assert pred_res.abstention_reason == "LOW_CONFIDENCE"

        # Run batch prediction
        batch_res = engine.predict_batch([sample_features, sample_features])
        assert len(batch_res) == 2
