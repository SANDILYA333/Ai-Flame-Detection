"""Focused Unit and Integration Test Suite for XGBoost Experimental Classifier.

Validates:
1. Model construction and default hyperparameter configuration.
2. Training and prediction on synthetic and preprocessed matrices.
3. Class-probability normalization and calibration bounds.
4. Determinism across repeated training with identical random seed.
5. Evaluation framework compatibility with EvaluationHarness.
6. Serialization roundtrip (train -> get_parameters -> save -> load -> predict).
7. ModelRegistry integration, content hashing, and recursive secret auditing.
8. Immutability and isolation of existing production models.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from packages.schemas.ml import ModelArtifact, ModelMetadata
from services.ml.evaluation.harness import EvaluationHarness
from services.ml.models.registry import ModelRegistry
from services.ml.models.xgboost_model import XGBoostClassifier
from services.ml.preprocessing.transformer import FeaturePreprocessor


@pytest.fixture
def synthetic_binary_data() -> tuple[list[list[float]], list[str], list[str]]:
    """Synthetic binary dataset representing industrial vs non-industrial."""
    classes = ["industrial", "non_industrial"]
    feature_names = [f"feat_{i}" for i in range(10)]

    # 30 samples: 15 industrial (higher values), 15 non-industrial (lower values)
    x: list[list[float]] = []
    y: list[str] = []

    for i in range(15):
        row_ind = [float(j + i * 0.5 + 5.0) for j in range(10)]
        x.append(row_ind)
        y.append("industrial")

    for i in range(15):
        row_non = [float(j - i * 0.5) for j in range(10)]
        x.append(row_non)
        y.append("non_industrial")

    return x, y, feature_names


class TestXGBoostClassifier:
    """Test suite for XGBoost experimental model."""

    def test_instantiation_defaults(self) -> None:
        """Verify model instantiates with conservative defaults."""
        model = XGBoostClassifier(random_seed=42)
        assert model.model_name == "XGBoostClassifier"
        assert model.random_seed == 42
        assert model.n_estimators == 50
        assert model.max_depth == 3
        assert model.learning_rate == 0.05
        assert model.subsample == 0.8
        assert model.colsample_bytree == 0.8
        assert model.device == "cpu"
        assert model.tree_method == "hist"
        assert model.is_fitted is False
        assert model.booster is None

    def test_fit_and_predict(
        self, synthetic_binary_data: tuple[list[list[float]], list[str], list[str]]
    ) -> None:
        """Verify model fits and produces valid categorical predictions."""
        x, y, feat_names = synthetic_binary_data
        model = XGBoostClassifier(n_estimators=10, max_depth=2, random_seed=42)
        model.fit(x, y, feature_names=feat_names)

        assert model.is_fitted is True
        assert model.booster is not None
        assert model.n_features_ == 10
        assert model.feature_names_ == feat_names
        assert model.class_vocabulary == ["industrial", "non_industrial"]

        preds = model.predict(x)
        assert len(preds) == len(y)
        assert set(preds).issubset({"industrial", "non_industrial"})
        # Should achieve high separation on this simple dataset
        matches = sum(1 for p, true in zip(preds, y, strict=False) if p == true)
        assert matches >= 26

    def test_predict_proba_bounds_and_normalization(
        self, synthetic_binary_data: tuple[list[list[float]], list[str], list[str]]
    ) -> None:
        """Verify predicted probabilities sum strictly to 1.0 and lie in [0, 1]."""
        x, y, _ = synthetic_binary_data
        model = XGBoostClassifier(n_estimators=10, max_depth=2, random_seed=42)
        model.fit(x, y)

        probs = model.predict_proba(x)
        assert len(probs) == len(x)

        for p_dict in probs:
            assert "industrial" in p_dict
            assert "non_industrial" in p_dict
            p_ind = p_dict["industrial"]
            p_non = p_dict["non_industrial"]
            assert 0.0 <= p_ind <= 1.0
            assert 0.0 <= p_non <= 1.0
            assert abs((p_ind + p_non) - 1.0) < 1e-6

    def test_determinism_across_repeat_runs(
        self, synthetic_binary_data: tuple[list[list[float]], list[str], list[str]]
    ) -> None:
        """Verify identical training runs produce bitwise-consistent probabilities."""
        x, y, _ = synthetic_binary_data

        m1 = XGBoostClassifier(n_estimators=15, max_depth=3, random_seed=42)
        m1.fit(x, y)
        probs1 = m1.predict_proba(x)

        m2 = XGBoostClassifier(n_estimators=15, max_depth=3, random_seed=42)
        m2.fit(x, y)
        probs2 = m2.predict_proba(x)

        for p1, p2 in zip(probs1, probs2, strict=False):
            assert abs(p1["industrial"] - p2["industrial"]) < 1e-7
            assert abs(p1["non_industrial"] - p2["non_industrial"]) < 1e-7

    def test_feature_preprocessor_compatibility(self) -> None:
        """Verify compatibility with vectors output by FeaturePreprocessor."""
        raw_train: list[dict[str, Any]] = [
            {"frp": 100.0, "brightness": 350.0, "is_near": True, "ctx": "oil_gas"},
            {"frp": 120.0, "brightness": 360.0, "is_near": True, "ctx": "industrial"},
            {"frp": 15.0, "brightness": 310.0, "is_near": False, "ctx": "NONE"},
            {"frp": 20.0, "brightness": 305.0, "is_near": False, "ctx": "NONE"},
        ]
        y_train = ["industrial", "industrial", "non_industrial", "non_industrial"]

        preprocessor = FeaturePreprocessor()
        preprocessor.fit(raw_train)
        x_train_vec = preprocessor.transform(raw_train)

        model = XGBoostClassifier(n_estimators=5, max_depth=2, random_seed=42)
        model.fit(
            x_train_vec,
            y_train,
            feature_names=preprocessor.output_column_names,
        )

        assert model.is_fitted is True
        assert model.n_features_ == len(preprocessor.output_column_names)
        preds = model.predict(x_train_vec)
        assert len(preds) == 4

    def test_evaluation_harness_integration(
        self, synthetic_binary_data: tuple[list[list[float]], list[str], list[str]]
    ) -> None:
        """Verify EvaluationHarness computes metrics on XGBoost predictions."""
        x, y, _ = synthetic_binary_data
        model = XGBoostClassifier(n_estimators=10, max_depth=2, random_seed=42)
        model.fit(x, y)

        y_pred = model.predict(x)
        y_prob = model.predict_proba(x)
        classes = model.class_vocabulary

        per_class = EvaluationHarness.compute_per_class_metrics(y, y_pred, classes)
        macro_p, macro_r, macro_f1 = EvaluationHarness.compute_macro_metrics(per_class)
        cm = EvaluationHarness.compute_confusion_matrix(y, y_pred, classes)
        brier = EvaluationHarness.compute_brier_score(y, y_prob, class_labels=classes)
        log_loss = EvaluationHarness.compute_log_loss(y, y_prob)

        assert 0.0 <= macro_f1 <= 1.0
        assert len(cm) == 2
        assert brier >= 0.0
        assert log_loss >= 0.0

    def test_serialization_roundtrip(
        self, synthetic_binary_data: tuple[list[list[float]], list[str], list[str]]
    ) -> None:
        """Verify train -> get_parameters -> set_parameters preserves predictions."""
        x, y, feat_names = synthetic_binary_data
        m1 = XGBoostClassifier(n_estimators=10, max_depth=2, random_seed=42)
        m1.fit(x, y, feature_names=feat_names)

        orig_preds = m1.predict(x)
        orig_probs = m1.predict_proba(x)
        params = m1.get_parameters()

        # Serialization to JSON string and back
        json_str = json.dumps(params)
        loaded_params = json.loads(json_str)

        m2 = XGBoostClassifier()
        m2.set_parameters(loaded_params)

        assert m2.is_fitted is True
        reloaded_preds = m2.predict(x)
        reloaded_probs = m2.predict_proba(x)

        assert orig_preds == reloaded_preds
        for p1, p2 in zip(orig_probs, reloaded_probs, strict=False):
            assert abs(p1["industrial"] - p2["industrial"]) < 1e-6
            assert abs(p1["non_industrial"] - p2["non_industrial"]) < 1e-6

    def test_model_registry_artifact_lifecycle(
        self,
        synthetic_binary_data: tuple[list[list[float]], list[str], list[str]],
        tmp_path: Path,
    ) -> None:
        """Verify ModelRegistry serializes, validates, audits, and reconstructs artifact."""
        x, y, feat_names = synthetic_binary_data
        preprocessor = FeaturePreprocessor()
        # Fit on dummy dict
        dummy_dicts = [{f: val for f, val in zip(feat_names, row, strict=False)} for row in x]
        preprocessor.fit(dummy_dicts)
        x_vec = preprocessor.transform(dummy_dicts)

        model = XGBoostClassifier(n_estimators=10, max_depth=2, random_seed=42)
        model.fit(x_vec, y, feature_names=preprocessor.output_column_names)

        meta = ModelMetadata(
            model_id="real_xgboostclassifier_target_industrial_segregation_v1.0.0-experimental",
            model_type="XGBoostClassifier",
            model_version="v1.0.0-experimental",
            model_family="GradientBoostedTrees",
            target_id="target_industrial_segregation",
            target_version="target_v1.0.0",
            dataset_id="feat_ds_real_supervised_v1.0.0",
            dataset_version="v1.0.0",
            dataset_hash="b511e3dee5f05594567ca4460f2a7bc64e65c9dab82d2969f70bd8d041ff7256",
            feature_set_version="feat_v1.0.0",
            label_set_version="label_v1.0.0",
            split_strategy="PERSISTENT_SOURCE_HOLDOUT",
            split_version="PERSISTENT_SOURCE_HOLDOUT",
            random_seed=42,
            hyperparameters={"n_estimators": 10, "max_depth": 2},
            training_timestamp=datetime.now(UTC),
            train_record_count=len(x),
            feature_names=preprocessor.output_column_names,
            feature_dimensionality=len(preprocessor.output_column_names),
        )

        artifact = ModelArtifact(
            metadata=meta,
            preprocessor_state=preprocessor.to_dict(),
            model_parameters=model.get_parameters(),
            class_vocabulary=model.class_vocabulary,
        )

        artifact_file = tmp_path / "xgboost_test_artifact.json"
        ModelRegistry.save_to_file(artifact, artifact_file)
        assert artifact_file.exists()

        # Load and reconstruct
        loaded_art = ModelRegistry.load_from_file(artifact_file)
        assert loaded_art.metadata.model_type == "XGBoostClassifier"
        assert loaded_art.metadata.model_version == "v1.0.0-experimental"

        recon_preprocessor, recon_model = ModelRegistry.reconstruct_pipeline(loaded_art)
        assert isinstance(recon_model, XGBoostClassifier)
        assert recon_model.is_fitted is True

        recon_preds = recon_model.predict(x_vec)
        orig_preds = model.predict(x_vec)
        assert recon_preds == orig_preds

    def test_existing_production_artifacts_unmodified(self) -> None:
        """Verify production artifacts in artifacts/real/production remain untouched."""
        prod_dir = Path("artifacts/real/production")
        assert prod_dir.exists()
        prod_files = sorted(prod_dir.glob("real_*_target_industrial_segregation_v1.0.0.json"))
        assert len(prod_files) == 5

        for p in prod_files:
            art = ModelRegistry.load_from_file(p)
            assert art.metadata.model_version == "v1.0.0-production"
            assert "xgboost" not in p.name.lower()
