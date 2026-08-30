"""Multinomial Softmax Logistic Regression Baseline Classifier (B3 Linear).

Implements deterministic multi-class gradient descent with L2 regularization,
feature coefficient interpretability, and class-probability outputs.
"""

import math
import random
from typing import Any

from services.ml.models.base import BaseMLModel


class LogisticRegressionClassifier(BaseMLModel):
    """B3 Baseline: Multi-class Multinomial Softmax Logistic Regression with L2."""

    def __init__(
        self,
        learning_rate: float = 0.05,
        max_epochs: int = 150,
        l2_lambda: float = 0.01,
        random_seed: int = 42,
    ) -> None:
        super().__init__(
            model_name="LogisticRegressionClassifier", random_seed=random_seed
        )
        self.learning_rate: float = learning_rate
        self.max_epochs: int = max_epochs
        self.l2_lambda: float = l2_lambda

        # Weights: [n_classes][n_features], Biases: [n_classes]
        self.weights: list[list[float]] = []
        self.biases: list[float] = []
        self.feature_names: list[str] = []
        self.training_loss_history: list[float] = []

    def fit(
        self,
        x_train: list[list[float]] | list[dict[str, Any]],
        y_train: list[str],
        class_vocabulary: list[str] | None = None,
    ) -> "LogisticRegressionClassifier":
        """Fit weights using deterministic batch gradient descent on TRAIN only.

        Args:
            x_train: 2D float feature matrix [n_samples, n_features].
            y_train: Target class strings [n_samples].
            class_vocabulary: Optional class list.

        Returns:
            self: Fitted model.
        """
        if not x_train or not y_train:
            raise ValueError("x_train and y_train cannot be empty.")

        if isinstance(x_train[0], dict):
            raise TypeError(
                "LogisticRegressionClassifier requires preprocessed 2D float matrix."
            )

        n_samples = len(x_train)
        n_features = len(x_train[0])

        self.class_vocabulary = sorted(set(class_vocabulary or y_train))
        n_classes = len(self.class_vocabulary)
        class_to_idx = {c: i for i, c in enumerate(self.class_vocabulary)}

        # Initialize deterministic weights
        rng = random.Random(self.random_seed)
        self.weights = [
            [(rng.random() - 0.5) * 0.01 for _ in range(n_features)]
            for _ in range(n_classes)
        ]
        self.biases = [0.0 for _ in range(n_classes)]

        # Target 1-hot matrix
        y_indices = [class_to_idx[y] for y in y_train]

        self.training_loss_history = []

        # Gradient descent optimization
        for _ in range(self.max_epochs):
            grad_w = [[0.0 for _ in range(n_features)] for _ in range(n_classes)]
            grad_b = [0.0 for _ in range(n_classes)]
            total_loss = 0.0

            for i in range(n_samples):
                x_i = x_train[i]
                true_k = y_indices[i]

                # Compute logits: z_k = w_k * x + b_k
                logits = [
                    sum(w * x for w, x in zip(self.weights[k], x_i, strict=False))
                    + self.biases[k]
                    for k in range(n_classes)
                ]

                # Stable softmax
                max_logit = max(logits)
                exp_logits = [math.exp(z - max_logit) for z in logits]
                sum_exp = sum(exp_logits)
                probs = [e / sum_exp for e in exp_logits]

                # Loss: -log(p_true)
                p_true = max(probs[true_k], 1e-15)
                total_loss -= math.log(p_true)

                # Gradient: p_k - y_k
                for k in range(n_classes):
                    diff = probs[k] - (1.0 if k == true_k else 0.0)
                    grad_b[k] += diff
                    for j in range(n_features):
                        grad_w[k][j] += diff * x_i[j]

            # Average gradients and add L2 regularization
            for k in range(n_classes):
                self.biases[k] -= self.learning_rate * (grad_b[k] / n_samples)
                for j in range(n_features):
                    gw = (grad_w[k][j] / n_samples) + (
                        self.l2_lambda * self.weights[k][j]
                    )
                    self.weights[k][j] -= self.learning_rate * gw

            self.training_loss_history.append(total_loss / n_samples)

        self.is_fitted = True
        return self

    def predict_proba(
        self,
        x_data: list[list[float]] | list[dict[str, Any]],
    ) -> list[dict[str, float]]:
        """Compute Softmax probabilities for input samples."""
        if not self.is_fitted:
            raise ValueError(
                "LogisticRegressionClassifier must be fitted before predict_proba."
            )

        if not x_data:
            return []

        if isinstance(x_data[0], dict):
            raise TypeError("Expected preprocessed 2D float matrix.")

        if self.weights and len(x_data[0]) != len(self.weights[0]):
            raise ValueError(
                f"Feature dimension mismatch: expected "
                f"{len(self.weights[0])} features, got {len(x_data[0])}."
            )

        n_classes = len(self.class_vocabulary)
        probs_list: list[dict[str, float]] = []

        for x_i in x_data:
            logits = [
                sum(w * x for w, x in zip(self.weights[k], x_i, strict=False))
                + self.biases[k]
                for k in range(n_classes)
            ]
            max_logit = max(logits)
            exp_logits = [math.exp(z - max_logit) for z in logits]
            sum_exp = sum(exp_logits)

            row_probs = {
                self.class_vocabulary[k]: float(exp_logits[k] / sum_exp)
                for k in range(n_classes)
            }
            probs_list.append(row_probs)

        return probs_list

    def predict(
        self,
        x_data: list[list[float]] | list[dict[str, Any]],
    ) -> list[str]:
        """Predict class with highest Softmax probability."""
        probs = self.predict_proba(x_data)
        predictions: list[str] = []

        for p_dict in probs:
            best_cls = max(p_dict.keys(), key=lambda k: p_dict[k])
            predictions.append(best_cls)

        return predictions

    def get_coefficients_by_class(
        self, feature_names: list[str] | None = None
    ) -> dict[str, dict[str, float]]:
        """Return raw linear coefficients per class for each feature."""
        if not self.is_fitted or not self.weights:
            return {}

        n_classes = len(self.class_vocabulary)
        n_features = len(self.weights[0])
        names = feature_names or [f"f_{i}" for i in range(n_features)]

        coefs: dict[str, dict[str, float]] = {}
        for k in range(n_classes):
            cls_name = self.class_vocabulary[k]
            coefs[cls_name] = {}
            for j in range(min(n_features, len(names))):
                coefs[cls_name][names[j]] = float(self.weights[k][j])

        return coefs

    def get_feature_importances(
        self, feature_names: list[str] | None = None
    ) -> dict[str, float]:
        """Compute aggregate feature importances (mean absolute weight)."""
        if not self.is_fitted or not self.weights:
            return {}

        n_classes = len(self.class_vocabulary)
        n_features = len(self.weights[0])
        names = feature_names or [f"f_{i}" for i in range(n_features)]

        importances: dict[str, float] = {}
        for j in range(min(n_features, len(names))):
            avg_magnitude = (
                sum(abs(self.weights[k][j]) for k in range(n_classes)) / n_classes
            )
            importances[names[j]] = float(avg_magnitude)

        return importances

    def get_parameters(self) -> dict[str, Any]:
        return {
            "learning_rate": self.learning_rate,
            "max_epochs": self.max_epochs,
            "l2_lambda": self.l2_lambda,
            "weights": self.weights,
            "biases": self.biases,
            "class_vocabulary": self.class_vocabulary,
            "training_loss_history": self.training_loss_history,
        }

    def set_parameters(self, params: dict[str, Any]) -> None:
        self.learning_rate = float(params.get("learning_rate", 0.05))
        self.max_epochs = int(params.get("max_epochs", 150))
        self.l2_lambda = float(params.get("l2_lambda", 0.01))
        self.weights = list(params.get("weights", []))
        self.biases = list(params.get("biases", []))
        self.class_vocabulary = list(params.get("class_vocabulary", []))
        self.training_loss_history = list(params.get("training_loss_history", []))
        self.is_fitted = True
