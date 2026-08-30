"""Unit tests for ML target definitions, ReferenceEvidence, and LabelConstructor."""

from datetime import UTC, datetime

import pytest

from packages.schemas.common import Coordinate
from packages.schemas.enums import SourceRole
from packages.schemas.ml import (
    ExclusionReason,
    LabelConflictPolicy,
    LabelProvenanceType,
    LabelTier,
    ReferenceEvidence,
    TargetType,
    TargetUnit,
)
from services.ml.labels.constructor import LabelConstructor
from services.ml.labels.reporting import (
    generate_target_catalog_json,
    generate_target_catalog_markdown,
)
from services.ml.labels.targets import (
    get_standard_target_registry,
)


class TestMLLabelConstruction:
    """Test suite validating target specifications and auditable label construction."""

    def test_standard_targets_registry_and_schemas(self) -> None:
        """Standard targets are correctly registered with explicit vocabularies."""
        registry = get_standard_target_registry()
        assert len(registry) == 3
        assert "target_thermal_phenomenon" in registry
        assert "target_industrial_segregation" in registry
        assert "target_persistent_combustion" in registry

        # Verify Target 1
        t1 = registry["target_thermal_phenomenon"]
        assert t1.target_type == TargetType.MULTICLASS_CLASSIFICATION
        assert t1.unit_of_prediction == TargetUnit.EVENT
        assert "flare" in t1.class_vocabulary
        assert "unknown" in t1.class_vocabulary
        assert t1.is_approved is True

        # Verify Target 2 (Industrial Segregation)
        t2 = registry["target_industrial_segregation"]
        assert t2.target_type == TargetType.BINARY_CLASSIFICATION
        assert t2.unit_of_prediction == TargetUnit.EVENT
        assert set(t2.class_vocabulary) == {
            "industrial",
            "non_industrial",
            "unknown",
        }
        assert t2.positive_definition is not None
        assert t2.negative_definition is not None

        # Verify Target 3 (Persistent Combustion)
        t3 = registry["target_persistent_combustion"]
        assert t3.target_type == TargetType.BINARY_CLASSIFICATION
        assert "persistent_source" in t3.class_vocabulary

    def test_authoritative_tier_a_label_assignment(self) -> None:
        """Tier A authoritative evidence produces high-confidence training label."""
        ev = ReferenceEvidence(
            evidence_id="ev_001",
            source_name="GEM_OIL_GAS_PLANTS",
            source_role=SourceRole.GROUND_TRUTH_EVIDENCE,
            entity_id="evt_jamnagar_01",
            geometry=Coordinate(latitude=22.48, longitude=70.06),
            observed_at=datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC),
            claim_class="flare",
            confidence_score=1.0,
            tier=LabelTier.TIER_A_AUTHORITATIVE,
            provenance_type=LabelProvenanceType.GROUND_TRUTH,
            evidence_payload={"plant_name": "Jamnagar Refinery Complex"},
        )

        constructor = LabelConstructor()
        decision = constructor.construct_label(
            target_id="target_thermal_phenomenon",
            entity_id="evt_jamnagar_01",
            evidence_items=[ev],
        )

        assert decision.assigned_class == "flare"
        assert decision.label_tier == LabelTier.TIER_A_AUTHORITATIVE
        assert decision.provenance_type == LabelProvenanceType.GROUND_TRUTH
        assert decision.confidence_score == 1.0
        assert decision.is_train_eligible is True
        assert decision.is_eval_eligible is True
        assert decision.has_conflicting_evidence is False
        assert decision.exclusion_reason is None

    def test_multi_source_tier_b_consensus_construction(self) -> None:
        """Multiple corroborating Tier B sources form a valid consensus label."""
        ev1 = ReferenceEvidence(
            evidence_id="ev_vnf_01",
            source_name="VIIRS_NIGHTFIRE_VNF",
            source_role=SourceRole.GROUND_TRUTH_EVIDENCE,
            entity_id="evt_ind_02",
            geometry=Coordinate(latitude=22.47, longitude=70.05),
            claim_class="industrial_thermal_source",
            confidence_score=0.90,
            tier=LabelTier.TIER_B_STRONG_EVIDENCE,
            provenance_type=LabelProvenanceType.REFERENCE_LABEL,
        )
        ev2 = ReferenceEvidence(
            evidence_id="ev_wri_01",
            source_name="WRI_POWER_PLANTS",
            source_role=SourceRole.REFERENCE,
            entity_id="evt_ind_02",
            geometry=Coordinate(latitude=22.471, longitude=70.051),
            claim_class="industrial",
            confidence_score=0.85,
            tier=LabelTier.TIER_B_STRONG_EVIDENCE,
            provenance_type=LabelProvenanceType.REFERENCE_LABEL,
        )

        constructor = LabelConstructor()
        decision = constructor.construct_label(
            target_id="target_industrial_segregation",
            entity_id="evt_ind_02",
            evidence_items=[ev1, ev2],
        )

        assert decision.assigned_class == "industrial"
        assert decision.label_tier == LabelTier.TIER_B_STRONG_EVIDENCE
        assert decision.confidence_score == 0.90
        assert decision.is_train_eligible is True
        assert len(decision.contributing_evidence_ids) == 2

    def test_weak_proxy_tier_c_deterministic_inference_tagging(self) -> None:
        """Phase-3 rules are classified as TIER_C_PROXY_WEAK, not ground truth."""
        ev_rule = ReferenceEvidence(
            evidence_id="ev_p3_01",
            source_name="PHASE3_HEURISTIC_RULES",
            source_role=SourceRole.GROUND_TRUTH_EVIDENCE,
            entity_id="evt_weak_01",
            geometry=Coordinate(latitude=22.40, longitude=70.00),
            claim_class="vegetation_wildfire",
            confidence_score=0.60,
            tier=LabelTier.TIER_C_PROXY_WEAK,
            provenance_type=LabelProvenanceType.DETERMINISTIC_INFERENCE,
        )

        constructor = LabelConstructor()
        decision = constructor.construct_label(
            target_id="target_thermal_phenomenon",
            entity_id="evt_weak_01",
            evidence_items=[ev_rule],
        )

        assert decision.assigned_class == "vegetation_wildfire"
        assert decision.label_tier == LabelTier.TIER_C_PROXY_WEAK
        assert decision.provenance_type == LabelProvenanceType.DETERMINISTIC_INFERENCE
        assert decision.confidence_score == 0.60

    def test_conflict_resolution_tier_precedence(self) -> None:
        """Tier A authoritative evidence overrides conflicting Tier C weak evidence."""
        ev_authoritative = ReferenceEvidence(
            evidence_id="ev_auth_01",
            source_name="DISASTER_MANAGEMENT_AUTHORITY",
            source_role=SourceRole.GROUND_TRUTH_EVIDENCE,
            entity_id="evt_conflict_01",
            geometry=Coordinate(latitude=22.48, longitude=70.06),
            claim_class="flare",
            confidence_score=1.0,
            tier=LabelTier.TIER_A_AUTHORITATIVE,
            provenance_type=LabelProvenanceType.GROUND_TRUTH,
        )
        ev_weak_proxy = ReferenceEvidence(
            evidence_id="ev_weak_01",
            source_name="UNVALIDATED_NEWS_SCRAPER",
            source_role=SourceRole.REFERENCE,
            entity_id="evt_conflict_01",
            geometry=Coordinate(latitude=22.48, longitude=70.06),
            claim_class="vegetation_wildfire",
            confidence_score=0.50,
            tier=LabelTier.TIER_C_PROXY_WEAK,
            provenance_type=LabelProvenanceType.WEAK_LABEL,
        )

        constructor = LabelConstructor()
        decision = constructor.construct_label(
            target_id="target_thermal_phenomenon",
            entity_id="evt_conflict_01",
            evidence_items=[ev_authoritative, ev_weak_proxy],
            conflict_policy=LabelConflictPolicy.TIER_PRECEDENCE,
        )

        assert decision.assigned_class == "flare"
        assert decision.label_tier == LabelTier.TIER_A_AUTHORITATIVE
        assert decision.has_conflicting_evidence is True
        assert "superseded" in (decision.conflict_resolution_notes or "").lower()
        assert decision.is_train_eligible is True

    def test_unresolvable_equal_tier_conflict_yields_unknown_and_exclusion(
        self,
    ) -> None:
        """Contradictory claims at the same tier resolve to UNKNOWN and exclusion."""
        ev1 = ReferenceEvidence(
            evidence_id="ev_cat1",
            source_name="CATALOG_A",
            source_role=SourceRole.GROUND_TRUTH_EVIDENCE,
            entity_id="evt_deadlock_01",
            geometry=Coordinate(latitude=22.48, longitude=70.06),
            claim_class="industrial",
            confidence_score=0.85,
            tier=LabelTier.TIER_B_STRONG_EVIDENCE,
        )
        ev2 = ReferenceEvidence(
            evidence_id="ev_cat2",
            source_name="CATALOG_B",
            source_role=SourceRole.GROUND_TRUTH_EVIDENCE,
            entity_id="evt_deadlock_01",
            geometry=Coordinate(latitude=22.48, longitude=70.06),
            claim_class="non_industrial",
            confidence_score=0.85,
            tier=LabelTier.TIER_B_STRONG_EVIDENCE,
        )

        constructor = LabelConstructor()
        decision = constructor.construct_label(
            target_id="target_industrial_segregation",
            entity_id="evt_deadlock_01",
            evidence_items=[ev1, ev2],
        )

        assert decision.assigned_class == "unknown"
        assert decision.label_tier == LabelTier.UNKNOWN
        assert decision.has_conflicting_evidence is True
        assert decision.is_train_eligible is False
        assert decision.is_eval_eligible is False
        assert decision.exclusion_reason == ExclusionReason.CONFLICTING_LABEL_EVIDENCE

    def test_missing_evidence_preservation_unknown_not_negative(self) -> None:
        """Absence of evidence creates UNKNOWN class, NEVER a fabricated negative."""
        constructor = LabelConstructor()

        # Zero evidence for industrial segregation
        decision = constructor.construct_label(
            target_id="target_industrial_segregation",
            entity_id="evt_no_data",
            evidence_items=[],
        )

        # Must NOT be fabricated as "non_industrial"
        assert decision.assigned_class == "unknown"
        assert decision.label_tier == LabelTier.UNKNOWN
        assert decision.is_train_eligible is False
        assert decision.exclusion_reason == ExclusionReason.INSUFFICIENT_LABEL_EVIDENCE

    def test_unregistered_target_raises_error(self) -> None:
        """Attempting to construct a label for an unknown target raises ValueError."""
        constructor = LabelConstructor()
        with pytest.raises(ValueError, match="is not registered"):
            constructor.construct_label(
                target_id="target_non_existent",
                entity_id="evt_001",
            )

    def test_target_reporting_utilities(self) -> None:
        """Target reporting generates valid Markdown and JSON representations."""
        md = generate_target_catalog_markdown()
        assert "| Target ID | Name |" in md
        assert "`target_thermal_phenomenon`" in md
        assert "`target_industrial_segregation`" in md

        json_catalog = generate_target_catalog_json()
        assert json_catalog["total_targets"] == 3
        assert any(
            t["target_id"] == "target_industrial_segregation"
            for t in json_catalog["targets"]
        )
