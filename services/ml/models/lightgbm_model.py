"""LightGBM Experimental Gradient Boosted Decision Tree Classifier.

Additive experimental implementation adhering to BaseMLModel interface for
rigorous benchmarking against existing baseline classifiers. Runs deterministically
on CPU without GPU requirements using native LightGBM APIs.
"""

from __future__ import annotations

from typing import Any

import lightgbm as lgb
import numpy as np

from services.ml.models.base import BaseMLModel


class LightGBMClassifier(BaseMLModel):
    """Experimental Gradient Boosted Decision Tree model using native LightGBM."""

    def __init__(
        self,
        n_estimators: int = 50,
        num_leaves: int = 15,
        max_depth: int = 3,
        learning_rate: float = 0.05,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        min_child_samples: int = 20,
        reg_alpha: float = 0.1,
        reg_lambda: float = 1.0,
        scale_pos_weight: float = 1.0,
        random_seed: int = 42,
        n_jobs: int = 1,
    ) -> None:
        super().__init__(model_name="LightGBMClassifier", random_seed=random_seed)
        self.n_estimators: int = max(1, n_estimators)
        self.num_leaves: int = max(2, num_leaves)
        self.max_depth: int = max(-1, max_depth)
        self.learning_rate: float = float(learning_rate)
        self.subsample: float = float(subsample)
        self.colsample_bytree: float = float(colsample_bytree)
        self.min_child_samples: int = max(1, min_child_samples)
        self.reg_alpha: float = float(reg_alpha)
        self.reg_lambda: float = float(reg_lambda)
        self.scale_pos_weight: float = float(scale_pos_weight)
        self.n_jobs: int = n_jobs

        self.booster: lgb.Booster | None = None
        self.n_features_: int = 0
        self.feature_names_: list[str] = []
        self.feature_importances_: list[float] = []

        # Probability calibration parameters (Platt scaling)
        self.calibration_a: float = 1.0
        self.calibration_b: float = 0.0
        self.is_calibrated: bool = False

    def fit(
        self,
        x_train: list[list[float]] | list[dict[str, Any]],
        y_train: list[str],
        class_vocabulary: list[str] | None = None,
        feature_names: list[str] | None = None,
    ) -> "LightGBMClassifier":
        """Fit LightGBM booster strictly on training data."""
        if not x_train or not y_train:
            raise ValueError("x_train and y_train cannot be empty.")

        if isinstance(x_train[0], dict):
            raise TypeError("Expected preprocessed 2D float matrix.")

        if len(x_train) != len(y_train):
            raise ValueError(
                f"Length mismatch: len(x_train)={len(x_train)} != len(y_train)={len(y_train)}."
            )

        self.class_vocabulary = sorted(set(class_vocabulary or y_train))
        self.n_features_ = len(x_train[0])
        self.feature_names_ = (
            list(feature_names)
            if feature_names and len(feature_names) == self.n_features_
            else [f"f_{i}" for i in range(self.n_features_)]
        )

        n_classes = len(self.class_vocabulary)
        if n_classes < 2:
            raise ValueError("Cannot train LightGBMClassifier on single class.")

        x_arr = np.array(x_train, dtype=np.float32)

        if n_classes == 2:
            pos_cls = (
                "industrial"
                if "industrial" in self.class_vocabulary
                else self.class_vocabulary[1]
            )
            y_arr = np.array(
                [1.0 if y == pos_cls else 0.0 for y in y_train],
                dtype=np.float32,
            )
            params: dict[str, Any] = {
                "objective": "binary",
                "metric": "binary_logloss",
                "boosting_type": "gbdt",
                "learning_rate": self.learning_rate,
                "num_leaves": self.num_leaves,
                "max_depth": self.max_depth,
                "min_child_samples": self.min_child_samples,
                "subsample": self.subsample,
                "subsample_freq": 1 if self.subsample < 1.0 else 0,
                "colsample_bytree": self.colsample_bytree,
                "reg_alpha": self.reg_alpha,
                "reg_lambda": self.reg_lambda,
                "scale_pos_weight": self.scale_pos_weight,
                "device": "cpu",
                "deterministic": True,
                "seed": self.random_seed,
                "verbose": -1,
                "n_jobs": self.n_jobs,
            }
        else:
            class_to_idx = {c: i for i, c in enumerate(self.class_vocabulary)}
            y_arr = np.array([class_to_idx[y] for y in y_train], dtype=np.float32)
            params = {
                "objective": "multiclass",
                "num_class": n_classes,
                "metric": "multi_logloss",
                "boosting_type": "gbdt",
                "learning_rate": self.learning_rate,
                "num_leaves": self.num_leaves,
                "max_depth": self.max_depth,
                "min_child_samples": self.min_child_samples,
                "subsample": self.subsample,
                "subsample_freq": 1 if self.subsample < 1.0 else 0,
                "colsample_bytree": self.colsample_bytree,
                "reg_alpha": self.reg_alpha,
                "reg_lambda": self.reg_lambda,
                "device": "cpu",
                "deterministic": True,
                "seed": self.random_seed,
                "verbose": -1,
                "n_jobs": self.n_jobs,
            }

        train_data = lgb.Dataset(
            x_arr,
            label=y_arr,
            feature_name=self.feature_names_,
            free_raw_data=False,
        )
        self.booster = lgb.train(
            params,
            train_data,
            num_boost_round=self.n_estimators,
        )

        # Gain-based feature importances
        raw_importances = self.booster.feature_importance(importance_type="gain")
        total_gain = float(np.sum(raw_importances))
        self.feature_importances_ = [
            float(val / total_gain) if total_gain > 0 else 0.0
            for val in raw_importances
        ]

        self.is_fitted = True
        return self

    def predict_proba(
        self,
        x_data: list[list[float]] | list[dict[str, Any]],
    ) -> list[dict[str, float]]:
        """Predict class probability distribution for given samples."""
        if not self.is_fitted or self.booster is None:
            raise ValueError("LightGBMClassifier must be fitted before predict_proba.")

        if not x_data:
            return []

        if isinstance(x_data[0], dict):
            raise TypeError("Expected preprocessed 2D float matrix.")

        if len(x_data[0]) != self.n_features_:
            raise ValueError(
                f"Feature dimension mismatch: expected {self.n_features_} "
                f"features, got {len(x_data[0])}."
            )

        x_arr = np.array(x_data, dtype=np.float32)
        raw_preds = self.booster.predict(x_arr)

        n_classes = len(self.class_vocabulary)
        probs: list[dict[str, float]] = []

        if n_classes == 2:
            pos_cls = (
                "industrial"
                if "industrial" in self.class_vocabulary
                else self.class_vocabulary[1]
            )
            neg_cls = [c for c in self.class_vocabulary if c != pos_cls][0]

            for p in raw_preds:
                p_raw = float(max(1e-7, min(1.0 - 1e-7, float(p))))
                if self.is_calibrated:
                    # Apply Platt scaling
                    z = float(np.log(p_raw / (1.0 - p_raw)))
                    z = float(np.clip(z, -10.0, 10.0))
                    p_pos = float(1.0 / (1.0 + np.exp(-(self.calibration_a * z + self.calibration_b))))
                else:
                    p_pos = p_raw

                p_pos = float(max(0.0, min(1.0, p_pos)))
                p_neg = float(max(0.0, min(1.0, 1.0 - p_pos)))
                total = p_pos + p_neg
                if total > 0:
                    p_pos /= total
                    p_neg /= total
                probs.append({pos_cls: p_pos, neg_cls: p_neg})
        else:
            for row in raw_preds:
                row_floats = [float(v) for v in row]
                total = sum(row_floats)
                if total > 0:
                    row_floats = [v / total for v in row_floats]
                prob_dict = {
                    cls_name: row_floats[idx]
                    for idx, cls_name in enumerate(self.class_vocabulary)
                }
                probs.append(prob_dict)

        return probs

    def predict(
        self,
        x_data: list[list[float]] | list[dict[str, Any]],
        threshold: float = 0.5,
    ) -> list[str]:
        """Predict class labels for given samples using decision threshold."""
        probs = self.predict_proba(x_data)
        predictions: list[str] = []

        if len(self.class_vocabulary) == 2:
            pos_cls = (
                "industrial"
                if "industrial" in self.class_vocabulary
                else self.class_vocabulary[1]
            )
            neg_cls = [c for c in self.class_vocabulary if c != pos_cls][0]
            for p_dict in probs:
                if p_dict.get(pos_cls, 0.0) >= threshold:
                    predictions.append(pos_cls)
                else:
                    predictions.append(neg_cls)
        else:
            for p_dict in probs:
                best_cls = max(self.class_vocabulary, key=lambda k: p_dict.get(k, 0.0))
                predictions.append(best_cls)

        return predictions

    def calibrate(
        self,
        x_val: list[list[float]] | list[dict[str, Any]],
        y_val: list[str],
        max_iter: int = 100,
        learning_rate: float = 0.05,
    ) -> "LightGBMClassifier":
        """Fit post-hoc Platt scaling calibration parameters on validation partition."""
        if not self.is_fitted or self.booster is None:
            raise ValueError("Model must be fitted before calibration.")

        if len(self.class_vocabulary) != 2:
            return self

        pos_cls = (
            "industrial"
            if "industrial" in self.class_vocabulary
            else self.class_vocabulary[1]
        )

        prev_cal = self.is_calibrated
        self.is_calibrated = False
        raw_probs = self.predict_proba(x_val)
        self.is_calibrated = prev_cal

        pos_probs = np.array([p[pos_cls] for p in raw_probs], dtype=np.float64)
        pos_probs = np.clip(pos_probs, 1e-7, 1.0 - 1e-7)
        z = np.log(pos_probs / (1.0 - pos_probs))
        z = np.clip(z, -10.0, 10.0)

        n_pos = sum(1 for y in y_val if y == pos_cls)
        n_neg = len(y_val) - n_pos
        t_pos = (n_pos + 1.0) / (n_pos + 2.0)
        t_neg = 1.0 / (n_neg + 2.0)
        y_targets = np.array([t_pos if y == pos_cls else t_neg for y in y_val], dtype=np.float64)

        a, b = 1.0, 0.0
        n_samples = len(y_val)
        for _ in range(max_iter):
            p_cal = 1.0 / (1.0 + np.exp(-(a * z + b)))
            p_cal = np.clip(p_cal, 1e-7, 1.0 - 1e-7)
            err = p_cal - y_targets
            grad_a = np.sum(err * z) / n_samples
            grad_b = np.sum(err) / n_samples
            a -= learning_rate * grad_a
            b -= learning_rate * grad_b

        self.calibration_a = float(a)
        self.calibration_b = float(b)
        self.is_calibrated = True
        return self

    def get_feature_importances(
        self, feature_names: list[str] | None = None
    ) -> dict[str, float]:
        """Return normalized gain feature importances."""
        if not self.is_fitted or not self.feature_importances_:
            return {}

        names = feature_names or self.feature_names_
        return {
            names[j]: float(self.feature_importances_[j])
            for j in range(min(len(names), len(self.feature_importances_)))
        }

    def get_parameters(self) -> dict[str, Any]:
        """Serialize model hyperparameters, metadata, and booster string to dict."""
        booster_str = ""
        if self.booster is not None:
            booster_str = self.booster.model_to_string()

        return {
            "n_estimators": self.n_estimators,
            "num_leaves": self.num_leaves,
            "max_depth": self.max_depth,
            "learning_rate": self.learning_rate,
            "subsample": self.subsample,
            "colsample_bytree": self.colsample_bytree,
            "min_child_samples": self.min_child_samples,
            "reg_alpha": self.reg_alpha,
            "reg_lambda": self.reg_lambda,
            "scale_pos_weight": self.scale_pos_weight,
            "random_seed": self.random_seed,
            "n_jobs": self.n_jobs,
            "n_features": self.n_features_,
            "feature_names": self.feature_names_,
            "class_vocabulary": self.class_vocabulary,
            "feature_importances": self.feature_importances_,
            "calibration_a": self.calibration_a,
            "calibration_b": self.calibration_b,
            "is_calibrated": self.is_calibrated,
            "booster_string": booster_str,
        }

    def set_parameters(self, params: dict[str, Any]) -> None:
        """Restore model from serialized parameter dictionary."""
        self.n_estimators = int(params.get("n_estimators", 50))
        self.num_leaves = int(params.get("num_leaves", 15))
        self.max_depth = int(params.get("max_depth", 3))
        self.learning_rate = float(params.get("learning_rate", 0.05))
        self.subsample = float(params.get("subsample", 0.8))
        self.colsample_bytree = float(params.get("colsample_bytree", 0.8))
        self.min_child_samples = int(params.get("min_child_samples", 20))
        self.reg_alpha = float(params.get("reg_alpha", 0.1))
        self.reg_lambda = float(params.get("reg_lambda", 1.0))
        self.scale_pos_weight = float(params.get("scale_pos_weight", 1.0))
        self.random_seed = int(params.get("random_seed", 42))
        self.n_jobs = int(params.get("n_jobs", 1))

        self.n_features_ = int(params.get("n_features", 0))
        self.feature_names_ = list(params.get("feature_names", []))
        self.class_vocabulary = list(params.get("class_vocabulary", []))
        self.feature_importances_ = list(params.get("feature_importances", []))
        self.calibration_a = float(params.get("calibration_a", 1.0))
        self.calibration_b = float(params.get("calibration_b", 0.0))
        self.is_calibrated = bool(params.get("is_calibrated", False))

        booster_str = params.get("booster_string")
        if booster_str:
            self.booster = lgb.Booster(model_str=booster_str)
            self.is_fitted = True
        else:
            self.booster = None
            self.is_fitted = False
