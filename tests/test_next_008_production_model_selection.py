"""Test Suite for NEXT-008: Production Model Selection & Deployment Policy.

Verifies:
1. Candidate model eligibility and multi-criteria scientific assessment.
2. Operating mode resolution (HIGH_PRECISION, HIGH_RECALL, SELECTIVE).
3. Confidence threshold boundary evaluation (>=, <, ==).
4. Selective abstention and review routing.
5. Invariant preservation: UNKNOWN != NON_INDUSTRIAL.
6. Artifact security and pilot artifact rejection.
7. Decision determinism and cryptographic provenance traceability.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from packages.schemas.ml import ModelArtifact
from services.ml.deployment.policy import (
    ModelEligibilityStatus,
    ProductionDeploymentPolicyService,
    ProductionOperatingMode,
)
from services.ml.models.registry import ModelRegistry


class TestNext008ProductionModelSelection:
    """Test suite for NEXT-008 production model selection policies."""

    @pytest.fixture(scope="class")
    @classmethod
    def deployment_decision(cls) -> Any:
        """Generate or load the authoritative production deployment decision."""
        eval_path = Path("artifacts/real/evaluation/real_model_evaluation_report.json")
        out_path = Path("artifacts/real/deployment/production_model_selection.json")
        return (
            ProductionDeploymentPolicyService.evaluate_and_generate_deployment_decision(
                evaluation_report_path=eval_path,
                production_artifact_dir="artifacts/real/production",
                output_path=out_path,
            )
        )

    def test_candidate_model_eligibility_and_hard_constraints(
        self, deployment_decision: Any
    ) -> None:
        """Verify model candidate assessments and hard constraint evaluation."""
        assessments = {
            a.model_type: a for a in deployment_decision.candidate_assessments
        }

        # 1. Baselines must be rejected
        b0 = assessments["MajorityClassClassifier"]
        assert b0.eligibility_status == ModelEligibilityStatus.MODEL_REJECTED
        assert b0.passed_hard_constraints is False
        assert len(b0.failed_criteria) > 0

        b2 = assessments["DeterministicContextualClassifier"]
        assert b2.eligibility_status == ModelEligibilityStatus.MODEL_REJECTED
        assert b2.passed_hard_constraints is False

        # 2. DecisionTree must be RECOMMENDED (100% precision, Macro-F1 >= 0.75)
        dt = assessments["DecisionTreeClassifier"]
        assert dt.eligibility_status == ModelEligibilityStatus.MODEL_RECOMMENDED
        assert dt.passed_hard_constraints is True
        assert dt.precision == 1.0000
        assert dt.macro_f1 >= 0.75
        assert (
            dt.expected_calibration_error is not None
            and dt.expected_calibration_error <= 0.15
        )

        # 3. LogisticRegression must be RECOMMENDED (high recall candidate)
        lr = assessments["LogisticRegressionClassifier"]
        assert lr.eligibility_status == ModelEligibilityStatus.MODEL_RECOMMENDED
        assert lr.passed_hard_constraints is True
        assert lr.recall >= 0.70  # Captures 79.84%

        # 4. RandomForest must record ECE failure and be ELIGIBLE
        rf = assessments["RandomForestClassifier"]
        assert rf.eligibility_status == ModelEligibilityStatus.MODEL_ELIGIBLE
        assert rf.passed_hard_constraints is False
        assert any("ECE" in c for c in rf.failed_criteria)

    def test_operating_modes_resolution(self) -> None:
        """Verify all operating modes resolve to appropriate, validated engines."""
        # 1. HIGH_PRECISION mode
        engine_hp, policy_hp = (
            ProductionDeploymentPolicyService.resolve_production_model(
                ProductionOperatingMode.HIGH_PRECISION
            )
        )
        assert engine_hp.artifact.metadata.model_type == "DecisionTreeClassifier"
        assert policy_hp.confidence_threshold == 0.70
        assert policy_hp.expected_metrics["precision"] == 1.0000

        # 2. HIGH_RECALL mode
        engine_hr, policy_hr = (
            ProductionDeploymentPolicyService.resolve_production_model(
                ProductionOperatingMode.HIGH_RECALL
            )
        )
        assert (
            engine_hr.artifact.metadata.model_type
            == "LogisticRegressionClassifier"
        )
        assert policy_hr.confidence_threshold == 0.50
        assert policy_hr.expected_metrics["recall"] >= 0.70

        # 3. SELECTIVE mode
        engine_sel, policy_sel = (
            ProductionDeploymentPolicyService.resolve_production_model(
                ProductionOperatingMode.SELECTIVE
            )
        )
        assert engine_sel.artifact.metadata.model_type == "DecisionTreeClassifier"
        assert policy_sel.confidence_threshold == 0.80
        assert policy_sel.coverage_estimate == 0.782

    def test_confidence_threshold_boundary_evaluation(self) -> None:
        """Test strict threshold boundary conditions (>=, <, ==)."""
        # Case 1: Confidence strictly above threshold
        res_above = ProductionDeploymentPolicyService.apply_confidence_policy(
            predicted_class="industrial",
            confidence=0.85,
            mode=ProductionOperatingMode.SELECTIVE,
        )
        assert res_above["authorized_class"] == "industrial"
        assert res_above["is_abstained"] is False
        assert res_above["review_required"] is False

        # Case 2: Confidence strictly below threshold
        res_below = ProductionDeploymentPolicyService.apply_confidence_policy(
            predicted_class="industrial",
            confidence=0.75,
            mode=ProductionOperatingMode.SELECTIVE,  # threshold is 0.80
        )
        assert res_below["authorized_class"] == "unknown"
        assert res_below["is_abstained"] is True
        assert res_below["review_required"] is True

        # Case 3: Confidence exactly equal to threshold
        res_equal = ProductionDeploymentPolicyService.apply_confidence_policy(
            predicted_class="industrial",
            confidence=0.80,
            mode=ProductionOperatingMode.SELECTIVE,
        )
        assert res_equal["authorized_class"] == "industrial"
        assert res_equal["is_abstained"] is False
        assert res_equal["review_required"] is False

    def test_unknown_is_not_non_industrial_invariant(self) -> None:
        """CRITICAL INVARIANT: Abstained events must NEVER become non_industrial."""
        for conf in [0.10, 0.45, 0.60, 0.69]:
            res = ProductionDeploymentPolicyService.apply_confidence_policy(
                predicted_class="industrial",
                confidence=conf,
                mode=ProductionOperatingMode.HIGH_PRECISION,
            )
            assert res["authorized_class"] == "unknown"
            assert res["authorized_class"] != "non_industrial"
            assert res["is_abstained"] is True

    def test_security_audit_rejects_pilot_and_invalid_artifacts(self) -> None:
        """Verify safety auditor rejects pilot artifacts and schema mismatches."""
        pilot_path = Path(
            "artifacts/real/pilot/"
            "pilot_decisiontreeclassifier_target_industrial_segregation_v1.0.0.json"
        )
        if pilot_path.exists():
            pilot_artifact = ModelRegistry.load_from_file(pilot_path)
            with pytest.raises(ValueError, match="Security Violation"):
                ProductionDeploymentPolicyService.audit_artifact_safety(
                    pilot_artifact
                )

        # Test schema incompatibility rejection
        prod_path = Path(
            "artifacts/real/production/"
            "real_decisiontreeclassifier_target_industrial_segregation_v1.0.0.json"
        )
        prod_artifact = ModelRegistry.load_from_file(prod_path)
        # Verify valid production artifact passes cleanly
        ProductionDeploymentPolicyService.audit_artifact_safety(prod_artifact)

        # Mutate feature version and verify rejection
        invalid_metadata = prod_artifact.metadata.model_copy(
            update={"feature_set_version": "invalid_v9.9.9"}
        )
        invalid_artifact = ModelArtifact(
            metadata=invalid_metadata,
            preprocessor_state=prod_artifact.preprocessor_state,
            model_parameters=prod_artifact.model_parameters,
            class_vocabulary=prod_artifact.class_vocabulary,
        )
        with pytest.raises(ValueError, match="Schema Incompatibility"):
            ProductionDeploymentPolicyService.audit_artifact_safety(
                invalid_artifact
            )

    def test_decision_artifact_reproducibility_and_determinism(self) -> None:
        """Verify decision generation is strictly deterministic and idempotent."""
        eval_path = Path(
            "artifacts/real/evaluation/real_model_evaluation_report.json"
        )
        svc = ProductionDeploymentPolicyService
        p1 = svc.evaluate_and_generate_deployment_decision(
            evaluation_report_path=eval_path,
            production_artifact_dir="artifacts/real/production",
            output_path="artifacts/real/deployment/test_decision_1.json",
        )
        p2 = svc.evaluate_and_generate_deployment_decision(
            evaluation_report_path=eval_path,
            production_artifact_dir="artifacts/real/production",
            output_path="artifacts/real/deployment/test_decision_2.json",
        )

        assert p1.dataset_hash == p2.dataset_hash
        assert p1.evaluation_artifact_hash == p2.evaluation_artifact_hash
        assert len(p1.candidate_assessments) == len(p2.candidate_assessments)
        for a1, a2 in zip(
            p1.candidate_assessments, p2.candidate_assessments, strict=True
        ):
            assert a1.model_id == a2.model_id
            assert a1.eligibility_status == a2.eligibility_status
            assert a1.macro_f1 == a2.macro_f1

        # Clean up temporary test files
        Path("artifacts/real/deployment/test_decision_1.json").unlink(
            missing_ok=True
        )
        Path("artifacts/real/deployment/test_decision_2.json").unlink(
            missing_ok=True
        )

    def test_cryptographic_traceability_in_persisted_artifact(self) -> None:
        """Verify persisted production_model_selection.json metadata."""
        artifact_path = Path(
            "artifacts/real/deployment/production_model_selection.json"
        )
        assert artifact_path.exists(), "Deployment decision artifact must exist"

        data = json.loads(artifact_path.read_text(encoding="utf-8"))
        assert data["task_id"] == "NEXT-008"
        assert data["authorization_status"] == "AUTHORIZED"
        assert data["feature_schema_version"] == "feat_v1.0.0"
        assert len(data["dataset_hash"]) == 64
        assert len(data["evaluation_artifact_hash"]) == 64
        assert len(data["candidate_assessments"]) == 5
        assert len(data["operating_modes"]) == 3
        assert "HIGH_PRECISION" in data["operating_modes"]
        assert "HIGH_RECALL" in data["operating_modes"]
        assert "SELECTIVE" in data["operating_modes"]
