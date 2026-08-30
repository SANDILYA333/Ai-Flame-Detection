"""Feature Ablation, Shortcut Detection & Dependency Audit (ML-007).

Orchestrates multi-model, multi-subset feature ablation experiments across approved
feature groups (Thermal Core, Temporal History, Persistence, Spatial, Land Cover)
to quantify performance dependencies, shortcut risks, and label circularity.
"""

from datetime import UTC, datetime
from typing import Any

from packages.schemas.ml import (
    AblationExperimentResult,
    AblationStudyReport,
    FeatureGroup,
    SplitPartition,
    SupervisedDataset,
)
from services.ml.evaluation.harness import EvaluationHarness
from services.ml.features.registry import FeatureRegistry
from services.ml.features.standard_set import get_standard_feature_registry
from services.ml.models.base import BaseMLModel
from services.ml.models.contextual import DeterministicContextualClassifier
from services.ml.models.linear import LogisticRegressionClassifier
from services.ml.models.tree import DecisionTreeClassifier, RandomForestClassifier
from services.ml.models.trivial import MajorityClassClassifier
from services.ml.preprocessing.extractor import DatasetSplitExtractor
from services.ml.preprocessing.transformer import FeaturePreprocessor


class FeatureAblationService:
    """Service defining canonical ablation subsets and running ablation suites."""

    @classmethod
    def get_canonical_subsets(
        cls, registry: FeatureRegistry | None = None
    ) -> dict[str, list[str]]:
        """Derive standard feature subsets from canonical feature registry."""
        reg = registry or get_standard_feature_registry()
        approved = reg.list_features(allowed_only=True)

        groups: dict[FeatureGroup, list[str]] = {}
        for f in approved:
            groups.setdefault(f.feature_group, []).append(f.feature_name)

        thermal = sorted(groups.get(FeatureGroup.THERMAL_CORE, []))
        temporal = sorted(groups.get(FeatureGroup.TEMPORAL_HISTORY, []))
        persistence = sorted(groups.get(FeatureGroup.PERSISTENCE_SOURCE, []))
        spatial = sorted(groups.get(FeatureGroup.SPATIAL_CONTEXT, []))
        environmental = sorted(
            groups.get(FeatureGroup.LAND_COVER, [])
            + groups.get(FeatureGroup.ENVIRONMENTAL_WEATHER, [])
        )

        all_approved = sorted(f.feature_name for f in approved)

        return {
            "FULL": all_approved,
            "THERMAL_ONLY": thermal,
            "TEMPORAL_ONLY": temporal,
            "PERSISTENCE_ONLY": persistence,
            "SPATIAL_ONLY": spatial,
            "ENVIRONMENTAL_ONLY": environmental,
            "NO_SPATIAL": sorted(set(all_approved) - set(spatial)),
            "NO_PERSISTENCE": sorted(set(all_approved) - set(persistence)),
            "NO_CONTEXT": sorted(set(all_approved) - set(spatial) - set(environmental)),
            "THERMAL_PLUS_TEMPORAL": sorted(set(thermal) | set(temporal)),
            "THERMAL_PLUS_ENVIRONMENTAL": sorted(set(thermal) | set(environmental)),
            "THERMAL_PLUS_TEMPORAL_PLUS_ENVIRONMENTAL": sorted(
                set(thermal) | set(temporal) | set(environmental)
            ),
        }

    @classmethod
    def run_ablation_study(
        cls,
        dataset: SupervisedDataset,
        target_id: str = "target_industrial_segregation",
        subsets: dict[str, list[str]] | None = None,
        model_types: list[str] | None = None,
        hyperparameters_by_model: dict[str, dict[str, Any]] | None = None,
        random_seed: int = 42,
    ) -> AblationStudyReport:
        """Run complete ablation matrix across requested subsets and models.

        Args:
            dataset: Supervised dataset container with frozen split.
            target_id: Prediction target specification.
            subsets: Optional custom subset mapping. Defaults to canonical subsets.
            model_types: Models to evaluate (default: B0, B2, B3, B4-DT, B4-RF).
            hyperparameters_by_model: Model configuration parameters.
            random_seed: Random seed for deterministic execution.

        Returns:
            AblationStudyReport containing all per-experiment metrics and deltas.
        """
        now = datetime.now(UTC)
        canonical_subsets = subsets or cls.get_canonical_subsets()
        all_features = sorted(canonical_subsets.get("FULL", []))

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

        # Collect raw FULL baseline performance for computing deltas
        full_test_scores: dict[str, dict[str, float]] = {}
        raw_results: list[AblationExperimentResult] = []

        # 1. Run all experiments
        for s_name, s_features in canonical_subsets.items():
            for m_type in models:
                exp_res = cls._evaluate_single_ablation_experiment(
                    dataset=dataset,
                    target_id=target_id,
                    subset_name=s_name,
                    subset_features=s_features,
                    all_features=all_features,
                    model_type=m_type,
                    hyperparameters=hparams.get(m_type, {}),
                    random_seed=random_seed,
                )
                raw_results.append(exp_res)

                if s_name == "FULL" and exp_res.is_applicable:
                    full_test_scores[m_type] = {
                        "macro_f1": float(
                            exp_res.test_metrics.get("macro_f1", 0.0) or 0.0
                        ),
                        "balanced_accuracy": float(
                            exp_res.test_metrics.get("balanced_accuracy", 0.0) or 0.0
                        ),
                        "accuracy": float(
                            exp_res.test_metrics.get("accuracy", 0.0) or 0.0
                        ),
                    }

        # 2. Compute deltas against FULL and construct finalized results
        final_results: list[AblationExperimentResult] = []
        for res in raw_results:
            if not res.is_applicable or res.model_type not in full_test_scores:
                final_results.append(res)
                continue

            full_base = full_test_scores[res.model_type]
            test_f1 = float(res.test_metrics.get("macro_f1", 0.0) or 0.0)
            test_bacc = float(res.test_metrics.get("balanced_accuracy", 0.0) or 0.0)
            test_acc = float(res.test_metrics.get("accuracy", 0.0) or 0.0)

            updated_res = res.model_copy(
                update={
                    "delta_vs_full_macro_f1": test_f1 - full_base["macro_f1"],
                    "delta_vs_full_balanced_acc": test_bacc
                    - full_base["balanced_accuracy"],
                    "delta_vs_full_acc": test_acc - full_base["accuracy"],
                }
            )
            final_results.append(updated_res)

        # 3. Compute diagnostic shortcut deltas
        shortcut_diag = cls._compute_shortcut_diagnostics(final_results)

        return AblationStudyReport(
            study_id=f"ablation_{target_id}_{dataset.manifest.dataset_version}",
            dataset_id=dataset.manifest.dataset_id,
            dataset_version=dataset.manifest.dataset_version,
            target_id=target_id,
            created_at=now,
            subsets_evaluated=list(canonical_subsets.keys()),
            models_evaluated=models,
            results=final_results,
            shortcut_diagnostics=shortcut_diag,
        )

    @classmethod
    def _evaluate_single_ablation_experiment(
        cls,
        dataset: SupervisedDataset,
        target_id: str,
        subset_name: str,
        subset_features: list[str],
        all_features: list[str],
        model_type: str,
        hyperparameters: dict[str, Any],
        random_seed: int,
    ) -> AblationExperimentResult:
        """Train and evaluate single model under specific feature subset."""
        exp_id = f"exp_{model_type.lower()}_{subset_name.lower()}"
        excluded = sorted(set(all_features) - set(subset_features))

        # Check semantic applicability for deterministic contextual baseline B2
        if model_type == "DeterministicContextualClassifier":
            # B2 requires spatial proximity features
            has_spatial = "facility_distance_meters" in subset_features
            if not has_spatial and subset_name != "FULL":
                return AblationExperimentResult(
                    experiment_id=exp_id,
                    subset_name=subset_name,
                    model_type=model_type,
                    feature_names=subset_features,
                    feature_count=len(subset_features),
                    excluded_features=excluded,
                    is_applicable=False,
                )

        # 1. Extract partitioned matrices with restricted feature subset
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
            feature_names=subset_features if subset_features else None,
        )

        if not x_tr_raw or not y_tr:
            return AblationExperimentResult(
                experiment_id=exp_id,
                subset_name=subset_name,
                model_type=model_type,
                feature_names=subset_features,
                feature_count=len(subset_features),
                excluded_features=excluded,
                is_applicable=False,
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

        # 4. Fit model on TRAIN ONLY
        is_raw = model_type == "DeterministicContextualClassifier"
        fit_x = x_tr_raw if is_raw else x_tr_vec
        eval_va_x = x_va_raw if is_raw else x_va_vec
        eval_te_x = x_te_raw if is_raw else x_te_vec

        model.fit(fit_x, y_tr)

        # 5. Evaluate on TRAIN, VALIDATION, and TEST
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

        va_preds = model.predict(eval_va_x)
        va_probs = model.predict_proba(eval_va_x)
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
                y_pred=va_preds,
                y_prob=va_probs,
            )
            if y_va
            else None
        )

        te_preds = model.predict(eval_te_x)
        te_probs = model.predict_proba(eval_te_x)
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
                y_pred=te_preds,
                y_prob=te_probs,
            )
            if y_te
            else None
        )

        tr_dict = tr_rep.model_dump(mode="json")
        va_dict = va_rep.model_dump(mode="json") if va_rep else {}
        te_dict = te_rep.model_dump(mode="json") if te_rep else {}

        tr_f1 = float(tr_dict.get("macro_f1") or 0.0)
        te_f1 = float(te_dict.get("macro_f1") or 0.0)
        gen_gap = tr_f1 - te_f1

        return AblationExperimentResult(
            experiment_id=exp_id,
            subset_name=subset_name,
            model_type=model_type,
            feature_names=subset_features,
            feature_count=len(subset_features),
            excluded_features=excluded,
            is_applicable=True,
            train_metrics=tr_dict,
            validation_metrics=va_dict,
            test_metrics=te_dict,
            generalization_gap_macro_f1=gen_gap,
        )

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

        raise ValueError(f"Unsupported model_type '{model_type}' for ablation.")

    @staticmethod
    def _compute_shortcut_diagnostics(
        results: list[AblationExperimentResult],
    ) -> dict[str, Any]:
        """Compute contextual shortcut sensitivity and thermal contribution deltas."""
        by_model_subset: dict[str, dict[str, AblationExperimentResult]] = {}
        for r in results:
            if r.is_applicable:
                by_model_subset.setdefault(r.model_type, {})[r.subset_name] = r

        diagnostics: dict[str, Any] = {}

        for m_type, subsets in by_model_subset.items():
            full = subsets.get("FULL")
            no_spatial = subsets.get("NO_SPATIAL")
            spatial_only = subsets.get("SPATIAL_ONLY")
            thermal_only = subsets.get("THERMAL_ONLY")

            full_f1 = float(full.test_metrics.get("macro_f1") or 0.0) if full else None
            no_sp_f1 = (
                float(no_spatial.test_metrics.get("macro_f1") or 0.0)
                if no_spatial
                else None
            )
            sp_only_f1 = (
                float(spatial_only.test_metrics.get("macro_f1") or 0.0)
                if spatial_only
                else None
            )
            th_only_f1 = (
                float(thermal_only.test_metrics.get("macro_f1") or 0.0)
                if thermal_only
                else None
            )

            context_drop = (
                (full_f1 - no_sp_f1)
                if full_f1 is not None and no_sp_f1 is not None
                else None
            )
            thermal_drop = (
                (full_f1 - th_only_f1)
                if full_f1 is not None and th_only_f1 is not None
                else None
            )

            diagnostics[m_type] = {
                "full_test_macro_f1": full_f1,
                "no_spatial_test_macro_f1": no_sp_f1,
                "spatial_only_test_macro_f1": sp_only_f1,
                "thermal_only_test_macro_f1": th_only_f1,
                "context_dependency_delta": context_drop,
                "thermal_dependency_delta": thermal_drop,
            }

        return diagnostics

    @classmethod
    def generate_ablation_summary_markdown(cls, report: AblationStudyReport) -> str:
        """Generate formatted Markdown comparison matrix from AblationStudyReport."""
        lines = [
            f"# Feature Ablation & Scientific Dependency Audit — {report.study_id}",
            "",
            (
                f"**Dataset ID:** `{report.dataset_id}` "
                f"(Version: `{report.dataset_version}`)\\"
            ),
            f"**Target ID:** `{report.target_id}`\\",
            f"**Evaluation Timestamp:** `{report.created_at.isoformat()}`",
            "",
            "## 1. Multi-Model Ablation Comparison Matrix (Test Partition)",
            "",
            (
                "| Feature Subset | Feature Count | B0 Prior F1 | B2 Heuristic F1 | "
                "B3 Logistic F1 | B4 DecisionTree F1 | B4 RandomForest F1 |"
            ),
            "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
        ]

        # Group by subset name
        by_subset: dict[str, dict[str, AblationExperimentResult]] = {}
        counts: dict[str, int] = {}
        for r in report.results:
            by_subset.setdefault(r.subset_name, {})[r.model_type] = r
            counts[r.subset_name] = r.feature_count

        for s_name in report.subsets_evaluated:
            m_map = by_subset.get(s_name, {})
            f_count = counts.get(s_name, 0)

            b0_s = cls._format_model_f1(m_map, "MajorityClassClassifier")
            b2_s = cls._format_model_f1(m_map, "DeterministicContextualClassifier")
            b3_s = cls._format_model_f1(m_map, "LogisticRegressionClassifier")
            b4_dt_s = cls._format_model_f1(m_map, "DecisionTreeClassifier")
            b4_rf_s = cls._format_model_f1(m_map, "RandomForestClassifier")

            lines.append(
                f"| **`{s_name}`** | {f_count} | {b0_s} | {b2_s} | "
                f"{b3_s} | {b4_dt_s} | {b4_rf_s} |"
            )

        header_2 = (
            "| Model | Full Test F1 | No Spatial F1 | Thermal Only F1 | "
            "Spatial Only F1 | Context Dependency (Δ) |"
        )
        lines.extend(
            [
                "",
                "## 2. Contextual Shortcut & Dependency Diagnostics",
                "",
                header_2,
                "| :--- | :---: | :---: | :---: | :---: | :---: |",
            ]
        )

        for m_type, diag in report.shortcut_diagnostics.items():
            f_f1 = (
                f"{diag['full_test_macro_f1']:.4f}"
                if diag.get("full_test_macro_f1") is not None
                else "N/A"
            )
            n_sp = (
                f"{diag['no_spatial_test_macro_f1']:.4f}"
                if diag.get("no_spatial_test_macro_f1") is not None
                else "N/A"
            )
            th_on = (
                f"{diag['thermal_only_test_macro_f1']:.4f}"
                if diag.get("thermal_only_test_macro_f1") is not None
                else "N/A"
            )
            sp_on = (
                f"{diag['spatial_only_test_macro_f1']:.4f}"
                if diag.get("spatial_only_test_macro_f1") is not None
                else "N/A"
            )
            c_drop = (
                f"{diag['context_dependency_delta']:+.4f}"
                if diag.get("context_dependency_delta") is not None
                else "N/A"
            )

            lines.append(
                f"| `{m_type}` | {f_f1} | {n_sp} | {th_on} | {sp_on} | **{c_drop}** |"
            )

        return "\n".join(lines)

    @staticmethod
    def _format_model_f1(
        m_map: dict[str, AblationExperimentResult], model_name: str
    ) -> str:
        """Format test Macro F1 score string for a given model result."""
        res = m_map.get(model_name)
        if not res or not res.is_applicable:
            return "N/A"
        f1_val = res.test_metrics.get("macro_f1")
        if f1_val is None:
            return "N/A"
        return f"{float(f1_val):.4f}"
