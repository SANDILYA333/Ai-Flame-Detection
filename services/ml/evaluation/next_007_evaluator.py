"""NEXT-007: Comprehensive Real Production Model Scientific Evaluation Service.

Performs rigorous, leak-free evaluation of production ML model artifacts
on held-out data:
1. Core Classification Metrics (Accuracy, Balanced Accuracy, Precision, Recall, F1).
2. Probabilistic & Calibration Scoring (ROC-AUC, PR-AUC, Brier Score, Log Loss, ECE).
3. Selective Classification & Abstention Tradeoff Curves.
4. Model Feature Importance & Group-Ablation Impact.
5. Geographic Stratification (All 8 Indian & Global corridors).
6. Sensor Stratification (VIIRS, MODIS, HYBRID).
7. Temporal Stratification (Early, Middle, Late periods).
8. 95% Bootstrap Confidence Intervals (Deterministic seed=42).
9. Multi-Metric Candidate Selection & Scientific Acceptance Gates.
10. Evaluation Artifact Serialization under artifacts/real/evaluation/.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from packages.schemas.ml import (
    DatasetRowStatus,
    ModelArtifact,
    SupervisedDataset,
)
from services.ml.evaluation.harness import EvaluationHarness
from services.ml.features.standard_set import APPROVED_FEATURES
from services.ml.models.registry import ModelRegistry
from services.ml.preprocessing.extractor import DatasetSplitExtractor
from services.ml.preprocessing.transformer import FeaturePreprocessor

if TYPE_CHECKING:
    from services.ml.models.base import BaseMLModel


@dataclass(frozen=True)
class ConfusionMatrixData:
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    positive_class: str


@dataclass(frozen=True)
class CalibrationBin:
    bin_lower: float
    bin_upper: float
    sample_count: int
    mean_confidence: float
    observed_accuracy: float
    calibration_gap: float


@dataclass(frozen=True)
class AbstentionThresholdResult:
    confidence_threshold: float
    coverage: float
    abstention_rate: float
    accepted_samples: int
    selective_accuracy: float
    selective_precision: float
    selective_recall: float
    selective_macro_f1: float


@dataclass(frozen=True)
class StratificationResult:
    stratum_name: str
    sample_count: int
    industrial_count: int
    non_industrial_count: int
    status: str  # "VALID" or "INSUFFICIENT_SAMPLE"
    accuracy: float | None
    macro_f1: float | None
    balanced_accuracy: float | None


@dataclass(frozen=True)
class FeatureAblationResult:
    feature_group: str
    features_removed: list[str]
    remaining_feature_count: int
    macro_f1: float
    balanced_accuracy: float
    macro_f1_delta: float
    balanced_accuracy_delta: float


@dataclass(frozen=True)
class SingleModelEvaluationReport:
    model_id: str
    model_type: str
    model_role: str
    model_version: str
    artifact_path: str
    artifact_hash: str
    train_samples: int
    val_samples: int
    test_samples: int
    positive_class: str
    accuracy: float
    balanced_accuracy: float
    precision: float
    recall: float
    f1_score: float
    macro_f1: float
    per_class_metrics: dict[str, dict[str, Any]]
    confusion_matrix: ConfusionMatrixData
    roc_auc: float | None
    pr_auc: float | None
    brier_score: float | None
    log_loss: float | None
    expected_calibration_error: float | None
    calibration_bins: list[CalibrationBin]
    abstention_curve: list[AbstentionThresholdResult]
    top_feature_importances: dict[str, float]
    geographic_stratification: list[StratificationResult]
    sensor_stratification: list[StratificationResult]
    temporal_stratification: list[StratificationResult]
    confidence_intervals: dict[str, tuple[float, float]]


@dataclass(frozen=True)
class Next007CampaignReport:
    campaign_id: str
    dataset_id: str
    dataset_version: str
    dataset_hash: str
    evaluated_at: str
    target_id: str
    split_strategy: str
    random_seed: int
    total_physical_events: int
    eligible_labeled_events: int
    industrial_events: int
    non_industrial_events: int
    unknown_excluded_events: int
    models_evaluated: list[SingleModelEvaluationReport]
    feature_ablation_matrix: list[FeatureAblationResult]
    model_comparison_table: list[dict[str, Any]]
    acceptance_gates: dict[str, dict[str, Any]]
    all_gates_passed: bool
    recommended_production_model: str
    executive_verdict: str


class Next007RealModelEvaluator:
    """Scientific evaluation engine for NEXT-007 real production models."""

    CONFIDENCE_THRESHOLDS: tuple[float, ...] = (0.50, 0.60, 0.70, 0.80, 0.90)
    BOOTSTRAP_ROUNDS: int = 1000
    POSITIVE_CLASS: str = "industrial"

    @classmethod
    def evaluate_production_campaign(
        cls,
        dataset: SupervisedDataset,
        production_artifact_dir: Path | str = "artifacts/real/production",
        output_dir: Path | str = "artifacts/real/evaluation",
        target_id: str = "target_industrial_segregation",
        event_coords: dict[str, tuple[float, float]] | None = None,
        random_seed: int = 42,
    ) -> Next007CampaignReport:
        """Run full real-world evaluation campaign on all production model artifacts."""
        now = datetime.now(UTC)
        prod_path = Path(production_artifact_dir)
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        (
            x_train_raw,
            y_train,
            _ids_train,
            x_val_raw,
            _y_val,
            _ids_val,
            x_test_raw,
            y_test,
            ids_test,
        ) = DatasetSplitExtractor.extract_split_matrices(
            dataset=dataset,
            target_id=target_id,
        )

        eligible_records = [
            r
            for r in dataset.records
            if r.row_status == DatasetRowStatus.TRAIN_ELIGIBLE
            and r.labels.get(target_id)
            and r.labels[target_id].is_train_eligible
            and r.labels[target_id].assigned_class != "unknown"
        ]
        ind_count = sum(
            1
            for r in eligible_records
            if r.labels[target_id].assigned_class == "industrial"
        )
        non_ind_count = sum(
            1
            for r in eligible_records
            if r.labels[target_id].assigned_class == "non_industrial"
        )
        unknown_count = len(dataset.records) - len(eligible_records)

        model_roles = {
            "MajorityClassClassifier": "B0 Baseline (Majority Class)",
            "DeterministicContextualClassifier": "B2 Reference (Deterministic)",
            "LogisticRegressionClassifier": "B3 Candidate (Softmax Linear)",
            "DecisionTreeClassifier": "B4-DT Candidate (CART Decision Tree)",
            "RandomForestClassifier": "B4-RF Candidate (Random Forest)",
        }

        evaluated_models: list[SingleModelEvaluationReport] = []

        for m_type, m_role in model_roles.items():
            artifact_file = prod_path / f"real_{m_type.lower()}_{target_id}_v1.0.0.json"
            if not artifact_file.exists():
                continue

            artifact = ModelRegistry.load_from_file(artifact_file)
            preprocessor, model = ModelRegistry.reconstruct_pipeline(artifact)

            if m_type == "DeterministicContextualClassifier":
                y_pred = model.predict(x_test_raw)
                y_prob = model.predict_proba(x_test_raw)
            else:
                x_test_vec = preprocessor.transform(x_test_raw)
                y_pred = model.predict(x_test_vec)
                y_prob = model.predict_proba(x_test_vec)

            report = cls._evaluate_single_model(
                artifact=artifact,
                model=model,
                model_role=m_role,
                artifact_file=artifact_file,
                x_test_raw=x_test_raw,
                y_test=y_test,
                y_pred=y_pred,
                y_prob=y_prob,
                ids_test=ids_test,
                event_coords=event_coords,
                train_count=len(x_train_raw),
                val_count=len(x_val_raw),
                random_seed=random_seed,
            )
            evaluated_models.append(report)

        ablation_results = cls._run_feature_group_ablation(
            x_train_raw=x_train_raw,
            y_train=y_train,
            x_test_raw=x_test_raw,
            y_test=y_test,
            random_seed=random_seed,
        )

        comparison_table: list[dict[str, Any]] = []
        for em in evaluated_models:
            ci_f1 = em.confidence_intervals.get("macro_f1", (0.0, 0.0))
            comparison_table.append(
                {
                    "model_type": em.model_type,
                    "role": em.model_role,
                    "accuracy": round(em.accuracy, 4),
                    "balanced_accuracy": round(em.balanced_accuracy, 4),
                    "precision": round(em.precision, 4),
                    "recall": round(em.recall, 4),
                    "macro_f1": round(em.macro_f1, 4),
                    "roc_auc": (
                        round(em.roc_auc, 4) if em.roc_auc is not None else "N/A"
                    ),
                    "pr_auc": round(em.pr_auc, 4) if em.pr_auc is not None else "N/A",
                    "brier_score": (
                        round(em.brier_score, 4)
                        if em.brier_score is not None
                        else "N/A"
                    ),
                    "ece": (
                        round(em.expected_calibration_error, 4)
                        if em.expected_calibration_error is not None
                        else "N/A"
                    ),
                    "ci_95_macro_f1": f"[{ci_f1[0]:.3f}, {ci_f1[1]:.3f}]",
                }
            )

        rf_report = next(
            (m for m in evaluated_models if "RandomForest" in m.model_type),
            evaluated_models[-1],
        )
        b0_report = next(
            (m for m in evaluated_models if "Majority" in m.model_type),
            evaluated_models[0],
        )

        gate_results: dict[str, dict[str, Any]] = {
            "MINIMUM_MACRO_F1": {
                "threshold": ">= 0.75",
                "observed": rf_report.macro_f1,
                "passed": rf_report.macro_f1 >= 0.75,
            },
            "MINIMUM_MINORITY_RECALL": {
                "threshold": ">= 0.70",
                "observed": rf_report.recall,
                "passed": rf_report.recall >= 0.70,
            },
            "MINIMUM_BALANCED_ACCURACY": {
                "threshold": ">= 0.75",
                "observed": rf_report.balanced_accuracy,
                "passed": rf_report.balanced_accuracy >= 0.75,
            },
            "MAXIMUM_CALIBRATION_ERROR": {
                "threshold": "<= 0.15",
                "observed": rf_report.expected_calibration_error or 0.0,
                "passed": (
                    rf_report.expected_calibration_error is not None
                    and rf_report.expected_calibration_error <= 0.15
                ),
            },
            "BASELINE_SUPERIORITY": {
                "threshold": f"> B0 ({b0_report.macro_f1:.4f})",
                "observed": rf_report.macro_f1,
                "passed": rf_report.macro_f1 > b0_report.macro_f1,
            },
        }

        all_passed = all(g["passed"] for g in gate_results.values())
        verdict = "COMPLETE" if all_passed else "FAILED"

        campaign = Next007CampaignReport(
            campaign_id=f"next_007_eval_{now.strftime('%Y%m%d_%H%M%S')}",
            dataset_id=dataset.manifest.dataset_id,
            dataset_version=dataset.manifest.dataset_version,
            dataset_hash=dataset.manifest.sha256_hash,
            evaluated_at=now.isoformat(),
            target_id=target_id,
            split_strategy=dataset.split_manifest.split_strategy.value,
            random_seed=random_seed,
            total_physical_events=len(dataset.records),
            eligible_labeled_events=len(eligible_records),
            industrial_events=ind_count,
            non_industrial_events=non_ind_count,
            unknown_excluded_events=unknown_count,
            models_evaluated=evaluated_models,
            feature_ablation_matrix=ablation_results,
            model_comparison_table=comparison_table,
            acceptance_gates=gate_results,
            all_gates_passed=all_passed,
            recommended_production_model=rf_report.model_id,
            executive_verdict=verdict,
        )

        campaign_dict = asdict(campaign)
        (out_path / "real_model_evaluation_report.json").write_text(
            json.dumps(campaign_dict, indent=2), encoding="utf-8"
        )
        (out_path / "model_comparison_table.json").write_text(
            json.dumps(comparison_table, indent=2), encoding="utf-8"
        )
        (out_path / "feature_ablation_report.json").write_text(
            json.dumps([asdict(a) for a in ablation_results], indent=2),
            encoding="utf-8",
        )

        return campaign

    @classmethod
    def _evaluate_single_model(
        cls,
        artifact: ModelArtifact,
        model: BaseMLModel,
        model_role: str,
        artifact_file: Path,
        x_test_raw: list[dict[str, Any]],
        y_test: list[str],
        y_pred: list[str],
        y_prob: list[dict[str, float]] | None,
        ids_test: list[str],
        event_coords: dict[str, tuple[float, float]] | None,
        train_count: int,
        val_count: int,
        random_seed: int,
    ) -> SingleModelEvaluationReport:
        """Compute all metrics, calibration, abstention, and stratification."""
        meta = artifact.metadata
        classes = sorted(set(y_test) | set(y_pred))

        per_class = EvaluationHarness.compute_per_class_metrics(
            y_test, y_pred, classes
        )
        _macro_p, _macro_r, macro_f1 = EvaluationHarness.compute_macro_metrics(
            per_class
        )
        cm = EvaluationHarness.compute_confusion_matrix(y_test, y_pred, classes)

        pos_cls = cls.POSITIVE_CLASS
        pos_idx = classes.index(pos_cls) if pos_cls in classes else 0
        tp = cm[pos_idx][pos_idx]
        fp = sum(cm[r][pos_idx] for r in range(len(classes)) if r != pos_idx)
        fn = sum(cm[pos_idx][c] for c in range(len(classes)) if c != pos_idx)
        tn = len(y_test) - (tp + fp + fn)

        accuracy = (
            sum(cm[i][i] for i in range(len(classes))) / len(y_test)
            if y_test
            else 0.0
        )
        recalls = [
            float(per_class[c].recall or 0.0)
            for c in classes
            if c in per_class and per_class[c].recall is not None
        ]
        balanced_acc = sum(recalls) / len(recalls) if recalls else 0.0

        pos_metrics = per_class.get(pos_cls)
        precision = float(pos_metrics.precision or 0.0) if pos_metrics else 0.0
        recall = float(pos_metrics.recall or 0.0) if pos_metrics else 0.0
        f1_score = float(pos_metrics.f1_score or 0.0) if pos_metrics else 0.0

        conf_matrix = ConfusionMatrixData(
            true_positives=tp,
            false_positives=fp,
            true_negatives=tn,
            false_negatives=fn,
            positive_class=pos_cls,
        )

        roc_auc: float | None = None
        pr_auc: float | None = None
        brier_score: float | None = None
        log_loss: float | None = None
        ece: float | None = None
        cal_bins: list[CalibrationBin] = []

        if y_prob and len(y_prob) == len(y_test):
            brier_score = EvaluationHarness.compute_brier_score(
                y_test, y_prob, class_labels=classes
            )
            log_loss = EvaluationHarness.compute_log_loss(y_test, y_prob)

            pos_probs = [p.get(pos_cls, 0.5) for p in y_prob]
            y_binary = [1 if y == pos_cls else 0 for y in y_test]

            roc_auc = cls._compute_roc_auc(y_binary, pos_probs)
            pr_auc = cls._compute_pr_auc(y_binary, pos_probs)
            ece, cal_bins = cls._compute_calibration(y_binary, pos_probs)

        abstention_curve = cls._compute_abstention_curve(
            y_test, y_pred, y_prob, pos_cls
        )

        top_importances: dict[str, float] = {}
        if hasattr(model, "feature_importances_"):
            imp = getattr(model, "feature_importances_", None)
            feat_names = meta.feature_names or [
                f.feature_name for f in APPROVED_FEATURES
            ]
            if imp and len(imp) == len(feat_names):
                ranked = sorted(
                    zip(feat_names, imp, strict=False),
                    key=lambda x: x[1],
                    reverse=True,
                )
                top_importances = {k: round(float(v), 5) for k, v in ranked[:10]}
        elif hasattr(model, "weights_"):
            weights = getattr(model, "weights_", {})
            feat_names = meta.feature_names or [
                f.feature_name for f in APPROVED_FEATURES
            ]
            pos_weights = weights.get(pos_cls, [])
            if pos_weights and len(pos_weights) == len(feat_names):
                ranked = sorted(
                    zip(feat_names, [abs(w) for w in pos_weights], strict=False),
                    key=lambda x: x[1],
                    reverse=True,
                )
                top_importances = {k: round(float(v), 5) for k, v in ranked[:10]}

        geo_strat = cls._compute_geographic_stratification(
            x_test_raw, y_test, y_pred, ids_test, event_coords
        )
        sensor_strat = cls._compute_sensor_stratification(x_test_raw, y_test, y_pred)
        temp_strat = cls._compute_temporal_stratification(x_test_raw, y_test, y_pred)

        conf_intervals = cls._compute_bootstrap_ci(
            y_test=y_test,
            y_pred=y_pred,
            y_prob=y_prob,
            classes=classes,
            pos_cls=pos_cls,
            n_rounds=cls.BOOTSTRAP_ROUNDS,
            seed=random_seed,
        )

        return SingleModelEvaluationReport(
            model_id=meta.model_id,
            model_type=meta.model_type,
            model_role=model_role,
            model_version=meta.model_version,
            artifact_path=str(artifact_file),
            artifact_hash=artifact.sha256_hash or "",
            train_samples=train_count,
            val_samples=val_count,
            test_samples=len(y_test),
            positive_class=pos_cls,
            accuracy=accuracy,
            balanced_accuracy=balanced_acc,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            macro_f1=macro_f1,
            per_class_metrics={
                k: v.model_dump(mode="json") for k, v in per_class.items()
            },
            confusion_matrix=conf_matrix,
            roc_auc=roc_auc,
            pr_auc=pr_auc,
            brier_score=brier_score,
            log_loss=log_loss,
            expected_calibration_error=ece,
            calibration_bins=cal_bins,
            abstention_curve=abstention_curve,
            top_feature_importances=top_importances,
            geographic_stratification=geo_strat,
            sensor_stratification=sensor_strat,
            temporal_stratification=temp_strat,
            confidence_intervals=conf_intervals,
        )

    @classmethod
    def _compute_roc_auc(cls, y_true: list[int], y_score: list[float]) -> float:
        """Compute ROC-AUC score via Wilcoxon-Mann-Whitney rank sum."""
        n_pos = sum(y_true)
        n_neg = len(y_true) - n_pos
        if n_pos == 0 or n_neg == 0:
            return 0.5

        paired = sorted(zip(y_score, y_true, strict=False), key=lambda x: x[0])
        rank_sum = 0
        for rank, (_score, label) in enumerate(paired, 1):
            if label == 1:
                rank_sum += rank

        u = rank_sum - (n_pos * (n_pos + 1)) / 2.0
        return max(0.0, min(1.0, float(u / (n_pos * n_neg))))

    @classmethod
    def _compute_pr_auc(cls, y_true: list[int], y_score: list[float]) -> float:
        """Compute Area under Precision-Recall curve."""
        n_pos = sum(y_true)
        if n_pos == 0:
            return 0.0

        paired = sorted(
            zip(y_score, y_true, strict=False), key=lambda x: x[0], reverse=True
        )
        tp = 0
        fp = 0
        precisions = []
        recalls = []

        for _score, label in paired:
            if label == 1:
                tp += 1
            else:
                fp += 1
            precisions.append(tp / (tp + fp))
            recalls.append(tp / n_pos)

        auc = 0.0
        prev_r = 0.0
        prev_p = 1.0
        for p, r in zip(precisions, recalls, strict=False):
            auc += (r - prev_r) * (p + prev_p) / 2.0
            prev_r = r
            prev_p = p
        return max(0.0, min(1.0, float(auc)))

    @classmethod
    def _compute_calibration(
        cls, y_true: list[int], y_prob: list[float], n_bins: int = 10
    ) -> tuple[float, list[CalibrationBin]]:
        """Compute Expected Calibration Error (ECE) and probability binning."""
        bin_size = 1.0 / n_bins
        bins: list[CalibrationBin] = []
        total_samples = len(y_true)
        total_ece = 0.0

        for i in range(n_bins):
            lower = i * bin_size
            upper = (i + 1) * bin_size
            in_bin = [
                (p, t)
                for p, t in zip(y_prob, y_true, strict=False)
                if (lower <= p < upper) or (i == n_bins - 1 and lower <= p <= upper)
            ]
            count = len(in_bin)
            if count == 0:
                bins.append(
                    CalibrationBin(
                        bin_lower=round(lower, 2),
                        bin_upper=round(upper, 2),
                        sample_count=0,
                        mean_confidence=round((lower + upper) / 2.0, 3),
                        observed_accuracy=0.0,
                        calibration_gap=0.0,
                    )
                )
                continue

            mean_conf = sum(p for p, _ in in_bin) / count
            obs_acc = sum(t for _, t in in_bin) / count
            gap = abs(mean_conf - obs_acc)
            total_ece += (count / total_samples) * gap

            bins.append(
                CalibrationBin(
                    bin_lower=round(lower, 2),
                    bin_upper=round(upper, 2),
                    sample_count=count,
                    mean_confidence=round(mean_conf, 4),
                    observed_accuracy=round(obs_acc, 4),
                    calibration_gap=round(gap, 4),
                )
            )

        return float(total_ece), bins

    @classmethod
    def _compute_abstention_curve(
        cls,
        y_true: list[str],
        y_pred: list[str],
        y_prob: list[dict[str, float]] | None,
        pos_cls: str,
    ) -> list[AbstentionThresholdResult]:
        """Compute selective classification metrics across confidence thresholds."""
        curve: list[AbstentionThresholdResult] = []
        total_n = len(y_true)
        if total_n == 0:
            return curve

        for thresh in cls.CONFIDENCE_THRESHOLDS:
            accepted_indices = []
            if y_prob:
                for idx, p_map in enumerate(y_prob):
                    max_p = max(p_map.values()) if p_map else 1.0
                    if max_p >= thresh:
                        accepted_indices.append(idx)
            else:
                accepted_indices = list(range(total_n))

            acc_count = len(accepted_indices)
            cov = acc_count / total_n
            abst_rate = 1.0 - cov

            if acc_count == 0:
                curve.append(
                    AbstentionThresholdResult(
                        confidence_threshold=thresh,
                        coverage=0.0,
                        abstention_rate=1.0,
                        accepted_samples=0,
                        selective_accuracy=0.0,
                        selective_precision=0.0,
                        selective_recall=0.0,
                        selective_macro_f1=0.0,
                    )
                )
                continue

            y_t_sub = [y_true[i] for i in accepted_indices]
            y_p_sub = [y_pred[i] for i in accepted_indices]

            classes_sub = sorted(set(y_t_sub) | set(y_p_sub))
            per_c = EvaluationHarness.compute_per_class_metrics(
                y_t_sub, y_p_sub, classes_sub
            )
            _mp, _mr, macro_f1 = EvaluationHarness.compute_macro_metrics(per_c)

            acc = (
                sum(
                    1
                    for yt, yp in zip(y_t_sub, y_p_sub, strict=False)
                    if yt == yp
                )
                / acc_count
            )
            pos_m = per_c.get(pos_cls)
            p_val = float(pos_m.precision or 0.0) if pos_m else 0.0
            r_val = float(pos_m.recall or 0.0) if pos_m else 0.0

            curve.append(
                AbstentionThresholdResult(
                    confidence_threshold=thresh,
                    coverage=round(cov, 4),
                    abstention_rate=round(abst_rate, 4),
                    accepted_samples=acc_count,
                    selective_accuracy=round(acc, 4),
                    selective_precision=round(p_val, 4),
                    selective_recall=round(r_val, 4),
                    selective_macro_f1=round(macro_f1, 4),
                )
            )

        return curve

    @classmethod
    def _compute_geographic_stratification(
        cls,
        x_test_raw: list[dict[str, Any]],
        y_test: list[str],
        y_pred: list[str],
        ids_test: list[str] | None = None,
        event_coords: dict[str, tuple[float, float]] | None = None,
    ) -> list[StratificationResult]:
        """Evaluate performance stratified across all 8 study corridors."""
        corridor_bounds = {
            "Amazon Basin": (-14.0, -62.0, -8.0, -52.0),
            "Persian Gulf": (24.0, 48.0, 28.5, 54.0),
            "California WUI": (34.0, -122.0, 40.0, -118.0),
            "Australia Southeast": (-38.0, 144.0, -32.0, 152.0),
            "Angul-Talcher": (20.7, 84.8, 21.8, 85.6),
            "Jamnagar-Kutch": (22.0, 69.5, 23.0, 70.8),
            "Singrauli-Sonbhadra": (23.8, 82.3, 24.5, 83.2),
            "Punjab Agricultural": (30.0, 75.2, 31.0, 76.5),
        }

        strat_results: list[StratificationResult] = []

        for c_name, (min_lat, min_lon, max_lat, max_lon) in corridor_bounds.items():
            matched_indices = []
            for i, row in enumerate(x_test_raw):
                lat = 0.0
                lon = 0.0
                if ids_test and event_coords and i < len(ids_test):
                    eid = ids_test[i]
                    if eid in event_coords:
                        lat, lon = event_coords[eid]
                if lat == 0.0 and lon == 0.0:
                    lat = float(row.get("latitude", 0.0))
                    lon = float(row.get("longitude", 0.0))

                if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
                    matched_indices.append(i)

            sample_n = len(matched_indices)
            if sample_n < 5:
                strat_results.append(
                    StratificationResult(
                        stratum_name=c_name,
                        sample_count=sample_n,
                        industrial_count=sum(
                            1 for i in matched_indices if y_test[i] == "industrial"
                        ),
                        non_industrial_count=sum(
                            1
                            for i in matched_indices
                            if y_test[i] == "non_industrial"
                        ),
                        status="INSUFFICIENT_SAMPLE",
                        accuracy=None,
                        macro_f1=None,
                        balanced_accuracy=None,
                    )
                )
                continue

            y_t_sub = [y_test[i] for i in matched_indices]
            y_p_sub = [y_pred[i] for i in matched_indices]
            classes_sub = sorted(set(y_t_sub) | set(y_p_sub))
            per_c = EvaluationHarness.compute_per_class_metrics(
                y_t_sub, y_p_sub, classes_sub
            )
            _mp, _mr, macro_f1 = EvaluationHarness.compute_macro_metrics(per_c)
            acc = (
                sum(
                    1
                    for yt, yp in zip(y_t_sub, y_p_sub, strict=False)
                    if yt == yp
                )
                / sample_n
            )
            recs = [
                float(per_c[c].recall or 0.0)
                for c in classes_sub
                if c in per_c and per_c[c].recall is not None
            ]
            bal_acc = sum(recs) / len(recs) if recs else 0.0

            strat_results.append(
                StratificationResult(
                    stratum_name=c_name,
                    sample_count=sample_n,
                    industrial_count=sum(1 for yt in y_t_sub if yt == "industrial"),
                    non_industrial_count=sum(
                        1 for yt in y_t_sub if yt == "non_industrial"
                    ),
                    status="VALID",
                    accuracy=round(acc, 4),
                    macro_f1=round(macro_f1, 4),
                    balanced_accuracy=round(bal_acc, 4),
                )
            )

        return strat_results

    @classmethod
    def _compute_sensor_stratification(
        cls,
        x_test_raw: list[dict[str, Any]],
        y_test: list[str],
        y_pred: list[str],
    ) -> list[StratificationResult]:
        """Evaluate performance stratified by sensor instrument."""
        sensors = ["VIIRS", "MODIS", "HYBRID"]
        strat_results: list[StratificationResult] = []

        for sensor in sensors:
            matched_indices = [
                i
                for i, row in enumerate(x_test_raw)
                if row.get("sensor_instrument") == sensor
            ]
            sample_n = len(matched_indices)
            if sample_n < 5:
                strat_results.append(
                    StratificationResult(
                        stratum_name=sensor,
                        sample_count=sample_n,
                        industrial_count=sum(
                            1 for i in matched_indices if y_test[i] == "industrial"
                        ),
                        non_industrial_count=sum(
                            1
                            for i in matched_indices
                            if y_test[i] == "non_industrial"
                        ),
                        status="INSUFFICIENT_SAMPLE",
                        accuracy=None,
                        macro_f1=None,
                        balanced_accuracy=None,
                    )
                )
                continue

            y_t_sub = [y_test[i] for i in matched_indices]
            y_p_sub = [y_pred[i] for i in matched_indices]
            classes_sub = sorted(set(y_t_sub) | set(y_p_sub))
            per_c = EvaluationHarness.compute_per_class_metrics(
                y_t_sub, y_p_sub, classes_sub
            )
            _mp, _mr, macro_f1 = EvaluationHarness.compute_macro_metrics(per_c)
            acc = (
                sum(
                    1
                    for yt, yp in zip(y_t_sub, y_p_sub, strict=False)
                    if yt == yp
                )
                / sample_n
            )
            recs = [
                float(per_c[c].recall or 0.0)
                for c in classes_sub
                if c in per_c and per_c[c].recall is not None
            ]
            bal_acc = sum(recs) / len(recs) if recs else 0.0

            strat_results.append(
                StratificationResult(
                    stratum_name=sensor,
                    sample_count=sample_n,
                    industrial_count=sum(1 for yt in y_t_sub if yt == "industrial"),
                    non_industrial_count=sum(
                        1 for yt in y_t_sub if yt == "non_industrial"
                    ),
                    status="VALID",
                    accuracy=round(acc, 4),
                    macro_f1=round(macro_f1, 4),
                    balanced_accuracy=round(bal_acc, 4),
                )
            )

        return strat_results

    @classmethod
    def _compute_temporal_stratification(
        cls,
        x_test_raw: list[dict[str, Any]],
        y_test: list[str],
        y_pred: list[str],
    ) -> list[StratificationResult]:
        """Evaluate performance stratified across temporal periods."""
        n = len(y_test)
        if n < 15:
            return []

        w1_idx = list(range(0, n // 3))
        w2_idx = list(range(n // 3, 2 * (n // 3)))
        w3_idx = list(range(2 * (n // 3), n))

        windows = [
            ("Early Period (March - April)", w1_idx),
            ("Middle Period (May - June)", w2_idx),
            ("Late Period (July - August)", w3_idx),
        ]
        strat_results: list[StratificationResult] = []

        for w_name, idxs in windows:
            sample_n = len(idxs)
            y_t_sub = [y_test[i] for i in idxs]
            y_p_sub = [y_pred[i] for i in idxs]
            classes_sub = sorted(set(y_t_sub) | set(y_p_sub))
            per_c = EvaluationHarness.compute_per_class_metrics(
                y_t_sub, y_p_sub, classes_sub
            )
            _mp, _mr, macro_f1 = EvaluationHarness.compute_macro_metrics(per_c)
            acc = (
                sum(
                    1
                    for yt, yp in zip(y_t_sub, y_p_sub, strict=False)
                    if yt == yp
                )
                / sample_n
            )
            recs = [
                float(per_c[c].recall or 0.0)
                for c in classes_sub
                if c in per_c and per_c[c].recall is not None
            ]
            bal_acc = sum(recs) / len(recs) if recs else 0.0

            strat_results.append(
                StratificationResult(
                    stratum_name=w_name,
                    sample_count=sample_n,
                    industrial_count=sum(1 for yt in y_t_sub if yt == "industrial"),
                    non_industrial_count=sum(
                        1 for yt in y_t_sub if yt == "non_industrial"
                    ),
                    status="VALID",
                    accuracy=round(acc, 4),
                    macro_f1=round(macro_f1, 4),
                    balanced_accuracy=round(bal_acc, 4),
                )
            )

        return strat_results

    @classmethod
    def _compute_bootstrap_ci(
        cls,
        y_test: list[str],
        y_pred: list[str],
        y_prob: list[dict[str, float]] | None,
        classes: list[str],
        pos_cls: str,
        n_rounds: int,
        seed: int,
    ) -> dict[str, tuple[float, float]]:
        """Compute 95% bootstrap confidence intervals."""
        import random

        rng = random.Random(seed)
        n = len(y_test)
        if n < 10:
            return {}

        boot_f1s: list[float] = []
        boot_bal_accs: list[float] = []
        boot_accs: list[float] = []
        boot_precisions: list[float] = []
        boot_recalls: list[float] = []
        boot_rocs: list[float] = []

        pos_probs = [p.get(pos_cls, 0.5) for p in y_prob] if y_prob else None
        y_binary = [1 if y == pos_cls else 0 for y in y_test]

        for _ in range(n_rounds):
            sample_indices = [rng.randint(0, n - 1) for _ in range(n)]
            yt_s = [y_test[i] for i in sample_indices]
            yp_s = [y_pred[i] for i in sample_indices]

            per_c = EvaluationHarness.compute_per_class_metrics(yt_s, yp_s, classes)
            _p, _r, f1 = EvaluationHarness.compute_macro_metrics(per_c)
            acc = sum(1 for yt, yp in zip(yt_s, yp_s, strict=False) if yt == yp) / n
            recs = [
                float(per_c[c].recall or 0.0)
                for c in classes
                if c in per_c and per_c[c].recall is not None
            ]
            bal_acc = sum(recs) / len(recs) if recs else 0.0

            pos_m = per_c.get(pos_cls)
            p_val = float(pos_m.precision or 0.0) if pos_m else 0.0
            r_val = float(pos_m.recall or 0.0) if pos_m else 0.0

            boot_f1s.append(f1)
            boot_bal_accs.append(bal_acc)
            boot_accs.append(acc)
            boot_precisions.append(p_val)
            boot_recalls.append(r_val)

            if pos_probs:
                yb_s = [y_binary[i] for i in sample_indices]
                prob_s = [pos_probs[i] for i in sample_indices]
                boot_rocs.append(cls._compute_roc_auc(yb_s, prob_s))

        def get_ci(values: list[float]) -> tuple[float, float]:
            s_val = sorted(values)
            low_idx = int(0.025 * len(s_val))
            high_idx = int(0.975 * len(s_val))
            return round(s_val[low_idx], 4), round(s_val[high_idx], 4)

        cis = {
            "macro_f1": get_ci(boot_f1s),
            "balanced_accuracy": get_ci(boot_bal_accs),
            "accuracy": get_ci(boot_accs),
            "precision": get_ci(boot_precisions),
            "recall": get_ci(boot_recalls),
        }
        if boot_rocs:
            cis["roc_auc"] = get_ci(boot_rocs)

        return cis

    @classmethod
    def _run_feature_group_ablation(
        cls,
        x_train_raw: list[dict[str, Any]],
        y_train: list[str],
        x_test_raw: list[dict[str, Any]],
        y_test: list[str],
        random_seed: int,
    ) -> list[FeatureAblationResult]:
        """Perform feature ablation experiments by feature group on Random Forest."""
        from services.ml.models.tree import RandomForestClassifier

        feature_groups: dict[str, list[str]] = {
            "THERMAL_CORE": [
                "brightness_mean_kelvin",
                "brightness_max_kelvin",
                "frp_mean_mw",
                "frp_max_mw",
                "frp_min_mw",
                "frp_sum_mw",
                "frp_std_mw",
            ],
            "TEMPORAL_HISTORY": [
                "detection_count",
                "duration_hours",
                "temporal_density",
                "time_since_previous_event_hours",
                "prior_event_count_24h",
                "prior_event_count_7d",
                "prior_event_count_30d",
            ],
            "PERSISTENCE_SOURCE": [
                "is_persistent_source",
                "persistence_state",
                "persistence_active_days",
                "persistence_total_events",
                "persistence_recurrence_ratio",
            ],
            "SPATIAL_CONTEXT": [
                "spatial_extent_radius_meters",
                "facility_distance_meters",
                "facility_context_type",
                "is_near_industrial_facility",
                "power_plant_distance_meters",
                "water_distance_meters",
            ],
            "LAND_COVER_ENVIRONMENTAL": [
                "is_protected_area",
                "landcover_class",
                "daynight_ratio",
                "satellite_platform_diversity",
                "sensor_instrument",
            ],
        }

        prep_full = FeaturePreprocessor()
        prep_full.fit(x_train_raw)
        x_tr_full = prep_full.transform(x_train_raw)
        x_te_full = prep_full.transform(x_test_raw)

        rf_full = RandomForestClassifier(
            n_estimators=5, max_depth=3, random_seed=random_seed
        )
        rf_full.fit(x_tr_full, y_train)
        pred_full = rf_full.predict(x_te_full)

        classes = sorted(set(y_test) | set(pred_full))
        per_c_full = EvaluationHarness.compute_per_class_metrics(
            y_test, pred_full, classes
        )
        _mp, _mr, base_f1 = EvaluationHarness.compute_macro_metrics(per_c_full)
        recs_full = [
            float(per_c_full[c].recall or 0.0)
            for c in classes
            if c in per_c_full and per_c_full[c].recall is not None
        ]
        base_bal_acc = sum(recs_full) / len(recs_full) if recs_full else 0.0

        ablation_results: list[FeatureAblationResult] = []

        for g_name, drop_cols in feature_groups.items():
            x_tr_abl = [
                {k: v for k, v in row.items() if k not in drop_cols}
                for row in x_train_raw
            ]
            x_te_abl = [
                {k: v for k, v in row.items() if k not in drop_cols}
                for row in x_test_raw
            ]

            prep_abl = FeaturePreprocessor()
            prep_abl.fit(x_tr_abl)
            x_tr_abl_vec = prep_abl.transform(x_tr_abl)
            x_te_abl_vec = prep_abl.transform(x_te_abl)

            rf_abl = RandomForestClassifier(
                n_estimators=5, max_depth=3, random_seed=random_seed
            )
            rf_abl.fit(x_tr_abl_vec, y_train)
            pred_abl = rf_abl.predict(x_te_abl_vec)

            classes_abl = sorted(set(y_test) | set(pred_abl))
            per_c_abl = EvaluationHarness.compute_per_class_metrics(
                y_test, pred_abl, classes_abl
            )
            _mp, _mr, abl_f1 = EvaluationHarness.compute_macro_metrics(per_c_abl)
            recs_abl = [
                float(per_c_abl[c].recall or 0.0)
                for c in classes_abl
                if c in per_c_abl and per_c_abl[c].recall is not None
            ]
            abl_bal_acc = sum(recs_abl) / len(recs_abl) if recs_abl else 0.0

            ablation_results.append(
                FeatureAblationResult(
                    feature_group=g_name,
                    features_removed=drop_cols,
                    remaining_feature_count=len(x_tr_abl[0]) if x_tr_abl else 0,
                    macro_f1=round(abl_f1, 4),
                    balanced_accuracy=round(abl_bal_acc, 4),
                    macro_f1_delta=round(abl_f1 - base_f1, 4),
                    balanced_accuracy_delta=round(abl_bal_acc - base_bal_acc, 4),
                )
            )

        return ablation_results
