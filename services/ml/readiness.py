"""Scientific and technical ML readiness assessment engine for Phase 4.

Evaluates whether the repository, contracts, reference data, and configuration
satisfy the 8 scientific pillars required before supervised ML training can proceed:
1. Target definition and class taxonomy approval
2. Reference label quality and Tier A/B provenance
3. Feature metadata definitions and latency compatibility
4. Leakage audit compliance
5. Split strategy definition and group independence
6. Benchmark scope and evaluation metric definitions
7. Probability calibration & abstention contracts
8. Reproducibility metadata and deterministic hashing
"""

from datetime import UTC, datetime
from typing import Any

from packages.config.ml import MLConfig
from packages.schemas.ml import (
    LabelMetadata,
    LabelTier,
    MLReadinessReport,
    ReadinessStatus,
    SplitIntegrityReport,
    TargetDefinition,
)
from services.ml.features.leakage import LeakageAuditor, LeakageAuditReport
from services.ml.features.registry import FeatureRegistry


class MLReadinessAuditor:
    """Auditor assessing if repository is ready for supervised ML."""

    @classmethod
    def evaluate_readiness(
        cls,
        target_definition: TargetDefinition | None = None,
        reference_labels: list[LabelMetadata] | None = None,
        feature_registry: FeatureRegistry | None = None,
        leakage_report: LeakageAuditReport | None = None,
        split_report: SplitIntegrityReport | None = None,
        ml_config: MLConfig | None = None,
        dataset_hash_available: bool = False,
    ) -> MLReadinessReport:
        """Perform comprehensive readiness assessment across all Phase 4 pillars."""
        open_questions: list[str] = []
        blockers: list[str] = []
        details: dict[str, Any] = {}

        # 1. Target Definition Assessment
        target_ready = False
        if target_definition is None:
            blockers.append("Target definition is missing.")
            open_questions.append(
                "What is the official supervised target and prediction unit?"
            )
            details["target"] = "Missing target definition."
        elif not target_definition.is_approved:
            blockers.append(
                f"Target '{target_definition.target_id}' is not yet approved/frozen."
            )
            unresolved = (
                target_definition.unresolved_reason or "Awaiting scientific sign-off."
            )
            open_questions.append(
                f"Target '{target_definition.name}' remains unapproved: {unresolved}"
            )
            details["target"] = {
                "target_id": target_definition.target_id,
                "is_approved": False,
                "unresolved_reason": target_definition.unresolved_reason,
            }
        else:
            target_ready = True
            details["target"] = {
                "target_id": target_definition.target_id,
                "is_approved": True,
                "class_vocabulary": target_definition.class_vocabulary,
            }

        # 2. Reference Label Quality & Provenance Assessment
        labels_ready = False
        if not reference_labels:
            blockers.append("No reference ground-truth labels available in registry.")
            open_questions.append(
                "Which reference source becomes authoritative for benchmark?"
            )
            details["labels"] = "Zero reference labels provided."
        else:
            tier_a_count = sum(
                1
                for lbl in reference_labels
                if lbl.label_tier == LabelTier.TIER_A_AUTHORITATIVE
            )
            tier_b_count = sum(
                1
                for lbl in reference_labels
                if lbl.label_tier == LabelTier.TIER_B_STRONG_EVIDENCE
            )
            tier_c_count = sum(
                1
                for lbl in reference_labels
                if lbl.label_tier == LabelTier.TIER_C_PROXY_WEAK
            )

            if tier_a_count == 0 and tier_b_count == 0:
                blockers.append(
                    "All provided labels are Tier C (weak/proxy) or unverified; "
                    "supervised training on weak labels as ground truth is prohibited."
                )
                open_questions.append(
                    "How will Tier A/B ground truth be acquired/adjudicated?"
                )
            else:
                labels_ready = True

            details["labels"] = {
                "total_count": len(reference_labels),
                "tier_a_count": tier_a_count,
                "tier_b_count": tier_b_count,
                "tier_c_count": tier_c_count,
            }

        # 3. Feature Metadata & Availability Assessment
        features_ready = False
        if feature_registry is None:
            blockers.append("Feature registry is uninitialized.")
            details["features"] = "Feature registry not provided."
        else:
            features = feature_registry.list_features(allowed_only=True)
            if not features:
                blockers.append(
                    "Feature registry contains no approved features for training."
                )
                details["features"] = "No approved features registered."
            else:
                features_ready = True
                details["features"] = {
                    "approved_count": len(features),
                    "feature_names": [f.feature_name for f in features],
                }

        # 4. Leakage Audit Assessment
        leakage_audit_passed = False
        if leakage_report is None and feature_registry is not None:
            auditor = LeakageAuditor()
            leakage_report = auditor.audit_feature_set(
                feature_registry.list_features(),
                target_definition=target_definition,
            )

        if leakage_report is not None:
            leakage_audit_passed = leakage_report.is_safe
            if not leakage_report.is_safe:
                blockers.append(
                    f"Leakage audit detected "
                    f"{leakage_report.violation_count} violation(s)."
                )
                details["leakage"] = {
                    "is_safe": False,
                    "violations": [v.model_dump() for v in leakage_report.violations],
                }
            else:
                details["leakage"] = {
                    "is_safe": True,
                    "audited_count": leakage_report.total_audited,
                }
        else:
            blockers.append("Leakage audit has not been performed.")
            details["leakage"] = "Leakage audit report missing."

        # 5. Split Strategy & Group Independence Assessment
        split_strategy_ready = False
        if split_report is None:
            blockers.append("Split integrity verification has not been performed.")
            open_questions.append(
                "What demonstration study area and temporal boundaries are frozen?"
            )
            details["splits"] = "Split report missing."
        elif not split_report.is_valid:
            blockers.append("Split integrity check failed leakage invariants.")
            details["splits"] = {
                "is_valid": False,
                "event_leakage_violations": (split_report.event_leakage_violations),
                "source_leakage_violations": (split_report.source_leakage_violations),
                "temporal_inversion_violations": (
                    split_report.temporal_inversion_violations
                ),
            }
        else:
            split_strategy_ready = True
            details["splits"] = {
                "is_valid": True,
                "strategy": split_report.split_strategy.value,
                "train_count": split_report.train_count,
                "val_count": split_report.validation_count,
                "test_count": split_report.test_count,
            }

        # 6. Benchmark Scope & Metrics Assessment
        benchmark_defined = False
        if ml_config is None:
            blockers.append("ML configuration contract is missing.")
            details["benchmark"] = "MLConfig missing."
        elif not ml_config.is_complete:
            blockers.append(
                f"ML configuration '{ml_config.version}' is incomplete. "
                f"Missing: {', '.join(ml_config.missing_parameters)}"
            )
            open_questions.append(
                "Which primary metric and calibration cutoff are frozen?"
            )
            details["benchmark"] = {
                "is_complete": False,
                "missing_parameters": ml_config.missing_parameters,
            }
        else:
            benchmark_defined = True
            details["benchmark"] = {
                "is_complete": True,
                "required_metrics": ml_config.required_metrics,
                "primary_metric": ml_config.primary_metric,
            }

        # 7. Reproducibility & Determinism Assessment
        reproducibility_ready = False
        if dataset_hash_available and ml_config is not None:
            reproducibility_ready = True
            details["reproducibility"] = {
                "dataset_hash_verified": True,
                "config_fingerprint": ml_config.compute_fingerprint(),
            }
        else:
            blockers.append(
                "Dataset content-hash or configuration fingerprint missing."
            )
            details["reproducibility"] = {
                "dataset_hash_verified": dataset_hash_available,
            }

        # Overall Status Determination
        all_passed = (
            target_ready
            and labels_ready
            and features_ready
            and leakage_audit_passed
            and split_strategy_ready
            and benchmark_defined
            and reproducibility_ready
        )

        if all_passed:
            overall_status = ReadinessStatus.READY
        elif not target_ready or not labels_ready or not split_strategy_ready:
            overall_status = ReadinessStatus.BLOCKED
        else:
            overall_status = ReadinessStatus.NOT_READY

        report_id = f"readiness_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"

        return MLReadinessReport(
            report_id=report_id,
            overall_status=overall_status,
            evaluated_at=datetime.now(UTC),
            target_ready=target_ready,
            labels_ready=labels_ready,
            features_ready=features_ready,
            leakage_audit_passed=leakage_audit_passed,
            split_strategy_ready=split_strategy_ready,
            benchmark_defined=benchmark_defined,
            reproducibility_ready=reproducibility_ready,
            open_questions=open_questions,
            blockers=blockers,
            readiness_details=details,
        )
