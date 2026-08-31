"""Execution Script for NEXT-008: Production Model Selection & Deployment Policy.

Consumes the authoritative NEXT-007 evaluation report, executes multi-criteria model
selection, verifies hard constraints and trade-offs, and generates the machine-readable
deployment decision artifact at:
artifacts/real/deployment/production_model_selection.json.
"""

from __future__ import annotations

from pathlib import Path

from services.ml.deployment.policy import (
    ProductionDeploymentPolicyService,
    ProductionOperatingMode,
)


def run_production_model_selection() -> None:
    print("=" * 75)
    print("SIH26162 — NEXT-008 PRODUCTION MODEL SELECTION & DEPLOYMENT POLICY")
    print("=" * 75)
    print()

    eval_report_path = Path(
        "artifacts/real/evaluation/real_model_evaluation_report.json"
    )
    if not eval_report_path.exists():
        print(f"[ERROR] Evaluation report not found at {eval_report_path}.")
        return

    output_path = Path(
        "artifacts/real/deployment/production_model_selection.json"
    )

    print("Evaluating candidate models against scientific multi-criteria...")
    decision = (
        ProductionDeploymentPolicyService.evaluate_and_generate_deployment_decision(
            evaluation_report_path=eval_report_path,
            production_artifact_dir="artifacts/real/production",
            output_path=output_path,
        )
    )

    print("\n" + "-" * 75)
    print("CANDIDATE MODEL ELIGIBILITY ASSESSMENTS:")
    print("-" * 75)
    for a in decision.candidate_assessments:
        print(f"Model: {a.model_type} ({a.model_role})")
        print(f"  - Status:           {a.eligibility_status.value}")
        print(
            f"  - Macro-F1:         {a.macro_f1:.4f} | "
            f"Balanced Acc: {a.balanced_accuracy:.4f}"
        )
        print(
            f"  - Precision:        {a.precision:.4f} | "
            f"Recall:       {a.recall:.4f}"
        )
        roc_str = f"{a.roc_auc:.4f}" if a.roc_auc is not None else "N/A"
        ece_str = (
            f"{a.expected_calibration_error:.4f}"
            if a.expected_calibration_error is not None
            else "N/A"
        )
        print(f"  - ROC-AUC:          {roc_str} | ECE:          {ece_str}")
        print(
            f"  - Hard Constraints: "
            f"{'PASSED' if a.passed_hard_constraints else 'FAILED'}"
        )
        if a.failed_criteria:
            print(f"  - Failed Criteria:  {', '.join(a.failed_criteria)}")
        print(f"  - Notes:            {a.selection_notes}")
        print()

    print("-" * 75)
    print("AUTHORIZED PRODUCTION OPERATING MODES:")
    print("-" * 75)
    for mode_name, mode_pol in decision.operating_modes.items():
        print(f"Operating Mode: [{mode_name}]")
        print(f"  - Assigned Model:       {mode_pol.assigned_model_type}")
        print(f"  - Model Version:        {mode_pol.model_version}")
        print(f"  - Confidence Threshold: {mode_pol.confidence_threshold:.2f}")
        print(f"  - Abstention Action:    {mode_pol.abstention_action}")
        print(f"  - Coverage Estimate:    {mode_pol.coverage_estimate * 100:.1f}%")
        print(f"  - Policy Description:   {mode_pol.policy_description}")
        print("  - Expected Metrics:")
        for k, v in mode_pol.expected_metrics.items():
            print(f"      * {k:20s}: {v:.4f}")
        print()

    print("-" * 75)
    print("RUNTIME POLICY VERIFICATION (SMOKE TEST):")
    print("-" * 75)
    for mode in [
        ProductionOperatingMode.HIGH_PRECISION,
        ProductionOperatingMode.HIGH_RECALL,
        ProductionOperatingMode.SELECTIVE,
    ]:
        engine, policy = (
            ProductionDeploymentPolicyService.resolve_production_model(mode)
        )
        print(
            f"  - Mode '{mode.value}': resolved {engine.artifact.metadata.model_type} "
            f"(Threshold={policy.confidence_threshold:.2f})"
        )

    print("\n" + "=" * 75)
    print(f"AUTHORIZATION STATUS:       {decision.authorization_status}")
    print(f"DEPLOYMENT ARTIFACT PATH:   {output_path}")
    print("=" * 75)


if __name__ == "__main__":
    run_production_model_selection()
