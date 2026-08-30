"""Model registry and secure serialization service for ML artifacts."""

import json
from pathlib import Path
from typing import Any

from packages.schemas.ml import ModelArtifact
from services.ml.models.base import BaseMLModel
from services.ml.models.contextual import DeterministicContextualClassifier
from services.ml.models.linear import LogisticRegressionClassifier
from services.ml.models.tree import DecisionTreeClassifier, RandomForestClassifier
from services.ml.models.trivial import MajorityClassClassifier
from services.ml.preprocessing.transformer import FeaturePreprocessor

SENSITIVE_KEY_PATTERNS: tuple[str, ...] = (
    "map_key",
    "token",
    "secret",
    "password",
    "api_key",
    "credential",
)


class ModelRegistry:
    """Registry managing model persistence, metadata validation, and reconstruction."""

    @classmethod
    def serialize_artifact(cls, artifact: ModelArtifact) -> str:
        """Serialize ModelArtifact to JSON while auditing against secret leaks."""
        data = artifact.model_dump(mode="json")
        cls._audit_no_secrets(data)
        return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=True)

    @classmethod
    def deserialize_artifact(cls, json_str: str) -> ModelArtifact:
        """Deserialize ModelArtifact from JSON string."""
        data = json.loads(json_str)
        return ModelArtifact.model_validate(data)

    @classmethod
    def save_to_file(cls, artifact: ModelArtifact, file_path: Path | str) -> Path:
        """Save ModelArtifact to filesystem."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        json_content = cls.serialize_artifact(artifact)
        path.write_text(json_content, encoding="utf-8")
        return path

    @classmethod
    def load_from_file(cls, file_path: Path | str) -> ModelArtifact:
        """Load ModelArtifact from filesystem."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Model artifact not found at {path}")
        json_content = path.read_text(encoding="utf-8")
        return cls.deserialize_artifact(json_content)

    @classmethod
    def reconstruct_pipeline(
        cls, artifact: ModelArtifact
    ) -> tuple[FeaturePreprocessor, BaseMLModel]:
        """Reconstruct fitted FeaturePreprocessor and BaseMLModel from artifact."""
        # 1. Reconstruct preprocessor
        preprocessor = FeaturePreprocessor.from_dict(artifact.preprocessor_state)

        # 2. Reconstruct model by model_type
        m_type = artifact.metadata.model_type
        model: BaseMLModel

        if m_type == "MajorityClassClassifier":
            model = MajorityClassClassifier()
        elif m_type == "DeterministicContextualClassifier":
            model = DeterministicContextualClassifier()
        elif m_type == "LogisticRegressionClassifier":
            model = LogisticRegressionClassifier()
        elif m_type == "DecisionTreeClassifier":
            model = DecisionTreeClassifier()
        elif m_type == "RandomForestClassifier":
            model = RandomForestClassifier()
        else:
            raise ValueError(f"Unknown model type '{m_type}' in artifact.")

        model.set_parameters(artifact.model_parameters)
        return preprocessor, model

    @classmethod
    def _audit_no_secrets(cls, obj: Any, path: str = "") -> None:
        """Recursively ensure no API keys, tokens, or passwords exist in metadata."""
        if isinstance(obj, dict):
            for k, v in obj.items():
                k_lower = str(k).lower()
                for pattern in SENSITIVE_KEY_PATTERNS:
                    if pattern in k_lower:
                        raise ValueError(
                            f"Prohibited sensitive key '{k}' found at path '{path}.{k}'"
                        )
                cls._audit_no_secrets(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                cls._audit_no_secrets(item, f"{path}[{i}]")
