"""Evaluation harness and multi-class metrics computation for Phase 4 ML.

Provides rigorous, leak-free evaluation reporting:
- Per-class precision, recall, F1, and support
- Confusion matrix and macro-averaged metrics
- Probabilistic scoring (Brier score, multi-class log loss)
- Selective classification / abstention metrics
"""

import math
from datetime import UTC, datetime

from packages.schemas.ml import (
    EvaluationReport,
    PerClassEvaluationMetrics,
    SplitPartition,
)


class EvaluationHarness:
    """Harness computing structured metrics across models and baselines."""

    @staticmethod
    def extract_class_labels(
        y_true: list[str],
        y_pred: list[str],
        explicit_vocabulary: list[str] | None = None,
    ) -> list[str]:
        """Derive sorted unique class labels from vocabulary and predictions."""
        if explicit_vocabulary:
            return sorted(set(explicit_vocabulary))
        all_labels = set(y_true) | set(y_pred)
        return sorted(all_labels)

    @staticmethod
    def compute_confusion_matrix(
        y_true: list[str],
        y_pred: list[str],
        class_labels: list[str],
    ) -> list[list[int]]:
        """Compute confusion matrix: rows are true, columns are predictions."""
        label_to_idx = {label: i for i, label in enumerate(class_labels)}
        n_classes = len(class_labels)
        matrix = [[0 for _ in range(n_classes)] for _ in range(n_classes)]

        for true_val, pred_val in zip(y_true, y_pred, strict=False):
            if true_val in label_to_idx and pred_val in label_to_idx:
                r = label_to_idx[true_val]
                c = label_to_idx[pred_val]
                matrix[r][c] += 1

        return matrix

    @classmethod
    def compute_per_class_metrics(
        cls,
        y_true: list[str],
        y_pred: list[str],
        class_labels: list[str],
    ) -> dict[str, PerClassEvaluationMetrics]:
        """Compute precision, recall, F1, and confusion counts for each class."""
        cm = cls.compute_confusion_matrix(y_true, y_pred, class_labels)
        total_samples = len(y_true)
        metrics: dict[str, PerClassEvaluationMetrics] = {}

        for i, cls_name in enumerate(class_labels):
            tp = cm[i][i]
            fp = sum(cm[r][i] for r in range(len(class_labels)) if r != i)
            fn = sum(cm[i][c] for c in range(len(class_labels)) if c != i)
            tn = total_samples - (tp + fp + fn)
            support = tp + fn

            precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
            recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
            f1 = (
                float(2 * precision * recall / (precision + recall))
                if (precision + recall) > 0
                else 0.0
            )

            metrics[cls_name] = PerClassEvaluationMetrics(
                class_name=cls_name,
                true_positives=tp,
                false_positives=fp,
                false_negatives=fn,
                true_negatives=tn,
                support=support,
                precision=precision,
                recall=recall,
                f1_score=f1,
            )

        return metrics

    @staticmethod
    def compute_macro_metrics(
        per_class: dict[str, PerClassEvaluationMetrics],
    ) -> tuple[float, float, float]:
        """Compute unweighted macro-averaged precision, recall, and F1."""
        if not per_class:
            return 0.0, 0.0, 0.0

        precisions = [
            m.precision for m in per_class.values() if m.precision is not None
        ]
        recalls = [m.recall for m in per_class.values() if m.recall is not None]
        f1s = [m.f1_score for m in per_class.values() if m.f1_score is not None]

        macro_p = float(sum(precisions) / len(precisions)) if precisions else 0.0
        macro_r = float(sum(recalls) / len(recalls)) if recalls else 0.0
        macro_f1 = float(sum(f1s) / len(f1s)) if f1s else 0.0

        return macro_p, macro_r, macro_f1

    @staticmethod
    def compute_balanced_accuracy(
        per_class: dict[str, PerClassEvaluationMetrics],
    ) -> float:
        """Compute balanced accuracy across classes with positive support."""
        supported_recalls = [
            m.recall
            for m in per_class.values()
            if m.support > 0 and m.recall is not None
        ]
        if not supported_recalls:
            return 0.0
        return float(sum(supported_recalls) / len(supported_recalls))

    @staticmethod
    def compute_accuracy(y_true: list[str], y_pred: list[str]) -> float:
        """Compute standard overall accuracy."""
        if not y_true:
            return 0.0
        correct = sum(1 for t, p in zip(y_true, y_pred, strict=False) if t == p)
        return float(correct / len(y_true))

    @staticmethod
    def compute_brier_score(
        y_true: list[str],
        y_prob: list[dict[str, float]],
        class_labels: list[str],
    ) -> float:
        """Compute multi-class Brier score: MSE between probs and 1-hot targets."""
        if not y_true or not y_prob:
            return 0.0

        total_sq_error = 0.0
        for true_label, prob_dict in zip(y_true, y_prob, strict=False):
            for cls_name in class_labels:
                p = prob_dict.get(cls_name, 0.0)
                y_bin = 1.0 if true_label == cls_name else 0.0
                total_sq_error += (p - y_bin) ** 2

        return float(total_sq_error / len(y_true))

    @staticmethod
    def compute_log_loss(
        y_true: list[str],
        y_prob: list[dict[str, float]],
        eps: float = 1e-15,
    ) -> float:
        """Compute multi-class cross-entropy log loss."""
        if not y_true or not y_prob:
            return 0.0

        total_loss = 0.0
        for true_label, prob_dict in zip(y_true, y_prob, strict=False):
            p = prob_dict.get(true_label, 0.0)
            p_clipped = max(eps, min(1.0 - eps, p))
            total_loss -= math.log(p_clipped)

        return float(total_loss / len(y_true))

    @classmethod
    def evaluate_predictions(
        cls,
        evaluation_id: str,
        experiment_id: str,
        dataset_id: str,
        dataset_version: str,
        model_id: str,
        model_version: str,
        split_partition: SplitPartition,
        y_true: list[str],
        y_pred: list[str],
        y_prob: list[dict[str, float]] | None = None,
        abstention_flags: list[bool] | None = None,
        class_labels: list[str] | None = None,
    ) -> EvaluationReport:
        """Evaluate model predictions, computing per-class and aggregate metrics."""
        total_samples = len(y_true)
        if total_samples != len(y_pred):
            raise ValueError(
                f"Length mismatch: y_true ({len(y_true)}) != y_pred ({len(y_pred)})."
            )

        # Handle abstentions
        abstained_count = 0
        eval_true: list[str] = []
        eval_pred: list[str] = []
        eval_prob: list[dict[str, float]] | None = [] if y_prob is not None else None

        if abstention_flags:
            for i, is_abstained in enumerate(abstention_flags):
                if is_abstained:
                    abstained_count += 1
                else:
                    eval_true.append(y_true[i])
                    eval_pred.append(y_pred[i])
                    if y_prob is not None and eval_prob is not None:
                        eval_prob.append(y_prob[i])
        else:
            eval_true = y_true
            eval_pred = y_pred
            eval_prob = y_prob

        evaluated_count = len(eval_true)
        abstention_rate = (
            float(abstained_count / total_samples) if total_samples > 0 else 0.0
        )

        labels = cls.extract_class_labels(y_true, y_pred, class_labels)
        cm = cls.compute_confusion_matrix(eval_true, eval_pred, labels)
        per_class = cls.compute_per_class_metrics(eval_true, eval_pred, labels)
        macro_p, macro_r, macro_f1 = cls.compute_macro_metrics(per_class)
        balanced_acc = cls.compute_balanced_accuracy(per_class)
        acc = cls.compute_accuracy(eval_true, eval_pred)

        brier: float | None = None
        logloss: float | None = None
        if eval_prob:
            brier = cls.compute_brier_score(eval_true, eval_prob, labels)
            logloss = cls.compute_log_loss(eval_true, eval_prob)

        return EvaluationReport(
            evaluation_id=evaluation_id,
            experiment_id=experiment_id,
            dataset_id=dataset_id,
            dataset_version=dataset_version,
            model_id=model_id,
            model_version=model_version,
            split_partition_evaluated=split_partition,
            accuracy=acc,
            balanced_accuracy=balanced_acc,
            macro_precision=macro_p,
            macro_recall=macro_r,
            macro_f1=macro_f1,
            brier_score=brier,
            log_loss=logloss,
            per_class_metrics=per_class,
            confusion_matrix=cm,
            class_labels=labels,
            total_samples=total_samples,
            evaluated_samples=evaluated_count,
            abstained_samples=abstained_count,
            abstention_rate=abstention_rate,
            created_at=datetime.now(UTC),
        )
