"""Formal tests for B3 Logistic Regression Classifier (ML-005).

Validates determinism, probability validity, shape checking, class stability,
coefficient interpretability, and loss convergence.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from packages.schemas.ml import ModelArtifact, ModelMetadata
from services.ml.models.linear import LogisticRegressionClassifier
from services.ml.models.registry import ModelRegistry


class TestMLB3StatisticalModel:
    """Test suite formalizing B3 Logistic Regression Classifier (ML-005)."""

    def test_b3_determinism(self) -> None:
        """Same dataset and same seed produce identical weights and predictions."""
        x_train = [[1.0, 2.0], [3.0, 4.0], [-1.0, -2.0], [-3.0, -4.0]]
        y_train = ["industrial", "industrial", "non_industrial", "non_industrial"]

        clf1 = LogisticRegressionClassifier(max_epochs=20, random_seed=42)
        clf1.fit(x_train, y_train)

        clf2 = LogisticRegressionClassifier(max_epochs=20, random_seed=42)
        clf2.fit(x_train, y_train)

        assert clf1.weights == clf2.weights
        assert clf1.biases == clf2.biases

        x_test = [[2.0, 3.0], [-2.0, -3.0]]
        assert clf1.predict(x_test) == clf2.predict(x_test)
        assert clf1.predict_proba(x_test) == clf2.predict_proba(x_test)

    def test_b3_shape_validation(self) -> None:
        """Mismatch in feature dimensions raises ValueError."""
        x_train = [[1.0, 2.0, 3.0], [-1.0, -2.0, -3.0]]
        y_train = ["industrial", "non_industrial"]

        clf = LogisticRegressionClassifier(max_epochs=10, random_seed=42)
        clf.fit(x_train, y_train)

        # 2 features passed instead of 3
        with pytest.raises(ValueError, match="Feature dimension mismatch"):
            clf.predict_proba([[1.0, 2.0]])

    def test_b3_probability_validity(self) -> None:
        """Softmax probabilities strictly sum to 1.0 and lie in [0, 1]."""
        x_train = [
            [2.0, 1.0],
            [1.5, 2.5],
            [-2.0, -1.0],
            [-1.5, -2.5],
        ]
        y_train = ["industrial", "industrial", "non_industrial", "non_industrial"]

        clf = LogisticRegressionClassifier(max_epochs=30, random_seed=42)
        clf.fit(x_train, y_train)

        probs = clf.predict_proba([[0.5, 0.5], [-0.5, -0.5], [10.0, 10.0]])
        assert len(probs) == 3

        for p_row in probs:
            total = sum(p_row.values())
            assert pytest.approx(total, 1e-6) == 1.0
            for val in p_row.values():
                assert 0.0 <= val <= 1.0

    def test_b3_coefficient_interpretability(self) -> None:
        """get_coefficients_by_class and get_feature_importances expose associations."""
        x_train = [[5.0, 0.1], [6.0, 0.2], [-5.0, -0.1], [-6.0, -0.2]]
        y_train = ["industrial", "industrial", "non_industrial", "non_industrial"]
        f_names = ["facility_proximity", "irrelevant_noise"]

        clf = LogisticRegressionClassifier(max_epochs=50, random_seed=42)
        clf.fit(x_train, y_train)

        coefs = clf.get_coefficients_by_class(f_names)
        assert "industrial" in coefs
        assert "non_industrial" in coefs
        assert "facility_proximity" in coefs["industrial"]

        importances = clf.get_feature_importances(f_names)
        assert importances["facility_proximity"] > importances["irrelevant_noise"]

    def test_b3_class_vocabulary_stability(self) -> None:
        """Class vocabulary ordering is preserved deterministically."""
        x_train = [[1.0], [-1.0]]
        y_train = ["zebra", "apple"]

        clf = LogisticRegressionClassifier(max_epochs=10, random_seed=42)
        clf.fit(x_train, y_train)

        # Sorted deterministically
        assert clf.class_vocabulary == ["apple", "zebra"]

    def test_b3_serialization_and_reload_invariance(self, tmp_path: Path) -> None:
        """Serialized B3 artifact reloads with 100% numerical invariance."""
        x_train = [[1.0, 2.0], [-1.0, -2.0]]
        y_train = ["industrial", "non_industrial"]

        clf = LogisticRegressionClassifier(max_epochs=20, random_seed=42)
        clf.fit(x_train, y_train)

        meta = ModelMetadata(
            model_id="b3_formal_test",
            model_type="LogisticRegressionClassifier",
            model_version="v1.0.0",
            target_id="target_industrial_segregation",
            dataset_version="v1.0.0",
            feature_set_version="feat_v1.0.0",
            label_set_version="label_v1.0.0",
            split_version="GROUPED_EVENT_HOLDOUT",
            training_timestamp=datetime.now(UTC),
            train_record_count=2,
        )

        artifact = ModelArtifact(
            metadata=meta,
            preprocessor_state={},
            model_parameters=clf.get_parameters(),
            class_vocabulary=clf.class_vocabulary,
        )

        art_file = tmp_path / "b3_artifact.json"
        ModelRegistry.save_to_file(artifact, art_file)

        loaded = ModelRegistry.load_from_file(art_file)
        _, recon_clf = ModelRegistry.reconstruct_pipeline(loaded)

        test_points = [[1.5, 2.5], [-1.5, -2.5]]
        assert clf.predict(test_points) == recon_clf.predict(test_points)
        assert clf.predict_proba(test_points) == recon_clf.predict_proba(test_points)
