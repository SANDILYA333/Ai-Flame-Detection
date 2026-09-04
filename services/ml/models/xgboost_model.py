"""XGBoost Experimental Gradient Boosted Decision Tree Classifier.

Additive experimental implementation adhering to BaseMLModel interface for
rigorous benchmarking against existing baseline classifiers. Runs deterministically
on CPU without GPU requirements.
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import xgboost as xgb

from services.ml.models.base import BaseMLModel


class XGBoostClassifier(BaseMLModel):
    """Experimental Gradient Boosted Decision Tree model using native XGBoost."""

    def __init__(
        self,
        n_estimators: int = 50,
        max_depth: int = 3,
        learning_rate: float = 0.05,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        reg_alpha: float = 0.1,
        reg_lambda: float = 1.0,
        min_child_weight: float = 1.0,
        scale_pos_weight: float = 1.0,
        objective: str = "binary:logistic",
        eval_metric: str = "logloss",
        random_seed: int = 42,
        tree_method: str = "hist",
        device: str = "cpu",
        n_jobs: int = 1,
    ) -> None:
        super().__init__(model_name="XGBoostClassifier", random_seed=random_seed)
        self.n_estimators: int = max(1, n_estimators)
        self.max_depth: int = max(1, max_depth)
        self.learning_rate: float = float(learning_rate)
        self.subsample: float = float(subsample)
        self.colsample_bytree: float = float(colsample_bytree)
        self.reg_alpha: float = float(reg_alpha)
        self.reg_lambda: float = float(reg_lambda)
        self.min_child_weight: float = float(min_child_weight)
        self.scale_pos_weight: float = float(scale_pos_weight)
        self.objective: str = objective
        self.eval_metric: str = eval_metric
        self.tree_method: str = tree_method
        self.device: str = device
        self.n_jobs: int = n_jobs

        self.booster: xgb.Booster | None = None
        self.n_features_: int = 0
        self.feature_names_: list[str] = []
        self.feature_importances_: list[float] = []

        # Probability calibration parameters (Platt scaling / temperature scaling)
        self.calibration_a: float = 1.0
        self.calibration_b: float = 0.0
        self.is_calibrated: bool = False

    def fit(
        self,
        x_train: list[list[float]] | list[dict[str, Any]],
        y_train: list[str],
        class_vocabulary: list[str] | None = None,
        feature_names: list[str] | None = None,
    ) -> "XGBoostClassifier":
        """Fit XGBoost booster strictly on training data."""
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
            raise ValueError("Cannot train XGBoostClassifier on single class.")

        x_arr = np.array(x_train, dtype=np.float32)

        # Class mapping
        if n_classes == 2:
            # Positive class is 'industrial' if present, otherwise second alphabetically
            pos_cls = (
                "industrial"
                if "industrial" in self.class_vocabulary
                else self.class_vocabulary[1]
            )
            # Label: 1 if positive class, 0 if negative class
            y_arr = np.array(
                [1.0 if y == pos_cls else 0.0 for y in y_train],
                dtype=np.float32,
            )
            obj = "binary:logistic"
            metric = self.eval_metric or "logloss"
            params: dict[str, Any] = {
                "max_depth": self.max_depth,
                "learning_rate": self.learning_rate,
                "subsample": self.subsample,
                "colsample_bytree": self.colsample_bytree,
                "reg_alpha": self.reg_alpha,
                "reg_lambda": self.reg_lambda,
                "min_child_weight": self.min_child_weight,
                "scale_pos_weight": self.scale_pos_weight,
                "objective": obj,
                "eval_metric": metric,
                "tree_method": self.tree_method,
                "device": self.device,
                "seed": self.random_seed,
                "nthread": self.n_jobs,
            }
        else:
            class_to_idx = {c: i for i, c in enumerate(self.class_vocabulary)}
            y_arr = np.array([class_to_idx[y] for y in y_train], dtype=np.float32)
            params = {
                "max_depth": self.max_depth,
                "learning_rate": self.learning_rate,
                "subsample": self.subsample,
                "colsample_bytree": self.colsample_bytree,
                "reg_alpha": self.reg_alpha,
                "reg_lambda": self.reg_lambda,
                "min_child_weight": self.min_child_weight,
                "objective": "multi:softprob",
                "num_class": n_classes,
                "eval_metric": "mlogloss",
                "tree_method": self.tree_method,
                "device": self.device,
                "seed": self.random_seed,
                "nthread": self.n_jobs,
            }

        dtrain = xgb.DMatrix(x_arr, label=y_arr, feature_names=self.feature_names_)
        self.booster = xgb.train(params, dtrain, num_boost_round=self.n_estimators)

        # Feature importances (gain-based)
        gain_dict = self.booster.get_score(importance_type="gain")
        total_gain = sum(gain_dict.values()) if gain_dict else 0.0
        self.feature_importances_ = [
            float(gain_dict.get(fname, 0.0) / total_gain) if total_gain > 0 else 0.0
            for fname in self.feature_names_
        ]

        self.is_fitted = True
        return self

    def predict_proba(
        self,
        x_data: list[list[float]] | list[dict[str, Any]],
    ) -> list[dict[str, float]]:
        """Predict class probability distribution for given samples."""
        if not self.is_fitted or self.booster is None:
            raise ValueError("XGBoostClassifier must be fitted before predict_proba.")

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
        dtest = xgb.DMatrix(x_arr, feature_names=self.feature_names_)
        raw_preds = self.booster.predict(dtest)

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
                    # Apply Platt scaling: log-odds -> calibrated probability
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
    ) -> "XGBoostClassifier":
        """Fit post-hoc Platt scaling calibration parameters on validation partition."""
        if not self.is_fitted or self.booster is None:
            raise ValueError("Model must be fitted before calibration.")

        if len(self.class_vocabulary) != 2:
            # Multi-class Platt scaling not applied
            return self

        pos_cls = (
            "industrial"
            if "industrial" in self.class_vocabulary
            else self.class_vocabulary[1]
        )

        # Temporarily disable calibration to compute raw uncalibrated probabilities
        prev_cal = self.is_calibrated
        self.is_calibrated = False
        raw_probs = self.predict_proba(x_val)
        self.is_calibrated = prev_cal

        pos_probs = np.array([p[pos_cls] for p in raw_probs], dtype=np.float64)
        pos_probs = np.clip(pos_probs, 1e-7, 1.0 - 1e-7)
        z = np.log(pos_probs / (1.0 - pos_probs))
        z = np.clip(z, -10.0, 10.0)

        # Targets with Laplace smoothing: N+ / (N+ + 2), 1 / (N- + 2)
        n_pos = sum(1 for y in y_val if y == pos_cls)
        n_neg = len(y_val) - n_pos
        t_pos = (n_pos + 1.0) / (n_pos + 2.0)
        t_neg = 1.0 / (n_neg + 2.0)
        y_targets = np.array([t_pos if y == pos_cls else t_neg for y in y_val], dtype=np.float64)

        # Gradient descent optimization for a and b
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
        """Serialize model hyperparameters, metadata, and booster to dict."""
        booster_data: dict[str, Any] = {}
        if self.booster is not None:
            raw_bytes = self.booster.save_raw(raw_format="json")
            booster_data = json.loads(raw_bytes.decode("utf-8"))

        return {
            "n_estimators": self.n_estimators,
            "max_depth": self.max_depth,
            "learning_rate": self.learning_rate,
            "subsample": self.subsample,
            "colsample_bytree": self.colsample_bytree,
            "reg_alpha": self.reg_alpha,
            "reg_lambda": self.reg_lambda,
            "min_child_weight": self.min_child_weight,
            "scale_pos_weight": self.scale_pos_weight,
            "objective": self.objective,
            "eval_metric": self.eval_metric,
            "random_seed": self.random_seed,
            "tree_method": self.tree_method,
            "device": self.device,
            "n_jobs": self.n_jobs,
            "n_features": self.n_features_,
            "feature_names": self.feature_names_,
            "class_vocabulary": self.class_vocabulary,
            "feature_importances": self.feature_importances_,
            "calibration_a": self.calibration_a,
            "calibration_b": self.calibration_b,
            "is_calibrated": self.is_calibrated,
            "booster_data": booster_data,
        }

    def set_parameters(self, params: dict[str, Any]) -> None:
        """Restore model from serialized parameter dictionary."""
        self.n_estimators = int(params.get("n_estimators", 50))
        self.max_depth = int(params.get("max_depth", 3))
        self.learning_rate = float(params.get("learning_rate", 0.05))
        self.subsample = float(params.get("subsample", 0.8))
        self.colsample_bytree = float(params.get("colsample_bytree", 0.8))
        self.reg_alpha = float(params.get("reg_alpha", 0.1))
        self.reg_lambda = float(params.get("reg_lambda", 1.0))
        self.min_child_weight = float(params.get("min_child_weight", 1.0))
        self.scale_pos_weight = float(params.get("scale_pos_weight", 1.0))
        self.objective = str(params.get("objective", "binary:logistic"))
        self.eval_metric = str(params.get("eval_metric", "logloss"))
        self.random_seed = int(params.get("random_seed", 42))
        self.tree_method = str(params.get("tree_method", "hist"))
        self.device = str(params.get("device", "cpu"))
        self.n_jobs = int(params.get("n_jobs", 1))

        self.n_features_ = int(params.get("n_features", 0))
        self.feature_names_ = list(params.get("feature_names", []))
        self.class_vocabulary = list(params.get("class_vocabulary", []))
        self.feature_importances_ = list(params.get("feature_importances", []))
        self.calibration_a = float(params.get("calibration_a", 1.0))
        self.calibration_b = float(params.get("calibration_b", 0.0))
        self.is_calibrated = bool(params.get("is_calibrated", False))

        booster_data = params.get("booster_data")
        if booster_data:
            json_bytes = json.dumps(booster_data).encode("utf-8")
            self.booster = xgb.Booster()
            self.booster.load_model(bytearray(json_bytes))
            self.is_fitted = True
        else:
            self.booster = None
            self.is_fitted = False
