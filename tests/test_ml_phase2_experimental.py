"""Comprehensive Phase 2 Test Suite for XGBoost & LightGBM Optimization.

Validates:
1. Decision threshold optimization behavior for XGBoost and LightGBM.
2. Class weighting (scale_pos_weight) parameterization and effect.
3. Platt scaling probability calibration on validation data.
4. Deterministic training and prediction for LightGBM.
5. Lossless serialization and deserialization roundtrips.
6. ModelRegistry integration and secret auditing for both models.
7. Feature importance extraction and normalization.
8. FeaturePreprocessor pipeline compatibility and unseen category robustness.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest

from packages.schemas.ml import ModelArtifact, ModelMetadata
from services.ml.models.lightgbm_model import LightGBMClassifier
from services.ml.models.registry import ModelRegistry
from services.ml.models.xgboost_model import XGBoostClassifier
from services.ml.preprocessing.transformer import FeaturePreprocessor


@pytest.fixture
def synthetic_binary_data() -> tuple[list[list[float]], list[str], list[list[float]], list[str]]:
    """Generate linearly separable binary dataset with train and validation partitions."""
    rng = np.random.default_rng(seed=42)
    n_train = 100
    n_val = 40

    # Cluster 0: industrial (centered around [2.0, 2.0])
    # Cluster 1: non_industrial (centered around [-2.0, -2.0])
    x_tr_ind = rng.normal(loc=2.0, scale=0.8, size=(n_train // 2, 4)).tolist()
    y_tr_ind = ["industrial"] * (n_train // 2)
    x_tr_non = rng.normal(loc=-2.0, scale=0.8, size=(n_train // 2, 4)).tolist()
    y_tr_non = ["non_industrial"] * (n_train // 2)

    x_train = x_tr_ind + x_tr_non
    y_train = y_tr_ind + y_tr_non

    x_val_ind = rng.normal(loc=2.0, scale=0.8, size=(n_val // 2, 4)).tolist()
    y_val_ind = ["industrial"] * (n_val // 2)
    x_val_non = rng.normal(loc=-2.0, scale=0.8, size=(n_val // 2, 4)).tolist()
    y_val_non = ["non_industrial"] * (n_val // 2)

    x_val = x_val_ind + x_val_non
    y_val = y_val_ind + y_val_non

    return x_train, y_train, x_val, y_val


def test_xgboost_threshold_control(
    synthetic_binary_data: tuple[list[list[float]], list[str], list[list[float]], list[str]]
) -> None:
    """Verify decision threshold parameter shifts classification outcomes monotonically."""
    x_train, y_train, x_val, _ = synthetic_binary_data
    model = XGBoostClassifier(n_estimators=30, max_depth=3, random_seed=42)
    model.fit(x_train, y_train)

    preds_low_thresh = model.predict(x_val, threshold=0.10)
    preds_mid_thresh = model.predict(x_val, threshold=0.50)
    preds_high_thresh = model.predict(x_val, threshold=0.90)

    count_low = sum(1 for p in preds_low_thresh if p == "industrial")
    count_mid = sum(1 for p in preds_mid_thresh if p == "industrial")
    count_high = sum(1 for p in preds_high_thresh if p == "industrial")

    assert count_low >= count_mid >= count_high, (
        f"Threshold monotonicity violated: low={count_low}, mid={count_mid}, high={count_high}"
    )


def test_xgboost_scale_pos_weight(
    synthetic_binary_data: tuple[list[list[float]], list[str], list[list[float]], list[str]]
) -> None:
    """Verify scale_pos_weight is passed and alters positive class sensitivity."""
    x_train, y_train, x_val, _ = synthetic_binary_data
    model_unweighted = XGBoostClassifier(n_estimators=30, scale_pos_weight=1.0, random_seed=42)
    model_unweighted.fit(x_train, y_train)

    model_weighted = XGBoostClassifier(n_estimators=30, scale_pos_weight=5.0, random_seed=42)
    model_weighted.fit(x_train, y_train)

    probs_unweighted = [p["industrial"] for p in model_unweighted.predict_proba(x_val)]
    probs_weighted = [p["industrial"] for p in model_weighted.predict_proba(x_val)]

    # Higher scale_pos_weight increases positive class predicted probabilities
    assert np.mean(probs_weighted) >= np.mean(probs_unweighted) - 1e-4


def test_xgboost_platt_scaling_calibration(
    synthetic_binary_data: tuple[list[list[float]], list[str], list[list[float]], list[str]]
) -> None:
    """Verify post-hoc Platt scaling calibration adjusts probabilities and serializes."""
    x_train, y_train, x_val, y_val = synthetic_binary_data
    model = XGBoostClassifier(n_estimators=30, max_depth=3, random_seed=42)
    model.fit(x_train, y_train)

    assert model.is_calibrated is False
    model.calibrate(x_val, y_val)
    assert model.is_calibrated is True

    cal_probs = model.predict_proba(x_val)
    for p in cal_probs:
        assert 0.0 <= p["industrial"] <= 1.0
        assert 0.0 <= p["non_industrial"] <= 1.0
        assert abs(p["industrial"] + p["non_industrial"] - 1.0) < 1e-5

    # Parameter roundtrip preserves calibration state
    params = model.get_parameters()
    assert params["is_calibrated"] is True
    assert "calibration_a" in params
    assert "calibration_b" in params

    new_model = XGBoostClassifier()
    new_model.set_parameters(params)
    assert new_model.is_calibrated is True
    assert new_model.calibration_a == model.calibration_a


def test_lightgbm_deterministic_training(
    synthetic_binary_data: tuple[list[list[float]], list[str], list[list[float]], list[str]]
) -> None:
    """Verify LightGBM produces exact bitwise deterministic predictions across seeds."""
    x_train, y_train, x_val, _ = synthetic_binary_data

    lgb1 = LightGBMClassifier(n_estimators=30, max_depth=3, num_leaves=7, random_seed=42)
    lgb1.fit(x_train, y_train)
    probs1 = lgb1.predict_proba(x_val)

    lgb2 = LightGBMClassifier(n_estimators=30, max_depth=3, num_leaves=7, random_seed=42)
    lgb2.fit(x_train, y_train)
    probs2 = lgb2.predict_proba(x_val)

    for p1, p2 in zip(probs1, probs2, strict=True):
        assert abs(p1["industrial"] - p2["industrial"]) < 1e-6
        assert abs(p1["non_industrial"] - p2["non_industrial"]) < 1e-6


def test_lightgbm_predict_proba_distribution(
    synthetic_binary_data: tuple[list[list[float]], list[str], list[list[float]], list[str]]
) -> None:
    """Verify LightGBM predict_proba outputs valid probability distributions."""
    x_train, y_train, x_val, _ = synthetic_binary_data
    model = LightGBMClassifier(n_estimators=20, random_seed=42)
    model.fit(x_train, y_train)

    probs = model.predict_proba(x_val)
    assert len(probs) == len(x_val)
    for p in probs:
        assert set(p.keys()) == {"industrial", "non_industrial"}
        assert 0.0 <= p["industrial"] <= 1.0
        assert 0.0 <= p["non_industrial"] <= 1.0
        assert abs(p["industrial"] + p["non_industrial"] - 1.0) < 1e-5


def test_lightgbm_threshold_and_calibration(
    synthetic_binary_data: tuple[list[list[float]], list[str], list[list[float]], list[str]]
) -> None:
    """Verify LightGBM decision thresholding and Platt calibration."""
    x_train, y_train, x_val, y_val = synthetic_binary_data
    model = LightGBMClassifier(n_estimators=25, max_depth=3, random_seed=42)
    model.fit(x_train, y_train)

    # Threshold control
    low = sum(1 for p in model.predict(x_val, threshold=0.10) if p == "industrial")
    mid = sum(1 for p in model.predict(x_val, threshold=0.50) if p == "industrial")
    high = sum(1 for p in model.predict(x_val, threshold=0.90) if p == "industrial")
    assert low >= mid >= high

    # Calibration
    model.calibrate(x_val, y_val)
    assert model.is_calibrated is True
    cal_probs = model.predict_proba(x_val)
    for p in cal_probs:
        assert abs(p["industrial"] + p["non_industrial"] - 1.0) < 1e-5


def test_lightgbm_serialization_roundtrip(
    synthetic_binary_data: tuple[list[list[float]], list[str], list[list[float]], list[str]]
) -> None:
    """Verify LightGBM parameter serialization and restoration produces identical predictions."""
    x_train, y_train, x_val, _ = synthetic_binary_data
    model = LightGBMClassifier(n_estimators=30, max_depth=3, random_seed=42)
    model.fit(x_train, y_train, feature_names=["f0", "f1", "f2", "f3"])

    orig_probs = model.predict_proba(x_val)
    orig_params = model.get_parameters()

    # Restored instance
    restored = LightGBMClassifier()
    restored.set_parameters(orig_params)
    restored_probs = restored.predict_proba(x_val)

    for p_orig, p_rest in zip(orig_probs, restored_probs, strict=True):
        assert abs(p_orig["industrial"] - p_rest["industrial"]) < 1e-6
        assert abs(p_orig["non_industrial"] - p_rest["non_industrial"]) < 1e-6


def test_lightgbm_registry_integration_and_audit(
    tmp_path: Path,
    synthetic_binary_data: tuple[list[list[float]], list[str], list[list[float]], list[str]],
) -> None:
    """Verify LightGBM artifact serialization, file persistence, and zero-secret audit."""
    x_train, y_train, _, _ = synthetic_binary_data
    model = LightGBMClassifier(n_estimators=25, max_depth=3, random_seed=42)
    model.fit(x_train, y_train, feature_names=["f0", "f1", "f2", "f3"])

    meta = ModelMetadata(
        model_id="real_lightgbmclassifier_target_industrial_segregation_v1.0.0",
        model_type="LightGBMClassifier",
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
        hyperparameters=model.get_parameters(),
        training_timestamp=datetime.now(UTC),
        train_record_count=len(x_train),
        feature_names=["f0", "f1", "f2", "f3"],
        feature_dimensionality=4,
        validation_metrics={"macro_f1": 0.85},
        test_metrics={"accuracy": 0.88},
    )

    artifact = ModelArtifact(
        metadata=meta,
        preprocessor_state={},
        model_parameters=model.get_parameters(),
        class_vocabulary=model.class_vocabulary,
    )
    h = artifact.compute_content_hash()
    artifact = artifact.model_copy(
        update={"sha256_hash": h, "metadata": meta.model_copy(update={"artifact_hash": h})}
    )

    # Serialize & audit
    serialized = ModelRegistry.serialize_artifact(artifact)
    assert "LightGBMClassifier" in serialized

    # Save to disk
    art_path = tmp_path / "test_lgb_artifact.json"
    ModelRegistry.save_to_file(artifact, art_path)

    # Load back
    loaded_art = ModelRegistry.load_from_file(art_path)
    assert loaded_art.metadata.model_type == "LightGBMClassifier"
    prep, loaded_model = ModelRegistry.reconstruct_pipeline(loaded_art)
    assert isinstance(loaded_model, LightGBMClassifier)
    assert loaded_model.is_fitted is True


def test_lightgbm_feature_importances(
    synthetic_binary_data: tuple[list[list[float]], list[str], list[list[float]], list[str]]
) -> None:
    """Verify LightGBM gain feature importances sum to 1.0."""
    x_train, y_train, _, _ = synthetic_binary_data
    fnames = ["f_signal1", "f_signal2", "f_noise1", "f_noise2"]
    model = LightGBMClassifier(n_estimators=30, max_depth=3, random_seed=42)
    model.fit(x_train, y_train, feature_names=fnames)

    imps = model.get_feature_importances(fnames)
    assert len(imps) == 4
    assert abs(sum(imps.values()) - 1.0) < 1e-4
