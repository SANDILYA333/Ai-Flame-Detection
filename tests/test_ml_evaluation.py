"""Unit tests for evaluation harness, calibration contracts, and abstention engine."""

import math

from packages.schemas.ml import (
    AbstentionContract,
    AbstentionReason,
    SplitPartition,
)
from services.ml.calibration.abstention import AbstentionDecisionEngine
from services.ml.calibration.contract import CalibrationManager
from services.ml.evaluation.harness import EvaluationHarness


class TestMLEvaluationAndCalibration:
    """Test suite validating evaluation metrics, calibration, and abstention."""

    def test_confusion_matrix_and_per_class_metrics(self) -> None:
        """Harness computes confusion matrix and per-class precision/recall/F1."""
        y_true = ["flare", "flare", "fire", "fire", "unknown"]
        y_pred = ["flare", "fire", "fire", "fire", "unknown"]
        labels = ["fire", "flare", "unknown"]

        cm = EvaluationHarness.compute_confusion_matrix(y_true, y_pred, labels)
        assert cm == [
            [2, 0, 0],
            [1, 1, 0],
            [0, 0, 1],
        ]

        per_class = EvaluationHarness.compute_per_class_metrics(y_true, y_pred, labels)

        # Fire: TP=2, FP=1, FN=0 -> Precision = 2/3, Recall = 2/2 = 1.0
        assert per_class["fire"].true_positives == 2
        assert per_class["fire"].false_positives == 1
        assert per_class["fire"].false_negatives == 0
        assert math.isclose(per_class["fire"].precision or 0.0, 2 / 3, rel_tol=1e-3)
        assert math.isclose(per_class["fire"].recall or 0.0, 1.0, rel_tol=1e-3)

        # Flare: TP=1, FP=0, FN=1 -> Precision = 1.0, Recall = 1/2 = 0.5
        assert per_class["flare"].true_positives == 1
        assert per_class["flare"].false_positives == 0
        assert per_class["flare"].false_negatives == 1
        assert math.isclose(per_class["flare"].precision or 0.0, 1.0, rel_tol=1e-3)
        assert math.isclose(per_class["flare"].recall or 0.0, 0.5, rel_tol=1e-3)

    def test_evaluate_predictions_end_to_end(self) -> None:
        """Full evaluation pipeline generates structured EvaluationReport."""
        y_true = ["flare", "fire", "flare", "fire"]
        y_pred = ["flare", "fire", "flare", "flare"]
        y_prob = [
            {"flare": 0.9, "fire": 0.1},
            {"flare": 0.2, "fire": 0.8},
            {"flare": 0.85, "fire": 0.15},
            {"flare": 0.6, "fire": 0.4},
        ]

        report = EvaluationHarness.evaluate_predictions(
            evaluation_id="eval_001",
            experiment_id="exp_baseline_b0",
            dataset_id="ds_jamnagar_v1",
            dataset_version="v1.0.0",
            model_id="baseline_prior",
            model_version="v1.0",
            split_partition=SplitPartition.TEST,
            y_true=y_true,
            y_pred=y_pred,
            y_prob=y_prob,
        )

        assert report.evaluation_id == "eval_001"
        assert report.accuracy == 0.75  # 3 of 4 correct
        assert report.brier_score is not None
        assert report.brier_score >= 0.0
        assert report.log_loss is not None
        assert report.total_samples == 4
        assert report.evaluated_samples == 4
        assert report.abstained_samples == 0

    def test_calibration_manager_computes_ece_and_mce(self) -> None:
        """CalibrationManager computes calibration error across probability bins."""
        y_true = [1, 1, 0, 0]
        y_prob = [0.95, 0.90, 0.10, 0.05]

        ece, mce = CalibrationManager.compute_calibration_error(
            y_true, y_prob, n_bins=10
        )
        assert ece >= 0.0
        assert mce >= 0.0
        assert ece < 0.20

    def test_abstention_decision_engine(self) -> None:
        """AbstentionDecisionEngine evaluates confidence, uncertainty, completeness."""
        contract = AbstentionContract(
            abstention_id="abs_contract_v1",
            confidence_threshold=0.70,
            uncertainty_threshold=0.30,
            require_evidence_completeness=True,
            min_completeness_ratio=0.80,
            allow_abstention=True,
        )

        # 1. High confidence, complete evidence -> No abstention
        abs_1, reason_1 = AbstentionDecisionEngine.evaluate_abstention(
            confidence=0.85,
            uncertainty=0.10,
            evidence_completeness_ratio=1.0,
            contract=contract,
        )
        assert abs_1 is False
        assert reason_1 == AbstentionReason.NONE

        # 2. Incomplete evidence -> Abstention
        abs_2, reason_2 = AbstentionDecisionEngine.evaluate_abstention(
            confidence=0.90,
            uncertainty=0.10,
            evidence_completeness_ratio=0.50,  # Below 0.80
            contract=contract,
        )
        assert abs_2 is True
        assert reason_2 == AbstentionReason.INSUFFICIENT_EVIDENCE

        # 3. Low confidence -> Abstention
        abs_3, reason_3 = AbstentionDecisionEngine.evaluate_abstention(
            confidence=0.55,  # Below 0.70
            uncertainty=0.10,
            evidence_completeness_ratio=1.0,
            contract=contract,
        )
        assert abs_3 is True
        assert reason_3 == AbstentionReason.LOW_CONFIDENCE

    def test_coverage_and_selective_risk(self) -> None:
        """Calculates coverage and selective risk on non-abstained."""
        y_true = ["flare", "fire", "fire", "flare"]
        y_pred = ["flare", "fire", "flare", "fire"]
        abstain = [False, False, True, True]

        coverage, risk = AbstentionDecisionEngine.compute_coverage_and_selective_risk(
            y_true=y_true,
            y_pred=y_pred,
            abstention_flags=abstain,
        )

        assert coverage == 0.50
        assert risk == 0.0  # Zero errors on non-abstained samples
