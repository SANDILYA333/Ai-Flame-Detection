"""Trivial non-ML baseline: empirical prior / majority class classifier."""

from collections import Counter
from typing import Any

from services.ml.models.base import BaseMLModel


class MajorityClassClassifier(BaseMLModel):
    """Trivial baseline predicting empirical class prior distribution from TRAIN."""

    def __init__(self, random_seed: int = 42) -> None:
        super().__init__(model_name="MajorityClassClassifier", random_seed=random_seed)
        self.majority_class: str = "unknown"
        self.class_priors: dict[str, float] = {}

    def fit(
        self,
        x_train: list[list[float]] | list[dict[str, Any]],
        y_train: list[str],
        class_vocabulary: list[str] | None = None,
    ) -> "MajorityClassClassifier":
        """Fit empirical class prior distribution on training data."""
        if not y_train:
            raise ValueError("y_train cannot be empty for MajorityClassClassifier.")

        self.class_vocabulary = sorted(set(class_vocabulary or y_train))
        counts = Counter(y_train)
        total = len(y_train)

        self.class_priors = {
            cls_name: float(counts.get(cls_name, 0) / total)
            for cls_name in self.class_vocabulary
        }

        # Select majority class (tie-broken deterministically)
        most_common = counts.most_common()
        if most_common:
            self.majority_class = most_common[0][0]
        else:
            self.majority_class = self.class_vocabulary[0]

        self.is_fitted = True
        return self

    def predict(
        self,
        x_data: list[list[float]] | list[dict[str, Any]],
    ) -> list[str]:
        """Predict the majority class for every sample."""
        if not self.is_fitted:
            raise ValueError("MajorityClassClassifier must be fitted before predict.")
        return [self.majority_class for _ in range(len(x_data))]

    def predict_proba(
        self,
        x_data: list[list[float]] | list[dict[str, Any]],
    ) -> list[dict[str, float]]:
        """Return the training class prior distribution for every sample."""
        if not self.is_fitted:
            raise ValueError(
                "MajorityClassClassifier must be fitted before predict_proba."
            )
        return [dict(self.class_priors) for _ in range(len(x_data))]

    def get_parameters(self) -> dict[str, Any]:
        return {
            "majority_class": self.majority_class,
            "class_priors": self.class_priors,
            "class_vocabulary": self.class_vocabulary,
        }

    def set_parameters(self, params: dict[str, Any]) -> None:
        self.majority_class = str(params.get("majority_class", "unknown"))
        self.class_priors = dict(params.get("class_priors", {}))
        self.class_vocabulary = list(params.get("class_vocabulary", []))
        self.is_fitted = True
