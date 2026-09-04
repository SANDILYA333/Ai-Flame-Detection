"""Model registry and secure serialization service for ML artifacts (ML-009).

Enforces:
- Deterministic JSON serialization and content-addressable SHA-256 hashing.
- Recursive secret auditing (rejects API keys, tokens, credentials, passwords).
- Artifact integrity validation (schema versioning, parameter completeness).
- Exact pipeline reconstruction (FeaturePreprocessor + BaseMLModel).
"""

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
    "private_key",
    "authorization",
)

SUPPORTED_MODEL_TYPES: tuple[str, ...] = (
    "MajorityClassClassifier",
    "DeterministicContextualClassifier",
    "LogisticRegressionClassifier",
    "DecisionTreeClassifier",
    "RandomForestClassifier",
    "XGBoostClassifier",
    "LightGBMClassifier",
)


class ModelRegistry:
    """Registry managing model persistence, metadata validation, and reconstruction."""

    @classmethod
    def serialize_artifact(cls, artifact: ModelArtifact) -> str:
        """Serialize ModelArtifact to JSON while auditing against secret leaks.

        Computes and embeds deterministic SHA-256 content hash if not already present.
        """
        content_hash = artifact.compute_content_hash()
        artifact_to_save = artifact.model_copy(update={"sha256_hash": content_hash})

        data = artifact_to_save.model_dump(mode="json")
        cls._audit_no_secrets(data)
        return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=True)

    @classmethod
    def deserialize_artifact(cls, json_str: str) -> ModelArtifact:
        """Deserialize ModelArtifact from JSON string and audit integrity."""
        try:
            data = json.loads(json_str)
        except Exception as e:
            raise ValueError(f"Corrupted or invalid JSON artifact: {e}") from e

        cls._audit_no_secrets(data)
        artifact = ModelArtifact.model_validate(data)
        cls.verify_artifact_integrity(artifact)
        return artifact

    @classmethod
    def save_to_file(cls, artifact: ModelArtifact, file_path: Path | str) -> Path:
        """Save ModelArtifact to filesystem with content hashing and secret audits."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        json_content = cls.serialize_artifact(artifact)
        path.write_text(json_content, encoding="utf-8")
        return path

    @classmethod
    def load_from_file(cls, file_path: Path | str) -> ModelArtifact:
        """Load ModelArtifact from filesystem and verify integrity."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Model artifact not found at {path}")
        json_content = path.read_text(encoding="utf-8")
        return cls.deserialize_artifact(json_content)

    @classmethod
    def verify_artifact_integrity(cls, artifact: ModelArtifact) -> bool:
        """Verify structural validity, model type support, and content hash."""
        m_type = artifact.metadata.model_type
        if m_type not in SUPPORTED_MODEL_TYPES:
            raise ValueError(
                f"Unsupported model type '{m_type}'. "
                f"Expected one of {SUPPORTED_MODEL_TYPES}."
            )

        if not artifact.metadata.model_id or not artifact.metadata.target_id:
            raise ValueError(
                "Artifact metadata missing required model_id or target_id."
            )

        if not artifact.class_vocabulary:
            raise ValueError("Artifact class_vocabulary cannot be empty.")

        if len(artifact.class_vocabulary) != len(set(artifact.class_vocabulary)):
            raise ValueError("Artifact class_vocabulary contains duplicate entries.")

        # If sha256_hash is provided, verify content hash match
        if artifact.sha256_hash:
            computed_hash = artifact.compute_content_hash()
            if artifact.sha256_hash != computed_hash:
                raise ValueError(
                    f"Artifact content hash mismatch: stored={artifact.sha256_hash}, "
                    f"computed={computed_hash}. Artifact may be tampered with."
                )

        return True

    @classmethod
    def reconstruct_pipeline(
        cls, artifact: ModelArtifact
    ) -> tuple[FeaturePreprocessor, BaseMLModel]:
        """Reconstruct fitted FeaturePreprocessor and BaseMLModel from artifact."""
        cls.verify_artifact_integrity(artifact)

        # 1. Reconstruct preprocessor
        preprocessor = FeaturePreprocessor.from_dict(artifact.preprocessor_state)

        # 2. Reconstruct model by model_type
        m_type = artifact.metadata.model_type
        model: BaseMLModel

        if m_type == "MajorityClassClassifier":
            model = MajorityClassClassifier(random_seed=artifact.metadata.random_seed)
        elif m_type == "DeterministicContextualClassifier":
            model = DeterministicContextualClassifier(
                random_seed=artifact.metadata.random_seed
            )
        elif m_type == "LogisticRegressionClassifier":
            model = LogisticRegressionClassifier(
                random_seed=artifact.metadata.random_seed
            )
        elif m_type == "DecisionTreeClassifier":
            model = DecisionTreeClassifier(random_seed=artifact.metadata.random_seed)
        elif m_type == "RandomForestClassifier":
            model = RandomForestClassifier(random_seed=artifact.metadata.random_seed)
        elif m_type == "XGBoostClassifier":
            from services.ml.models.xgboost_model import XGBoostClassifier

            model = XGBoostClassifier(random_seed=artifact.metadata.random_seed)
        elif m_type == "LightGBMClassifier":
            from services.ml.models.lightgbm_model import LightGBMClassifier

            model = LightGBMClassifier(random_seed=artifact.metadata.random_seed)
        else:
            raise ValueError(f"Unknown model type '{m_type}' in artifact.")

        model.set_parameters(artifact.model_parameters)
        return preprocessor, model

    @classmethod
    def list_artifacts(cls, directory: Path | str) -> list[ModelArtifact]:
        """List and validate all artifacts in a local directory."""
        dir_path = Path(directory)
        if not dir_path.exists():
            return []

        artifacts: list[ModelArtifact] = []
        for p in sorted(dir_path.glob("*.json")):
            try:
                art = cls.load_from_file(p)
                artifacts.append(art)
            except Exception:
                continue
        return artifacts

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
        elif isinstance(obj, str):
            # Check string value for suspicious authorization tokens or map keys
            lower_str = obj.lower()
            if "bearer " in lower_str or "firms_map_key" in lower_str:
                raise ValueError(
                    f"Prohibited credential token detected in value at '{path}'"
                )
