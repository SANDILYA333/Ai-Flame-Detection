"""Real ML Model Training and Validation Orchestrator (NEXT-004).

Consumes canonical real SupervisedDataset (e.g. ds_real_supervised_v1.0.0), evaluates
the absolute scientific training gate, and fits the canonical model ladder (B0, B2, B3, B4-DT, B4-RF)
in pilot/smoke-training mode without bypassing scientific invariants.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packages.schemas.ml import (
    ModelArtifact,
    ModelMetadata,
    SplitPartition,
    SupervisedDataset,
    TrainingRunManifest,
)
from services.ml.models.base import BaseMLModel
from services.ml.models.contextual import DeterministicContextualClassifier
from services.ml.models.linear import LogisticRegressionClassifier
from services.ml.models.registry import ModelRegistry
from services.ml.models.tree import DecisionTreeClassifier, RandomForestClassifier
from services.ml.models.trivial import MajorityClassClassifier
from services.ml.preprocessing.extractor import DatasetSplitExtractor
from services.ml.preprocessing.transformer import FeaturePreprocessor
from services.ml.training.gate import RealTrainingGateEvaluation, RealTrainingGateEvaluator

CANONICAL_REAL_MODELS: tuple[str, ...] = (
    "MajorityClassClassifier",           # B0 Majority baseline
    "DeterministicContextualClassifier",  # B2 Deterministic contextual baseline
    "LogisticRegressionClassifier",       # B3 Softmax Logistic Regression
    "DecisionTreeClassifier",             # B4-DT CART Decision Tree
    "RandomForestClassifier",             # B4-RF Random Forest Ensemble
)


@dataclass(frozen=True)
class RealModelTrainingResult:
    """Result of training an individual model architecture on real data."""

    model_type: str
    model_id: str
    status: str  # "TRAINED_PILOT", "TRAINED_PRODUCTION", "BLOCKED"
    is_production_ready: bool
    train_record_count: int
    class_vocabulary: list[str]
    artifact_path: str | None
    artifact_hash: str | None
    reason: str
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RealTrainingSuiteResult:
    """Consolidated result of executing the real training suite."""

    dataset_id: str
    dataset_version: str
    target_id: str
    gate_evaluation: RealTrainingGateEvaluation
    model_results: dict[str, RealModelTrainingResult]
    is_production_ready: bool
    artifact_directory: str


class RealMLTrainer:
    """Orchestrates scientific gate evaluation and real ML model training."""

    def __init__(
        self,
        random_seed: int = 42,
        artifact_base_dir: Path | str = "artifacts/real/pilot",
    ) -> None:
        self.random_seed: int = random_seed
        self.artifact_base_dir = Path(artifact_base_dir)

    def train_real_suite(
        self,
        dataset: SupervisedDataset,
        target_id: str = "target_industrial_segregation",
        model_types: tuple[str, ...] | list[str] = CANONICAL_REAL_MODELS,
        hyperparameters: dict[str, dict[str, Any]] | None = None,
    ) -> RealTrainingSuiteResult:
        """Execute the real ML training suite with strict scientific gating.

        Args:
            dataset: The real SupervisedDataset (e.g. feat_ds_real_supervised_v1.0.0).
            target_id: Prediction target identifier.
            model_types: Sequence of model architecture names to fit.
            hyperparameters: Optional dictionary mapping model_type to param dicts.

        Returns:
            RealTrainingSuiteResult containing gate evaluation and per-model results.
        """
        now = datetime.now(UTC)
        params_map = hyperparameters or {}

        # 1. Scientific Gate Evaluation
        gate_eval = RealTrainingGateEvaluator.evaluate(dataset=dataset, target_id=target_id)

        # 2. Extract Training Matrices (strictly filtered, anti-leakage enforced)
        (
            x_train_raw,
            y_train,
            ids_train,
            x_val_raw,
            y_val,
            _ids_val,
            x_test_raw,
            y_test,
            _ids_test,
        ) = DatasetSplitExtractor.extract_split_matrices(
            dataset=dataset,
            target_id=target_id,
        )

        if not x_train_raw or not y_train:
            raise ValueError(
                f"Zero eligible training records found for target '{target_id}'."
            )

        # 3. Fit Preprocessor strictly on Train
        preprocessor = FeaturePreprocessor()
        preprocessor.fit(x_train_raw)
        x_train_vec = preprocessor.transform(x_train_raw)

        model_results: dict[str, RealModelTrainingResult] = {}
        self.artifact_base_dir.mkdir(parents=True, exist_ok=True)

        for m_type in model_types:
            m_params = params_map.get(m_type, {})
            model_inst = self._instantiate_model(
                model_type=m_type,
                params=m_params,
                random_seed=self.random_seed,
            )

            # Fit model on training partition
            if m_type == "DeterministicContextualClassifier":
                model_inst.fit(x_train_raw, y_train)
            else:
                model_inst.fit(x_train_vec, y_train)

            train_preds = model_inst.predict(
                x_train_raw if m_type == "DeterministicContextualClassifier" else x_train_vec
            )

            # Construct Metadata with strict Pilot & Gate markers
            model_id = (
                f"real_{m_type.lower()}_{target_id}_{dataset.manifest.dataset_version}"
            )
            model_family = (
                "TreeEnsemble"
                if "Tree" in m_type or "Forest" in m_type
                else "StatisticalLinear"
                if "Logistic" in m_type
                else "HeuristicBaseline"
            )

            model_meta = ModelMetadata(
                model_id=model_id,
                model_type=m_type,
                model_version="v1.0.0-pilot",
                model_family=model_family,
                target_id=target_id,
                target_version="target_v1.0.0",
                dataset_id=dataset.manifest.dataset_id,
                dataset_version=dataset.manifest.dataset_version,
                dataset_hash=dataset.manifest.sha256_hash,
                feature_set_version=dataset.manifest.feature_set_version,
                label_set_version=dataset.manifest.label_set_version,
                split_strategy=dataset.split_manifest.split_strategy.value,
                split_version=dataset.split_manifest.split_strategy.value,
                random_seed=self.random_seed,
                hyperparameters=m_params,
                training_timestamp=now,
                train_record_count=len(x_train_raw),
                feature_names=preprocessor.output_column_names,
                feature_dimensionality=len(preprocessor.output_column_names),
                validation_metrics={
                    "pilot_mode": True,
                    "scientific_gate_status": gate_eval.gate_status,
                    "is_production_ready": False,
                    "circularity_warning": gate_eval.circularity_warning,
                },
                test_metrics={
                    "pilot_mode": True,
                    "evaluation_status": "BLOCKED_BY_GATE",
                },
            )

            raw_artifact = ModelArtifact(
                metadata=model_meta,
                preprocessor_state=preprocessor.to_dict(),
                model_parameters=model_inst.get_parameters(),
                class_vocabulary=model_inst.class_vocabulary,
            )
            content_hash = raw_artifact.compute_content_hash()
            artifact = raw_artifact.model_copy(
                update={
                    "sha256_hash": content_hash,
                    "metadata": model_meta.model_copy(
                        update={"artifact_hash": content_hash}
                    ),
                }
            )

            # Persist artifact to filesystem in real pilot namespace
            artifact_file = self.artifact_base_dir / f"{model_id}.json"
            ModelRegistry.save_to_file(artifact, artifact_file)

            # Verification roundtrip
            self._verify_roundtrip(
                artifact_file=artifact_file,
                test_sample=x_train_raw[:3],
                expected_preds=train_preds[:3],
                is_contextual=(m_type == "DeterministicContextualClassifier"),
            )

            status_str = (
                "TRAINED_PRODUCTION" if gate_eval.is_production_ready else "TRAINED_PILOT"
            )
            reason_str = (
                "Production training completed successfully."
                if gate_eval.is_production_ready
                else "Fitted in pilot mode only; production training blocked by scientific gate."
            )

            model_results[m_type] = RealModelTrainingResult(
                model_type=m_type,
                model_id=model_id,
                status=status_str,
                is_production_ready=gate_eval.is_production_ready,
                train_record_count=len(x_train_raw),
                class_vocabulary=model_inst.class_vocabulary,
                artifact_path=str(artifact_file),
                artifact_hash=content_hash,
                reason=reason_str,
                metrics={"train_samples": len(x_train_raw)},
            )

        return RealTrainingSuiteResult(
            dataset_id=dataset.manifest.dataset_id,
            dataset_version=dataset.manifest.dataset_version,
            target_id=target_id,
            gate_evaluation=gate_eval,
            model_results=model_results,
            is_production_ready=gate_eval.is_production_ready,
            artifact_directory=str(self.artifact_base_dir),
        )

    def _instantiate_model(
        self,
        model_type: str,
        params: dict[str, Any],
        random_seed: int,
    ) -> BaseMLModel:
        """Instantiate canonical model class."""
        if model_type == "MajorityClassClassifier":
            return MajorityClassClassifier(random_seed=random_seed)
        if model_type == "DeterministicContextualClassifier":
            return DeterministicContextualClassifier(
                proximity_threshold_m=float(params.get("proximity_threshold_m", 1000.0)),
                random_seed=random_seed,
            )
        if model_type == "LogisticRegressionClassifier":
            return LogisticRegressionClassifier(
                learning_rate=float(params.get("learning_rate", 0.05)),
                max_epochs=int(params.get("max_epochs", 100)),
                l2_lambda=float(params.get("l2_lambda", 0.01)),
                random_seed=random_seed,
            )
        if model_type == "DecisionTreeClassifier":
            return DecisionTreeClassifier(
                max_depth=int(params.get("max_depth", 3)),
                min_samples_split=int(params.get("min_samples_split", 2)),
                min_samples_leaf=int(params.get("min_samples_leaf", 1)),
                random_seed=random_seed,
            )
        if model_type == "RandomForestClassifier":
            return RandomForestClassifier(
                n_estimators=int(params.get("n_estimators", 5)),
                max_depth=int(params.get("max_depth", 3)),
                random_seed=random_seed,
            )
        raise ValueError(f"Unsupported model_type: '{model_type}'")

    @staticmethod
    def _verify_roundtrip(
        artifact_file: Path,
        test_sample: list[dict[str, Any]],
        expected_preds: list[str],
        is_contextual: bool,
    ) -> None:
        """Verify saved artifact loads and reproduces identical predictions."""
        loaded_artifact = ModelRegistry.load_from_file(artifact_file)
        recon_prep, recon_model = ModelRegistry.reconstruct_pipeline(loaded_artifact)

        if is_contextual:
            preds = recon_model.predict(test_sample)
        else:
            transformed = recon_prep.transform(test_sample)
            preds = recon_model.predict(transformed)

        if preds != expected_preds:
            raise RuntimeError(
                f"Serialization reproducibility failure for {artifact_file.name}: "
                f"expected {expected_preds}, got {preds}"
            )
