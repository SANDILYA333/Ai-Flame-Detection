"""Abstract base interface for ML models and baselines."""

from abc import ABC, abstractmethod
from typing import Any


class BaseMLModel(ABC):
    """Abstract base class for all ML baseline models and classifiers."""

    def __init__(self, model_name: str, random_seed: int = 42) -> None:
        self.model_name: str = model_name
        self.random_seed: int = random_seed
        self.is_fitted: bool = False
        self.class_vocabulary: list[str] = []

    @abstractmethod
    def fit(
        self,
        x_train: list[list[float]] | list[dict[str, Any]],
        y_train: list[str],
        class_vocabulary: list[str] | None = None,
    ) -> "BaseMLModel":
        """Fit the model strictly on training data."""

    @abstractmethod
    def predict(
        self,
        x_data: list[list[float]] | list[dict[str, Any]],
    ) -> list[str]:
        """Predict class labels for given samples."""

    @abstractmethod
    def predict_proba(
        self,
        x_data: list[list[float]] | list[dict[str, Any]],
    ) -> list[dict[str, float]]:
        """Predict class probability distributions for given samples."""

    @abstractmethod
    def get_parameters(self) -> dict[str, Any]:
        """Return model parameters and weights for serialization."""

    @abstractmethod
    def set_parameters(self, params: dict[str, Any]) -> None:
        """Load model parameters and weights from serialized dictionary."""
