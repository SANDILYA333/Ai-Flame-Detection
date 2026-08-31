"""Unit tests for ML baseline classifiers and ModelRegistry."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from packages.schemas.ml import ModelArtifact, ModelMetadata
from services.ml.models.contextual import DeterministicContextualClassifier
from services.ml.models.linear import LogisticRegressionClassifier
from services.ml.models.registry import ModelRegistry
from services.ml.models.trivial import MajorityClassClassifier
from services.ml.preprocessing.transformer import FeaturePreprocessor


class TestMLBaselineModels:
    """Test suite validating baseline classifiers and model persistence."""

    def test_majority_class_classifier_b0(self) -> None:
        """MajorityClassClassifier predicts empirical class prior and majority class."""
        x_train = [[1.0], [2.0], [3.0], [4.0]]
        y_train = ["industrial", "industrial", "industrial", "non_industrial"]

        clf = MajorityClassClassifier(random_seed=42)
        clf.fit(x_train, y_train)

        assert clf.is_fitted is True
        assert clf.majority_class == "industrial"
        assert clf.class_priors["industrial"] == 0.75
        assert clf.class_priors["non_industrial"] == 0.25

        x_test = [[10.0], [20.0]]
        preds = clf.predict(x_test)
        assert preds == ["industrial", "industrial"]

        probs = clf.predict_proba(x_test)
        assert len(probs) == 2
        assert probs[0]["industrial"] == 0.75

    def test_deterministic_contextual_classifier_b2(self) -> None:
        """DeterministicContextualClassifier applies distance rules properly."""
        clf = DeterministicContextualClassifier(proximity_threshold_m=1000.0)
        clf.fit([], ["industrial", "non_industrial"])

        # Row 1: 200m from industrial facility -> industrial
        # Row 2: 5000m from industrial facility -> non_industrial
        x_data = [
            {"ctx_dist_osm_industrial_m": 200.0, "det_is_night": True},
            {"ctx_dist_osm_industrial_m": 5000.0, "det_is_night": False},
        ]

        preds = clf.predict(x_data)
        assert preds == ["industrial", "non_industrial"]

        probs = clf.predict_proba(x_data)
        assert probs[0]["industrial"] > probs[0]["non_industrial"]

    def test_logistic_regression_classifier_b3(self) -> None:
        """LogisticRegressionClassifier converges and outputs valid probabilities."""
        # Linearly separable 2-feature toy data
        x_train = [
            [1.0, 1.0],
            [1.2, 0.9],
            [0.8, 1.1],
            [-1.0, -1.0],
            [-1.2, -0.9],
            [-0.8, -1.1],
        ]
        y_train = [
            "industrial",
            "industrial",
            "industrial",
            "non_industrial",
            "non_industrial",
            "non_industrial",
        ]

        clf = LogisticRegressionClassifier(
            learning_rate=0.1, max_epochs=100, l2_lambda=0.001, random_seed=42
        )
        clf.fit(x_train, y_train)

        assert clf.is_fitted is True
        assert len(clf.training_loss_history) == 100
        # Loss should decrease
        assert clf.training_loss_history[-1] < clf.training_loss_history[0]

        # Predict on new samples
        x_test = [[1.5, 1.5], [-1.5, -1.5]]
        preds = clf.predict(x_test)
        assert preds == ["industrial", "non_industrial"]

        probs = clf.predict_proba(x_test)
        assert len(probs) == 2
        for p_dict in probs:
            assert pytest.approx(sum(p_dict.values()), 1e-5) == 1.0

        # Feature importances
        importances = clf.get_feature_importances(["f1", "f2"])
        assert "f1" in importances
        assert "f2" in importances

    def test_model_registry_save_load_roundtrip(self, tmp_path: Path) -> None:
        """ModelRegistry saves artifact, audits secrets, and reconstructs pipeline."""
        train_data = [{"dist": 100.0}, {"dist": 2000.0}]
        prep = FeaturePreprocessor().fit(train_data)
        x_vec = prep.transform(train_data)

        model = LogisticRegressionClassifier(max_epochs=10, random_seed=42)
        model.fit(x_vec, ["industrial", "non_industrial"])

        meta = ModelMetadata(
            model_id="test_model_001",
            model_type="LogisticRegressionClassifier",
            model_version="v1.0.0",
            target_id="target_industrial_segregation",
            dataset_version="v1.0.0",
            feature_set_version="feat_v1.0.0",
            label_set_version="label_v1.0.0",
            split_version="GROUPED_EVENT_HOLDOUT",
            random_seed=42,
            training_timestamp=datetime.now(UTC),
            train_record_count=2,
            feature_names=prep.output_column_names,
        )

        artifact = ModelArtifact(
            metadata=meta,
            preprocessor_state=prep.to_dict(),
            model_parameters=model.get_parameters(),
            class_vocabulary=model.class_vocabulary,
        )

        model_file = tmp_path / "model_artifact.json"
        ModelRegistry.save_to_file(artifact, model_file)

        loaded_artifact = ModelRegistry.load_from_file(model_file)
        recon_prep, recon_model = ModelRegistry.reconstruct_pipeline(loaded_artifact)

        # Verify predictions match perfectly
        test_sample = [{"dist": 150.0}]
        orig_pred = model.predict(prep.transform(test_sample))
        recon_pred = recon_model.predict(recon_prep.transform(test_sample))
        assert orig_pred == recon_pred
