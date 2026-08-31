"""Spatial, Temporal & Source Holdout Generalization Benchmark Service (ML-008).

Orchestrates multi-strategy, multi-model generalization experiments across:
- Grouped Event Holdout (GROUPED_EVENT_HOLDOUT)
- Persistent Source Holdout (PERSISTENT_SOURCE_HOLDOUT)
- Facility Holdout (FACILITY_HOLDOUT)
- Spatial Geographic Block Holdout (SPATIAL_GEOGRAPHIC_HOLDOUT)
- Chronological Temporal Holdout (TEMPORAL_HOLDOUT)
- Source / Sensor Platform Holdout (SOURCE_SENSOR_HOLDOUT)

Quantifies Generalization Gaps, evaluates spatial shortcut resilience, and validates
anti-leakage invariants.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from packages.schemas.ml import (
    FeatureDataset,
    GeneralizationExperimentResult,
    GeneralizationStudyReport,
    LabelDecision,
    SplitPartition,
    SplitStrategy,
    SupervisedDataset,
)
from services.ml.evaluation.harness import EvaluationHarness
from services.ml.labels.dataset import SupervisedDatasetBuilder
from services.ml.models.base import BaseMLModel
from services.ml.models.contextual import DeterministicContextualClassifier
from services.ml.models.linear import LogisticRegressionClassifier
from services.ml.models.tree import DecisionTreeClassifier, RandomForestClassifier
from services.ml.models.trivial import MajorityClassClassifier
from services.ml.preprocessing.extractor import DatasetSplitExtractor
from services.ml.preprocessing.transformer import FeaturePreprocessor


class GeneralizationBenchmarkService:
    """Service orchestrating rigorous generalization holdout benchmarks for Phase 4."""

    @classmethod
    def run_generalization_benchmark(
        cls,
        feature_dataset: FeatureDataset,
        label_decisions_by_target: dict[str, Sequence[LabelDecision]],
        target_id: str = "target_industrial_segregation",
        strategies: list[SplitStrategy] | None = None,
        model_types: list[str] | None = None,
        hyperparameters_by_model: dict[str, dict[str, Any]] | None = None,
        train_ratio: float = 0.60,
        val_ratio: float = 0.20,
        test_ratio: float = 0.20,
        random_seed: int = 42,
    ) -> GeneralizationStudyReport:
        """Run complete generalization matrix across holdout strategies and models.

        Args:
            feature_dataset: Underlying FeatureDataset.
            label_decisions_by_target: Labels mapped by target.
            target_id: Prediction target identifier.
            strategies: Optional list of SplitStrategy enums to benchmark.
            model_types: Optional list of baseline models to evaluate.
            hyperparameters_by_model: Model configuration dictionaries.
            train_ratio: Training proportion.
            val_ratio: Validation proportion.
            test_ratio: Test proportion.
            random_seed: Random seed for deterministic hashing.

        Returns:
            GeneralizationStudyReport containing all empirical generalization metrics.
        """
        now = datetime.now(UTC)
        eval_strategies = strategies or [
            SplitStrategy.GROUPED_EVENT_HOLDOUT,
            SplitStrategy.PERSISTENT_SOURCE_HOLDOUT,
            SplitStrategy.FACILITY_HOLDOUT,
            SplitStrategy.SPATIAL_GEOGRAPHIC_HOLDOUT,
            SplitStrategy.TEMPORAL_HOLDOUT,
            SplitStrategy.SOURCE_SENSOR_HOLDOUT,
        ]
        models = model_types or [
            "MajorityClassClassifier",
            "DeterministicContextualClassifier",
            "LogisticRegressionClassifier",
            "DecisionTreeClassifier",
            "RandomForestClassifier",
        ]
        hparams = hyperparameters_by_model or {
            "LogisticRegressionClassifier": {
                "learning_rate": 0.05,
                "max_epochs": 150,
                "l2_lambda": 0.01,
            },
            "DecisionTreeClassifier": {
                "max_depth": 5,
                "min_samples_split": 2,
                "min_samples_leaf": 1,
            },
            "RandomForestClassifier": {
                "n_estimators": 10,
                "max_depth": 5,
                "min_samples_split": 2,
                "min_samples_leaf": 1,
                "max_features": "sqrt",
            },
            "DeterministicContextualClassifier": {"proximity_threshold_m": 1000.0},
            "MajorityClassClassifier": {},
        }

        dataset_builder = SupervisedDatasetBuilder()
        datasets_by_strategy: dict[SplitStrategy, SupervisedDataset | None] = {}
        strategy_feasibility: dict[SplitStrategy, tuple[bool, str | None]] = {}

        # 1. Build supervised datasets for each strategy
        for strat in eval_strategies:
            try:
                sup_ds = dataset_builder.build_supervised_dataset(
                    feature_dataset=feature_dataset,
                    label_decisions_by_target=label_decisions_by_target,
                    split_strategy=strat,
                    train_ratio=train_ratio,
                    val_ratio=val_ratio,
                    test_ratio=test_ratio,
                    random_seed=random_seed,
                )
                datasets_by_strategy[strat] = sup_ds
                strategy_feasibility[strat] = (True, None)
            except Exception as e:
                datasets_by_strategy[strat] = None
                strategy_feasibility[strat] = (False, str(e))

        # 2. Evaluate all model-strategy pairs
        raw_results: list[GeneralizationExperimentResult] = []
        base_event_scores: dict[str, dict[str, float]] = {}

        for strat in eval_strategies:
            is_feasible, note = strategy_feasibility[strat]
            eval_ds = datasets_by_strategy.get(strat)

            if not is_feasible or eval_ds is None:
                for m_type in models:
                    raw_results.append(
                        GeneralizationExperimentResult(
                            experiment_id=f"gen_{strat.value.lower()}_{m_type.lower()}",
                            split_strategy=strat,
                            model_type=m_type,
                            is_feasible=False,
                            feasibility_notes=note
                            or "Dataset partition failed feasibility criteria.",
                        )
                    )
                continue

            for m_type in models:
                res = cls._evaluate_model_on_split(
                    dataset=eval_ds,
                    target_id=target_id,
                    strategy=strat,
                    model_type=m_type,
                    hyperparameters=hparams.get(m_type, {}),
                    random_seed=random_seed,
                )
                raw_results.append(res)

                if strat == SplitStrategy.GROUPED_EVENT_HOLDOUT and res.is_feasible:
                    base_event_scores[m_type] = {
                        "macro_f1": float(res.test_metrics.get("macro_f1", 0.0) or 0.0),
                        "balanced_accuracy": float(
                            res.test_metrics.get("balanced_accuracy", 0.0) or 0.0
                        ),
                    }

        # 3. Compute Generalization Gaps vs standard GROUPED_EVENT_HOLDOUT
        final_results: list[GeneralizationExperimentResult] = []
        gen_gaps_map: dict[str, dict[str, float | None]] = {}

        for res in raw_results:
            if not res.is_feasible or res.model_type not in base_event_scores:
                final_results.append(res)
                continue

            base_scores = base_event_scores[res.model_type]
            curr_f1 = float(res.test_metrics.get("macro_f1", 0.0) or 0.0)
            curr_bacc = float(res.test_metrics.get("balanced_accuracy", 0.0) or 0.0)

            gap_f1 = base_scores["macro_f1"] - curr_f1
            gap_bacc = base_scores["balanced_accuracy"] - curr_bacc

            updated = res.model_copy(
                update={
                    "generalization_gap_macro_f1": gap_f1,
                    "generalization_gap_balanced_acc": gap_bacc,
                }
            )
            final_results.append(updated)

            gen_gaps_map.setdefault(res.model_type, {})[res.split_strategy.value] = (
                gap_f1
            )

        # 4. Compile Shortcut Resilience under Spatial Block Holdout
        shortcut_res = cls._evaluate_spatial_shortcut_resilience(
            spatial_dataset=datasets_by_strategy.get(
                SplitStrategy.SPATIAL_GEOGRAPHIC_HOLDOUT
            ),
            target_id=target_id,
            hyperparameters_by_model=hparams,
            random_seed=random_seed,
        )

        return GeneralizationStudyReport(
            study_id=f"generalization_{target_id}_{feature_dataset.manifest.dataset_version}",
            dataset_id=feature_dataset.manifest.dataset_id,
            dataset_version=feature_dataset.manifest.dataset_version,
            target_id=target_id,
            created_at=now,
            strategies_evaluated=eval_strategies,
            models_evaluated=models,
            results=final_results,
            generalization_gaps=gen_gaps_map,
            shortcut_resilience=shortcut_res,
        )

    @classmethod
    def _evaluate_model_on_split(
        cls,
        dataset: SupervisedDataset,
        target_id: str,
        strategy: SplitStrategy,
        model_type: str,
        hyperparameters: dict[str, Any],
        random_seed: int,
        feature_names: list[str] | None = None,
    ) -> GeneralizationExperimentResult:
        """Train and evaluate single model under specific holdout partition."""
        exp_id = f"gen_{strategy.value.lower()}_{model_type.lower()}"

        # 1. Extract partitioned matrices
        (
            x_tr_raw,
            y_tr,
            _,
            x_va_raw,
            y_va,
            _,
            x_te_raw,
            y_te,
            _,
        ) = DatasetSplitExtractor.extract_split_matrices(
            dataset=dataset,
            target_id=target_id,
            feature_names=feature_names,
        )

        if not x_tr_raw or not y_tr or not x_te_raw or not y_te:
            return GeneralizationExperimentResult(
                experiment_id=exp_id,
                split_strategy=strategy,
                model_type=model_type,
                is_feasible=False,
                feasibility_notes=(
                    "NOT FEASIBLE WITH CURRENT DATA: Insufficient partition records "
                    f"(train={len(x_tr_raw)}, test={len(x_te_raw)})."
                ),
            )

        # 2. Fit FeaturePreprocessor STRICTLY on TRAIN only
        preprocessor = FeaturePreprocessor()
        preprocessor.fit(x_tr_raw)

        x_tr_vec = preprocessor.transform(x_tr_raw)
        x_va_vec = preprocessor.transform(x_va_raw)
        x_te_vec = preprocessor.transform(x_te_raw)

        # 3. Instantiate model
        model = cls._instantiate_model(
            model_type=model_type,
            hyperparameters=hyperparameters,
            random_seed=random_seed,
        )

        # 4. Fit model on TRAIN only
        is_raw = model_type == "DeterministicContextualClassifier"
        fit_x = x_tr_raw if is_raw else x_tr_vec
        eval_va_x = x_va_raw if is_raw else x_va_vec
        eval_te_x = x_te_raw if is_raw else x_te_vec

        model.fit(fit_x, y_tr)

        # 5. Evaluate on TRAIN, VALIDATION, and TEST partitions
        tr_preds = model.predict(fit_x)
        tr_probs = model.predict_proba(fit_x)
        tr_rep = EvaluationHarness.evaluate_predictions(
            evaluation_id=f"{exp_id}_train",
            experiment_id=exp_id,
            dataset_id=dataset.manifest.dataset_id,
            dataset_version=dataset.manifest.dataset_version,
            model_id=f"m_{model_type.lower()}",
            model_version="v1.0.0",
            split_partition=SplitPartition.TRAIN,
            y_true=y_tr,
            y_pred=tr_preds,
            y_prob=tr_probs,
        )

        va_rep = (
            EvaluationHarness.evaluate_predictions(
                evaluation_id=f"{exp_id}_val",
                experiment_id=exp_id,
                dataset_id=dataset.manifest.dataset_id,
                dataset_version=dataset.manifest.dataset_version,
                model_id=f"m_{model_type.lower()}",
                model_version="v1.0.0",
                split_partition=SplitPartition.VALIDATION,
                y_true=y_va,
                y_pred=model.predict(eval_va_x),
                y_prob=model.predict_proba(eval_va_x),
            )
            if y_va
            else None
        )

        te_rep = (
            EvaluationHarness.evaluate_predictions(
                evaluation_id=f"{exp_id}_test",
                experiment_id=exp_id,
                dataset_id=dataset.manifest.dataset_id,
                dataset_version=dataset.manifest.dataset_version,
                model_id=f"m_{model_type.lower()}",
                model_version="v1.0.0",
                split_partition=SplitPartition.TEST,
                y_true=y_te,
                y_pred=model.predict(eval_te_x),
                y_prob=model.predict_proba(eval_te_x),
            )
            if y_te
            else None
        )

        return GeneralizationExperimentResult(
            experiment_id=exp_id,
            split_strategy=strategy,
            model_type=model_type,
            is_feasible=True,
            train_record_count=len(x_tr_raw),
            val_record_count=len(x_va_raw),
            test_record_count=len(x_te_raw),
            train_metrics=tr_rep.model_dump(mode="json"),
            validation_metrics=va_rep.model_dump(mode="json") if va_rep else {},
            test_metrics=te_rep.model_dump(mode="json") if te_rep else {},
        )

    @classmethod
    def _evaluate_spatial_shortcut_resilience(
        cls,
        spatial_dataset: SupervisedDataset | None,
        target_id: str,
        hyperparameters_by_model: dict[str, dict[str, Any]],
        random_seed: int,
    ) -> dict[str, Any]:
        """Audit performance without proximity features under spatial holdout."""
        if spatial_dataset is None:
            return {"status": "NOT_EVALUATED", "reason": "Spatial dataset unavailable"}

        models = [
            "LogisticRegressionClassifier",
            "DecisionTreeClassifier",
            "RandomForestClassifier",
        ]
        resilience: dict[str, Any] = {}

        for m_type in models:
            # Full features
            full_res = cls._evaluate_model_on_split(
                dataset=spatial_dataset,
                target_id=target_id,
                strategy=SplitStrategy.SPATIAL_GEOGRAPHIC_HOLDOUT,
                model_type=m_type,
                hyperparameters=hyperparameters_by_model.get(m_type, {}),
                random_seed=random_seed,
            )

            # Thermal only features
            thermal_features = [
                "frp_mean_mw",
                "frp_max_mw",
                "frp_min_mw",
                "frp_sum_mw",
                "frp_std_mw",
                "duration_hours",
                "brightness_mean_kelvin",
                "brightness_max_kelvin",
                "detection_count",
                "daynight_ratio",
                "temporal_density",
                "spatial_extent_radius_meters",
                "satellite_platform_diversity",
                "sensor_instrument",
            ]
            th_res = cls._evaluate_model_on_split(
                dataset=spatial_dataset,
                target_id=target_id,
                strategy=SplitStrategy.SPATIAL_GEOGRAPHIC_HOLDOUT,
                model_type=m_type,
                hyperparameters=hyperparameters_by_model.get(m_type, {}),
                random_seed=random_seed,
                feature_names=thermal_features,
            )

            f_f1 = (
                float(full_res.test_metrics.get("macro_f1") or 0.0)
                if full_res.is_feasible
                else 0.0
            )
            th_f1 = (
                float(th_res.test_metrics.get("macro_f1") or 0.0)
                if th_res.is_feasible
                else 0.0
            )

            resilience[m_type] = {
                "spatial_holdout_full_f1": f_f1,
                "spatial_holdout_thermal_only_f1": th_f1,
                "spatial_shortcut_drop": f_f1 - th_f1,
            }

        return resilience

    @classmethod
    def _instantiate_model(
        cls,
        model_type: str,
        hyperparameters: dict[str, Any],
        random_seed: int,
    ) -> BaseMLModel:
        """Instantiate model instance with hyperparameters and random seed."""
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

        raise ValueError(f"Unsupported model_type '{model_type}' for generalization.")

    @classmethod
    def generate_generalization_summary_markdown(
        cls, report: GeneralizationStudyReport
    ) -> str:
        """Generate formatted Markdown comparison matrix for generalization."""
        lines = [
            f"# Generalization & Holdout Independence Benchmark — {report.study_id}",
            "",
            (
                f"**Dataset ID:** `{report.dataset_id}` "
                f"(Version: `{report.dataset_version}`)\\"
            ),
            f"**Target ID:** `{report.target_id}`\\",
            f"**Evaluation Timestamp:** `{report.created_at.isoformat()}`",
            "",
            "## 1. Generalization Benchmark Matrix (Test Partition Macro F1)",
            "",
            (
                "| Holdout Split Strategy | B0 Prior F1 | B2 Heuristic F1 | "
                "B3 Logistic F1 | B4 DecisionTree F1 | B4 RandomForest F1 |"
            ),
            "| :--- | :---: | :---: | :---: | :---: | :---: |",
        ]

        # Group by strategy
        by_strat: dict[SplitStrategy, dict[str, GeneralizationExperimentResult]] = {}
        for r in report.results:
            by_strat.setdefault(r.split_strategy, {})[r.model_type] = r

        for strat in report.strategies_evaluated:
            m_map = by_strat.get(strat, {})

            b0_s = cls._format_score(m_map, "MajorityClassClassifier")
            b2_s = cls._format_score(m_map, "DeterministicContextualClassifier")
            b3_s = cls._format_score(m_map, "LogisticRegressionClassifier")
            b4_dt_s = cls._format_score(m_map, "DecisionTreeClassifier")
            b4_rf_s = cls._format_score(m_map, "RandomForestClassifier")

            row_str = (
                f"| **`{strat.value}`** | {b0_s} | {b2_s} | {b3_s} | "
                f"{b4_dt_s} | {b4_rf_s} |"
            )
            lines.append(row_str)

        header_2 = (
            "| Model Architecture | Event Holdout F1 | Spatial Block Gap (Δ) | "
            "Source Holdout Gap (Δ) | Temporal Holdout Gap (Δ) |"
        )
        lines.extend(
            [
                "",
                "## 2. Generalization Gaps vs Standard Grouped Event Holdout",
                "",
                header_2,
                "| :--- | :---: | :---: | :---: | :---: |",
            ]
        )

        for m_type in report.models_evaluated:
            ev_res = by_strat.get(SplitStrategy.GROUPED_EVENT_HOLDOUT, {}).get(m_type)
            ev_f1 = (
                f"{float(ev_res.test_metrics.get('macro_f1', 0.0)):.4f}"
                if ev_res and ev_res.is_feasible
                else "N/A"
            )

            gaps = report.generalization_gaps.get(m_type, {})
            sp_gap = gaps.get(SplitStrategy.SPATIAL_GEOGRAPHIC_HOLDOUT.value)
            so_gap = gaps.get(SplitStrategy.PERSISTENT_SOURCE_HOLDOUT.value)
            te_gap = gaps.get(SplitStrategy.TEMPORAL_HOLDOUT.value)

            sp_s = f"{sp_gap:+.4f}" if sp_gap is not None else "N/A"
            so_s = f"{so_gap:+.4f}" if so_gap is not None else "N/A"
            te_s = f"{te_gap:+.4f}" if te_gap is not None else "N/A"

            lines.append(f"| `{m_type}` | {ev_f1} | **{sp_s}** | {so_s} | {te_s} |")

        return "\n".join(lines)

    @staticmethod
    def _format_score(
        m_map: dict[str, GeneralizationExperimentResult], model_name: str
    ) -> str:
        """Format score string."""
        res = m_map.get(model_name)
        if not res or not res.is_feasible:
            return "NOT FEASIBLE"
        val = res.test_metrics.get("macro_f1")
        if val is None:
            return "N/A"
        return f"{float(val):.4f}"
