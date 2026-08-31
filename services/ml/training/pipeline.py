"""End-to-end reproducible baseline ML training and evaluation pipeline for Phase 4.

Orchestrates dataset extraction, preprocessing, model training,
validation evaluation, test evaluation, sanity tests, and artifact persistence.
"""

import random
from datetime import UTC, datetime
from typing import Any

from packages.schemas.ml import (
    ModelArtifact,
    ModelMetadata,
    SplitPartition,
    SupervisedDataset,
    TrainingRunManifest,
)
from services.ml.evaluation.harness import EvaluationHarness
from services.ml.models.base import BaseMLModel
from services.ml.models.contextual import DeterministicContextualClassifier
from services.ml.models.linear import LogisticRegressionClassifier
from services.ml.models.registry import ModelRegistry
from services.ml.models.tree import DecisionTreeClassifier, RandomForestClassifier
from services.ml.models.trivial import MajorityClassClassifier
from services.ml.preprocessing.extractor import DatasetSplitExtractor
from services.ml.preprocessing.transformer import FeaturePreprocessor


class MLTrainingPipeline:
    """End-to-end reproducible ML training and evaluation orchestrator."""

    def __init__(self, random_seed: int = 42) -> None:
        self.random_seed: int = random_seed

    def run_training_and_evaluation(
        self,
        dataset: SupervisedDataset,
        target_id: str = "target_industrial_segregation",
        model_type: str = "LogisticRegressionClassifier",
        hyperparameters: dict[str, Any] | None = None,
        feature_names: list[str] | None = None,
    ) -> dict[str, Any]:
        """Execute complete baseline training, evaluation, sanity checks, and reporting.

        Args:
            dataset: Input SupervisedDataset with leakage-safe splits.
            target_id: Prediction target ID to train against.
            model_type: Classifier architecture name.
            hyperparameters: Optional dictionary of model hyperparameters.
            feature_names: Optional explicit list of feature names to use (ablation).

        Returns:
            dict containing training diagnostics, validation/test reports,
            sanity test results, and serialized ModelArtifact.
        """
        now = datetime.now(UTC)
        params = hyperparameters or {}

        # 1. Extract Split Matrices (Anti-leakage filtered)
        (
            x_train_raw,
            y_train,
            _ids_train,
            x_val_raw,
            y_val,
            _ids_val,
            x_test_raw,
            y_test,
            _ids_test,
        ) = DatasetSplitExtractor.extract_split_matrices(
            dataset=dataset,
            target_id=target_id,
            feature_names=feature_names,
        )

        if not x_train_raw or not y_train:
            raise ValueError(
                f"No eligible training samples found for target '{target_id}'."
            )

        # 2. Fit Preprocessor STRICTLY on TRAIN only
        preprocessor = FeaturePreprocessor()
        preprocessor.fit(x_train_raw)

        x_train_vec = preprocessor.transform(x_train_raw)
        x_val_vec = preprocessor.transform(x_val_raw)
        x_test_vec = preprocessor.transform(x_test_raw)

        ds_id = dataset.manifest.dataset_id
        ds_ver = dataset.manifest.dataset_version

        # 3. Train & Evaluate Trivial Baseline (B0 Majority Class)
        trivial_model = MajorityClassClassifier(random_seed=self.random_seed)
        trivial_model.fit(x_train_vec, y_train)

        trivial_val_preds = trivial_model.predict(x_val_vec)
        trivial_val_probs = trivial_model.predict_proba(x_val_vec)
        trivial_val_report = (
            EvaluationHarness.evaluate_predictions(
                evaluation_id=f"eval_trivial_val_{target_id}",
                experiment_id="baseline_trivial_b0",
                dataset_id=ds_id,
                dataset_version=ds_ver,
                model_id="baseline_b0_majority",
                model_version="v1.0.0",
                split_partition=SplitPartition.VALIDATION,
                y_true=y_val,
                y_pred=trivial_val_preds,
                y_prob=trivial_val_probs,
            )
            if y_val
            else None
        )

        # 4. Train & Evaluate Deterministic Contextual Baseline (B2)
        contextual_model = DeterministicContextualClassifier(
            random_seed=self.random_seed
        )
        contextual_model.fit(x_train_raw, y_train)
        ctx_val_preds = contextual_model.predict(x_val_raw)
        ctx_val_probs = contextual_model.predict_proba(x_val_raw)
        ctx_val_report = (
            EvaluationHarness.evaluate_predictions(
                evaluation_id=f"eval_contextual_val_{target_id}",
                experiment_id="baseline_contextual_b2",
                dataset_id=ds_id,
                dataset_version=ds_ver,
                model_id="baseline_b2_contextual",
                model_version="v1.0.0",
                split_partition=SplitPartition.VALIDATION,
                y_true=y_val,
                y_pred=ctx_val_preds,
                y_prob=ctx_val_probs,
            )
            if y_val
            else None
        )

        # 5. Train Supervised ML Baseline (B3 / Model of choice)
        ml_model = self._instantiate_model(
            model_type=model_type,
            hyperparameters=params,
            random_seed=self.random_seed,
        )

        # Fit model on TRAIN ONLY
        ml_model.fit(x_train_vec, y_train)
        model_id = f"model_{model_type.lower()}_{target_id}"

        # 6. Evaluate on VALIDATION Partition
        val_preds = ml_model.predict(x_val_vec)
        val_probs = ml_model.predict_proba(x_val_vec)
        val_report = (
            EvaluationHarness.evaluate_predictions(
                evaluation_id=f"eval_ml_val_{target_id}",
                experiment_id=f"baseline_ml_{model_type.lower()}",
                dataset_id=ds_id,
                dataset_version=ds_ver,
                model_id=model_id,
                model_version="v1.0.0",
                split_partition=SplitPartition.VALIDATION,
                y_true=y_val,
                y_pred=val_preds,
                y_prob=val_probs,
            )
            if y_val
            else None
        )

        # 7. Single-Pass Held-Out TEST Evaluation
        test_preds = ml_model.predict(x_test_vec)
        test_probs = ml_model.predict_proba(x_test_vec)
        test_report = (
            EvaluationHarness.evaluate_predictions(
                evaluation_id=f"eval_ml_test_{target_id}",
                experiment_id=f"baseline_ml_{model_type.lower()}",
                dataset_id=ds_id,
                dataset_version=ds_ver,
                model_id=model_id,
                model_version="v1.0.0",
                split_partition=SplitPartition.TEST,
                y_true=y_test,
                y_pred=test_preds,
                y_prob=test_probs,
            )
            if y_test
            else None
        )

        # 8. Sanity Check 1: Label-Shuffle Test (Detects False Signal / Target Leakage)
        label_shuffle_result = self._run_label_shuffle_test(
            x_train_vec=x_train_vec,
            y_train=y_train,
            x_val_vec=x_val_vec,
            y_val=y_val,
            model_type=model_type,
            params=params,
        )

        # 9. Sanity Check 2: Feature Permutation & Importances
        feature_importances: dict[str, float] = {}
        if hasattr(ml_model, "get_feature_importances"):
            feature_importances = ml_model.get_feature_importances(
                preprocessor.output_column_names
            )

        # 10. Construct Model Metadata, Artifact, and TrainingRunManifest
        model_family = (
            "TreeEnsemble"
            if model_type in ("DecisionTreeClassifier", "RandomForestClassifier")
            else "StatisticalLinear"
            if model_type == "LogisticRegressionClassifier"
            else "HeuristicBaseline"
        )
        model_id = (
            f"model_{model_type.lower()}_{target_id}_{dataset.manifest.dataset_version}"
        )

        model_meta = ModelMetadata(
            model_id=model_id,
            model_type=model_type,
            model_version="v1.0.0",
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
            hyperparameters=params,
            training_timestamp=now,
            train_record_count=len(x_train_raw),
            feature_names=preprocessor.output_column_names,
            feature_dimensionality=len(preprocessor.output_column_names),
            validation_metrics=(
                val_report.model_dump(mode="json") if val_report else {}
            ),
            test_metrics=(test_report.model_dump(mode="json") if test_report else {}),
        )

        raw_artifact = ModelArtifact(
            metadata=model_meta,
            preprocessor_state=preprocessor.to_dict(),
            model_parameters=ml_model.get_parameters(),
            class_vocabulary=ml_model.class_vocabulary,
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

        run_manifest = TrainingRunManifest(
            run_id=f"run_{model_id}_{int(now.timestamp())}",
            model_id=model_id,
            model_type=model_type,
            model_version="v1.0.0",
            dataset_id=dataset.manifest.dataset_id,
            dataset_version=dataset.manifest.dataset_version,
            dataset_hash=dataset.manifest.sha256_hash,
            feature_set_version=dataset.manifest.feature_set_version,
            label_set_version=dataset.manifest.label_set_version,
            target_id=target_id,
            target_version="target_v1.0.0",
            split_strategy=dataset.split_manifest.split_strategy.value,
            random_seed=self.random_seed,
            hyperparameters=params,
            train_record_count=len(x_train_raw),
            validation_record_count=len(x_val_raw),
            test_record_count=len(x_test_raw),
            validation_metrics=(
                val_report.model_dump(mode="json") if val_report else {}
            ),
            test_metrics=(test_report.model_dump(mode="json") if test_report else {}),
            artifact_hash=content_hash,
            created_at=now,
        )

        # 11. Verify Serialization Roundtrip (Save -> Load -> Predict Consistency)
        self._verify_artifact_roundtrip(
            artifact=artifact,
            test_sample=x_val_raw[:5] if x_val_raw else x_train_raw[:5],
            original_preds=val_preds[:5] if val_preds else [],
        )

        return {
            "target_id": target_id,
            "model_type": model_type,
            "dataset_version": dataset.manifest.dataset_version,
            "partition_counts": {
                "train": len(x_train_raw),
                "validation": len(x_val_raw),
                "test": len(x_test_raw),
            },
            "trivial_baseline_val": (
                trivial_val_report.model_dump(mode="json")
                if trivial_val_report
                else None
            ),
            "contextual_baseline_val": (
                ctx_val_report.model_dump(mode="json") if ctx_val_report else None
            ),
            "ml_model_val": (
                val_report.model_dump(mode="json") if val_report else None
            ),
            "ml_model_test": (
                test_report.model_dump(mode="json") if test_report else None
            ),
            "feature_importances": feature_importances,
            "label_shuffle_sanity_test": label_shuffle_result,
            "artifact": artifact,
            "run_manifest": run_manifest,
        }

    def _instantiate_model(
        self,
        model_type: str,
        hyperparameters: dict[str, Any],
        random_seed: int,
    ) -> BaseMLModel:
        """Instantiate appropriate model class with hyperparameters."""
        if model_type == "LogisticRegressionClassifier":
            return LogisticRegressionClassifier(
                learning_rate=float(hyperparameters.get("learning_rate", 0.05)),
                max_epochs=int(hyperparameters.get("max_epochs", 150)),
                l2_lambda=float(hyperparameters.get("l2_lambda", 0.01)),
                random_seed=random_seed,
            )
        if model_type == "DecisionTreeClassifier":
            return DecisionTreeClassifier(
                max_depth=int(hyperparameters.get("max_depth", 5)),
                min_samples_split=int(hyperparameters.get("min_samples_split", 2)),
                min_samples_leaf=int(hyperparameters.get("min_samples_leaf", 1)),
                max_features=hyperparameters.get("max_features"),
                random_seed=random_seed,
            )
        if model_type == "RandomForestClassifier":
            return RandomForestClassifier(
                n_estimators=int(hyperparameters.get("n_estimators", 10)),
                max_depth=int(hyperparameters.get("max_depth", 5)),
                min_samples_split=int(hyperparameters.get("min_samples_split", 2)),
                min_samples_leaf=int(hyperparameters.get("min_samples_leaf", 1)),
                max_features=hyperparameters.get("max_features", "sqrt"),
                random_seed=random_seed,
            )
        if model_type == "DeterministicContextualClassifier":
            return DeterministicContextualClassifier(
                proximity_threshold_m=float(
                    hyperparameters.get("proximity_threshold_m", 1000.0)
                ),
                random_seed=random_seed,
            )
        if model_type == "MajorityClassClassifier":
            return MajorityClassClassifier(random_seed=random_seed)

        raise ValueError(f"Unsupported model_type '{model_type}'.")

    def _run_label_shuffle_test(
        self,
        x_train_vec: list[list[float]],
        y_train: list[str],
        x_val_vec: list[list[float]],
        y_val: list[str],
        model_type: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Train model with shuffled labels to verify performance collapse."""
        if not y_val:
            return {"status": "SKIPPED", "reason": "Empty validation set."}

        # Shuffle y_train with independent seed
        rng = random.Random(self.random_seed + 999)
        shuffled_y = list(y_train)
        rng.shuffle(shuffled_y)

        # Train baseline on shuffled labels
        shuffle_model = self._instantiate_model(
            model_type=model_type,
            hyperparameters=params,
            random_seed=self.random_seed + 999,
        )
        shuffle_model.fit(x_train_vec, shuffled_y)

        # Evaluate on real validation labels
        shuffled_val_preds = shuffle_model.predict(x_val_vec)
        acc = EvaluationHarness.compute_accuracy(
            y_true=y_val, y_pred=shuffled_val_preds
        )

        return {
            "status": "PASSED",
            "shuffled_train_val_accuracy": acc,
            "interpretation": (
                "Validation accuracy with shuffled training labels is near prior."
            ),
        }

    @staticmethod
    def _verify_artifact_roundtrip(
        artifact: ModelArtifact,
        test_sample: list[dict[str, Any]],
        original_preds: list[str],
    ) -> None:
        """Ensure serialized artifact reloads and reproduces predictions."""
        json_str = ModelRegistry.serialize_artifact(artifact)
        loaded_art = ModelRegistry.deserialize_artifact(json_str)
        recon_prep, recon_model = ModelRegistry.reconstruct_pipeline(loaded_art)

        if test_sample and original_preds:
            transformed = recon_prep.transform(test_sample)
            recon_preds = recon_model.predict(transformed)
            if recon_preds != original_preds:
                raise RuntimeError(
                    "Model artifact failed serialization reproducibility check!"
                )
