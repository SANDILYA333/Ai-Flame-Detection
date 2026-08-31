"""Unit tests for Phase 4 ML readiness assessment engine."""

from packages.config.ml import MLConfig
from packages.schemas.ml import (
    FeatureDefinition,
    FeatureMissingnessHandling,
    FeatureType,
    LabelMetadata,
    LabelProvenanceType,
    LabelTier,
    LeakageRisk,
    ReadinessStatus,
    SplitIntegrityReport,
    SplitStrategy,
    TargetDefinition,
    TargetType,
    TargetUnit,
)
from services.ml.features.leakage import LeakageAuditReport
from services.ml.features.registry import FeatureRegistry
from services.ml.readiness import MLReadinessAuditor


class TestMLReadinessAuditor:
    """Test suite validating ML readiness auditing and blocker detection."""

    def test_unapproved_initial_state_reports_blocked(self) -> None:
        """Unapproved initial state reports status=BLOCKED with open questions."""
        report = MLReadinessAuditor.evaluate_readiness()

        assert report.overall_status == ReadinessStatus.BLOCKED
        assert report.target_ready is False
        assert report.labels_ready is False
        assert report.features_ready is False
        assert len(report.blockers) >= 4
        assert len(report.open_questions) >= 2

        # Verify open questions contain expected scientific decisions
        question_text = " ".join(report.open_questions).lower()
        assert "target" in question_text or "prediction unit" in question_text
        assert "ground-truth" in question_text or "reference" in question_text

    def test_weak_labels_only_reports_blocked(self) -> None:
        """Providing only Tier C (weak/proxy) labels keeps status BLOCKED."""
        target = TargetDefinition(
            target_id="target_phenomenon_v1",
            name="Phenomenon",
            target_type=TargetType.MULTICLASS_CLASSIFICATION,
            unit_of_prediction=TargetUnit.EVENT,
            class_vocabulary=["flare", "fire"],
            is_approved=True,
        )

        weak_labels = [
            LabelMetadata(
                label_id="lbl_w1",
                target_id="target_phenomenon_v1",
                entity_id="evt_01",
                label_value="flare",
                label_tier=LabelTier.TIER_C_PROXY_WEAK,  # Weak only
                provenance_type=LabelProvenanceType.WEAK_LABEL,
                source_name="Heuristic Proximity",
            )
        ]

        report = MLReadinessAuditor.evaluate_readiness(
            target_definition=target,
            reference_labels=weak_labels,
        )

        assert report.overall_status == ReadinessStatus.BLOCKED
        assert report.target_ready is True
        assert report.labels_ready is False
        assert any("weak labels" in b.lower() for b in report.blockers)

    def test_fully_validated_pipeline_reports_ready(self) -> None:
        """A fully approved and leak-free pipeline state reports status=READY."""
        target = TargetDefinition(
            target_id="target_phenomenon_v1",
            name="Phenomenon",
            target_type=TargetType.MULTICLASS_CLASSIFICATION,
            unit_of_prediction=TargetUnit.EVENT,
            class_vocabulary=["flare", "fire", "unknown"],
            is_approved=True,
        )

        tier_a_labels = [
            LabelMetadata(
                label_id="lbl_a1",
                target_id="target_phenomenon_v1",
                entity_id="evt_01",
                label_value="flare",
                label_tier=LabelTier.TIER_A_AUTHORITATIVE,
                provenance_type=LabelProvenanceType.GROUND_TRUTH,
                source_name="Refinery Log",
            )
        ]

        reg = FeatureRegistry()
        reg.register(
            FeatureDefinition(
                feature_name="frp_mean_mw",
                feature_type=FeatureType.NUMERIC,
                source_entity="Event",
                derivation_description="Mean FRP in MW.",
                availability_lag_seconds=0.0,
                missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
                allowed_for_training=True,
                leakage_risk=LeakageRisk.SAFE,
                version="v1.0",
            )
        )

        leakage_report = LeakageAuditReport(
            is_safe=True,
            total_audited=1,
            safe_count=1,
            violation_count=0,
            safe_features=["frp_mean_mw"],
        )

        split_report = SplitIntegrityReport(
            is_valid=True,
            split_strategy=SplitStrategy.GROUPED_EVENT_HOLDOUT,
            train_count=70,
            validation_count=15,
            test_count=15,
        )

        config = MLConfig(
            version="v1.0.0",
            target_name="thermal_phenomenon",
            target_type=TargetType.MULTICLASS_CLASSIFICATION,
            target_unit=TargetUnit.EVENT,
            class_vocabulary=("flare", "fire", "unknown"),
            feature_set_version="feat_v1",
            allowed_feature_names=("frp_mean_mw",),
            split_strategy=SplitStrategy.GROUPED_EVENT_HOLDOUT,
            train_ratio=0.70,
            validation_ratio=0.15,
            test_ratio=0.15,
            random_seed=42,
            required_metrics=("macro_f1",),
            primary_metric="macro_f1",
        )

        report = MLReadinessAuditor.evaluate_readiness(
            target_definition=target,
            reference_labels=tier_a_labels,
            feature_registry=reg,
            leakage_report=leakage_report,
            split_report=split_report,
            ml_config=config,
            dataset_hash_available=True,
        )

        assert report.overall_status == ReadinessStatus.READY
        assert report.target_ready is True
        assert report.labels_ready is True
        assert report.features_ready is True
        assert report.leakage_audit_passed is True
        assert report.split_strategy_ready is True
        assert report.benchmark_defined is True
        assert report.reproducibility_ready is True
        assert len(report.blockers) == 0
