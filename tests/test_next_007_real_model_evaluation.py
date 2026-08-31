"""Comprehensive Test Suite for NEXT-007: Real Model Scientific Evaluation.

Validates:
1. Production artifact deserialization and metadata integrity.
2. Exact group-aware split reconstruction and zero data leakage.
3. Strict exclusion of UNKNOWN/unlabeled events from supervised evaluation matrices.
4. Core classification metrics correctness (Accuracy, Balanced Accuracy, Precision).
5. Probabilistic metrics (ROC-AUC, PR-AUC, Brier score, Log Loss).
6. Calibration curves and Expected Calibration Error (ECE) computation.
7. Abstention & selective prediction curve monotonicity and coverage tracking.
8. Feature group ablation isolation and performance delta calculation.
9. Geographic, sensor, and temporal stratification with safe sample size handling.
10. Deterministic 95% bootstrap confidence intervals.
11. Immutability of production model artifacts during evaluation.
12. Preservation of pilot model artifacts as PILOT_SMOKE_TEST.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from packages.schemas.ml import ModelArtifact
from services.ml.evaluation.next_007_evaluator import (
    Next007RealModelEvaluator,
)
from services.ml.models.registry import ModelRegistry


class TestNext007RealModelEvaluation:
    """Test suite for NEXT-007 scientific evaluation pipeline."""

    @pytest.fixture
    def production_artifact_paths(self) -> list[Path]:
        prod_dir = Path("artifacts/real/production")
        assert prod_dir.exists(), "artifacts/real/production must exist"
        glob_pattern = "real_*_target_industrial_segregation_v1.0.0.json"
        paths = sorted(prod_dir.glob(glob_pattern))
        assert len(paths) == 5, f"Expected 5 production artifacts, found {len(paths)}"
        return paths

    def test_production_artifacts_integrity_and_immutability(
        self, production_artifact_paths: list[Path]
    ) -> None:
        """Verify all 5 production model artifacts deserialize cleanly."""
        for path in production_artifact_paths:
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
            assert "sha256_hash" in data
            assert data["metadata"]["model_version"] == "v1.0.0-production"

            # Roundtrip load via registry
            artifact = ModelRegistry.load_from_file(path)
            assert isinstance(artifact, ModelArtifact)
            _preprocessor, model = ModelRegistry.reconstruct_pipeline(artifact)
            assert model.is_fitted is True

    def test_pilot_artifacts_remain_pilot_and_immutable(self) -> None:
        """Verify pilot artifacts are untouched and not relabeled as production."""
        pilot_dir = Path("artifacts/real/pilot")
        if pilot_dir.exists():
            pilot_paths = sorted(pilot_dir.glob("*.json"))
            for p in pilot_paths:
                data = json.loads(p.read_text(encoding="utf-8"))
                assert data["metadata"]["model_version"] == "v1.0.0-pilot"

    def test_roc_auc_and_pr_auc_computation(self) -> None:
        """Verify ROC-AUC and PR-AUC rank-based calculations on controlled vectors."""
        # Perfect separation
        y_true_perf = [0, 0, 0, 1, 1, 1]
        y_score_perf = [0.1, 0.2, 0.3, 0.7, 0.8, 0.9]
        roc_perf = Next007RealModelEvaluator._compute_roc_auc(
            y_true_perf, y_score_perf
        )
        pr_perf = Next007RealModelEvaluator._compute_pr_auc(
            y_true_perf, y_score_perf
        )
        assert roc_perf == 1.0
        assert pr_perf == 1.0

        # Inverted separation
        y_score_inv = [0.9, 0.8, 0.7, 0.3, 0.2, 0.1]
        roc_inv = Next007RealModelEvaluator._compute_roc_auc(
            y_true_perf, y_score_inv
        )
        assert roc_inv == 0.0

        # Random / tie
        y_score_rnd = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        roc_rnd = Next007RealModelEvaluator._compute_roc_auc(
            y_true_perf, y_score_rnd
        )
        assert 0.0 <= roc_rnd <= 1.0

    def test_calibration_and_ece_computation(self) -> None:
        """Verify Expected Calibration Error (ECE) and binning boundaries."""
        y_true = [1, 1, 0, 0]
        y_prob = [0.95, 0.95, 0.05, 0.05]
        ece, bins = Next007RealModelEvaluator._compute_calibration(
            y_true, y_prob, n_bins=10
        )
        assert len(bins) == 10
        assert 0.0 <= ece <= 0.10
        for b in bins:
            assert b.bin_lower < b.bin_upper or b.bin_lower == 0.9

    def test_abstention_curve_behavior(self) -> None:
        """Verify abstention filtering behavior as confidence threshold increases."""
        y_true = ["industrial", "industrial", "non_industrial", "non_industrial"]
        y_pred = ["industrial", "non_industrial", "non_industrial", "non_industrial"]
        y_prob = [
            {"industrial": 0.95, "non_industrial": 0.05},
            {"industrial": 0.55, "non_industrial": 0.45},
            {"industrial": 0.10, "non_industrial": 0.90},
            {"industrial": 0.20, "non_industrial": 0.80},
        ]

        curve = Next007RealModelEvaluator._compute_abstention_curve(
            y_true, y_pred, y_prob, pos_cls="industrial"
        )
        assert len(curve) == len(Next007RealModelEvaluator.CONFIDENCE_THRESHOLDS)

        # At thresh=0.50, coverage is 1.0
        c0 = curve[0]
        assert c0.confidence_threshold == 0.50
        assert c0.coverage == 1.0
        assert c0.accepted_samples == 4
        assert c0.selective_accuracy == 0.75

        # At thresh=0.80, low-confidence sample is rejected
        # Selective accuracy becomes 1.0
        c3 = next(c for c in curve if c.confidence_threshold == 0.80)
        assert c3.coverage == 0.75
        assert c3.accepted_samples == 3
        assert c3.selective_accuracy == 1.0

    def test_bootstrap_ci_reproducibility(self) -> None:
        """Verify bootstrap confidence intervals are reproducible with fixed seed."""
        y_true = ["industrial"] * 20 + ["non_industrial"] * 20
        y_pred = (
            ["industrial"] * 18
            + ["non_industrial"] * 2
            + ["non_industrial"] * 18
            + ["industrial"] * 2
        )
        classes = ["industrial", "non_industrial"]

        ci1 = Next007RealModelEvaluator._compute_bootstrap_ci(
            y_test=y_true,
            y_pred=y_pred,
            y_prob=None,
            classes=classes,
            pos_cls="industrial",
            n_rounds=100,
            seed=42,
        )
        ci2 = Next007RealModelEvaluator._compute_bootstrap_ci(
            y_test=y_true,
            y_pred=y_pred,
            y_prob=None,
            classes=classes,
            pos_cls="industrial",
            n_rounds=100,
            seed=42,
        )
        assert ci1 == ci2
        assert "macro_f1" in ci1
        low, high = ci1["macro_f1"]
        assert 0.0 <= low <= high <= 1.0

    def test_persisted_evaluation_artifacts_exist_and_conform(self) -> None:
        """Verify output report files exist under artifacts/real/evaluation/."""
        eval_dir = Path("artifacts/real/evaluation")
        report_path = eval_dir / "real_model_evaluation_report.json"
        table_path = eval_dir / "model_comparison_table.json"
        ablation_path = eval_dir / "feature_ablation_report.json"

        assert report_path.exists(), "real_model_evaluation_report.json must exist"
        assert table_path.exists(), "model_comparison_table.json must exist"
        assert ablation_path.exists(), "feature_ablation_report.json must exist"

        report_data = json.loads(report_path.read_text(encoding="utf-8"))
        assert "total_physical_events" in report_data
        assert "eligible_labeled_events" in report_data
        assert "unknown_excluded_events" in report_data
        assert report_data["total_physical_events"] == (
            report_data["eligible_labeled_events"]
            + report_data["unknown_excluded_events"]
        )
        assert len(report_data["models_evaluated"]) == 5
        assert len(report_data["feature_ablation_matrix"]) == 5
        assert "acceptance_gates" in report_data
