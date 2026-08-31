"""Label decision engine and reference evidence synthesizer for Phase 4 ML.

Applies auditable association rules, quality tiering (Tier A/B/C), and explicit
conflict resolution policies to construct scientifically defensible LabelDecisions
while strictly enforcing the invariant: Missing != Negative, Unknown != Negative.
"""

from collections.abc import Sequence
from datetime import UTC, datetime

from packages.schemas.common import UtcDatetime
from packages.schemas.enums import SourceRole
from packages.schemas.ml import (
    ExclusionReason,
    LabelConflictPolicy,
    LabelDecision,
    LabelProvenanceType,
    LabelTier,
    ReferenceEvidence,
    TargetDefinition,
)
from services.ml.labels.targets import get_standard_target_registry


class LabelConstructor:
    """Constructs auditable LabelDecision records from reference evidence."""

    def __init__(
        self,
        targets: dict[str, TargetDefinition] | None = None,
        default_conflict_policy: LabelConflictPolicy = (
            LabelConflictPolicy.TIER_PRECEDENCE
        ),
    ) -> None:
        self.targets = targets or get_standard_target_registry()
        self.conflict_policy = default_conflict_policy

    def construct_label(
        self,
        target_id: str,
        entity_id: str,
        evidence_items: Sequence[ReferenceEvidence] | None = None,
        conflict_policy: LabelConflictPolicy | None = None,
        as_of_time: UtcDatetime | None = None,
    ) -> LabelDecision:
        """Construct a single LabelDecision for an entity and target.

        Args:
            target_id: Target specification identifier.
            entity_id: Prediction entity identifier (e.g. event_id).
            evidence_items: Sequence of matching ReferenceEvidence items.
            conflict_policy: Conflict resolution strategy.
            as_of_time: Timestamp of decision generation in UTC.

        Returns:
            LabelDecision: Auditable, structured label decision.
        """
        now = as_of_time or datetime.now(UTC)
        policy = conflict_policy or self.conflict_policy

        target_def = self.targets.get(target_id)
        if target_def is None:
            raise ValueError(f"Target '{target_id}' is not registered.")

        matched_evidence = [
            e
            for e in (evidence_items or [])
            if e.entity_id == entity_id
            and e.source_role
            in (
                SourceRole.GROUND_TRUTH_EVIDENCE,
                SourceRole.GROUND_TRUTH_CANDIDATE,
                SourceRole.REFERENCE,
            )
        ]

        # Case 1: Zero evidence available (Missing != Negative)
        if not matched_evidence:
            return LabelDecision(
                decision_id=f"dec_{target_id}_{entity_id}_none",
                target_id=target_id,
                entity_id=entity_id,
                assigned_class="unknown",
                label_tier=LabelTier.UNKNOWN,
                provenance_type=LabelProvenanceType.UNKNOWN,
                confidence_score=0.0,
                contributing_evidence_ids=[],
                has_conflicting_evidence=False,
                conflict_resolution_notes="No reference evidence matched.",
                is_train_eligible=False,
                is_eval_eligible=False,
                exclusion_reason=ExclusionReason.INSUFFICIENT_LABEL_EVIDENCE,
                decision_timestamp=now,
            )

        # Case 2: Evidence Synthesis & Conflict Analysis
        return self._synthesize_evidence(
            target_def=target_def,
            entity_id=entity_id,
            evidence=matched_evidence,
            policy=policy,
            timestamp=now,
        )

    def _synthesize_evidence(
        self,
        target_def: TargetDefinition,
        entity_id: str,
        evidence: list[ReferenceEvidence],
        policy: LabelConflictPolicy,
        timestamp: UtcDatetime,
    ) -> LabelDecision:
        """Evaluate evidence claims, resolve conflicts, and determine tier."""
        tier_weights = {
            LabelTier.TIER_A_AUTHORITATIVE: 4,
            LabelTier.TIER_B_STRONG_EVIDENCE: 3,
            LabelTier.TIER_C_PROXY_WEAK: 2,
            LabelTier.UNVERIFIED_HEURISTIC: 1,
            LabelTier.UNKNOWN: 0,
        }

        # Filter evidence to valid classes in vocabulary
        valid_evidence: list[ReferenceEvidence] = []
        for e in evidence:
            mapped_cls = self._map_claim_to_vocabulary(target_def, e.claim_class)
            if mapped_cls in target_def.class_vocabulary:
                valid_evidence.append(e)

        if not valid_evidence:
            return LabelDecision(
                decision_id=f"dec_{target_def.target_id}_{entity_id}_unmapped",
                target_id=target_def.target_id,
                entity_id=entity_id,
                assigned_class="unknown",
                label_tier=LabelTier.UNKNOWN,
                provenance_type=LabelProvenanceType.UNKNOWN,
                confidence_score=0.0,
                contributing_evidence_ids=[e.evidence_id for e in evidence],
                has_conflicting_evidence=False,
                conflict_resolution_notes=(
                    "Evidence claims could not be mapped to vocabulary."
                ),
                is_train_eligible=False,
                is_eval_eligible=False,
                exclusion_reason=ExclusionReason.AMBIGUOUS_CLASS,
                decision_timestamp=timestamp,
            )

        # Group by mapped claim class
        claims_by_class: dict[str, list[ReferenceEvidence]] = {}
        for e in valid_evidence:
            mapped_cls = self._map_claim_to_vocabulary(target_def, e.claim_class)
            if mapped_cls not in claims_by_class:
                claims_by_class[mapped_cls] = []
            claims_by_class[mapped_cls].append(e)

        distinct_classes = list(claims_by_class.keys())

        # Single unanimous class
        if len(distinct_classes) == 1:
            cls_name = distinct_classes[0]
            contributing = claims_by_class[cls_name]
            best_tier = max(
                (e.tier for e in contributing), key=lambda t: tier_weights.get(t, 0)
            )
            best_prov = contributing[0].provenance_type
            max_conf = max(e.confidence_score for e in contributing)

            # Determine eligibility
            is_train = (
                best_tier
                in (
                    LabelTier.TIER_A_AUTHORITATIVE,
                    LabelTier.TIER_B_STRONG_EVIDENCE,
                    LabelTier.TIER_C_PROXY_WEAK,
                )
                and cls_name != "unknown"
            )

            return LabelDecision(
                decision_id=f"dec_{target_def.target_id}_{entity_id}",
                target_id=target_def.target_id,
                entity_id=entity_id,
                assigned_class=cls_name,
                label_tier=best_tier,
                provenance_type=best_prov,
                confidence_score=max_conf,
                contributing_evidence_ids=[e.evidence_id for e in contributing],
                has_conflicting_evidence=False,
                conflict_resolution_notes=None,
                is_train_eligible=is_train,
                is_eval_eligible=(best_tier != LabelTier.UNKNOWN),
                exclusion_reason=(
                    None if is_train else ExclusionReason.INSUFFICIENT_LABEL_EVIDENCE
                ),
                decision_timestamp=timestamp,
            )

        # Conflicting classes exist across evidence items
        if policy in (
            LabelConflictPolicy.TIER_PRECEDENCE,
            LabelConflictPolicy.AUTHORITATIVE_OVERRIDE,
        ):
            # Check highest tier per class
            class_max_tiers = {
                cls_name: max(tier_weights.get(e.tier, 0) for e in ev_list)
                for cls_name, ev_list in claims_by_class.items()
            }
            highest_weight = max(class_max_tiers.values())
            top_classes = [
                cls_name
                for cls_name, weight in class_max_tiers.items()
                if weight == highest_weight
            ]

            # If a strictly higher tier dominates, it wins
            if len(top_classes) == 1:
                winner_cls = top_classes[0]
                winning_ev = [
                    e
                    for e in claims_by_class[winner_cls]
                    if tier_weights.get(e.tier, 0) == highest_weight
                ]
                best_tier = winning_ev[0].tier
                return LabelDecision(
                    decision_id=f"dec_{target_def.target_id}_{entity_id}_resolved",
                    target_id=target_def.target_id,
                    entity_id=entity_id,
                    assigned_class=winner_cls,
                    label_tier=best_tier,
                    provenance_type=winning_ev[0].provenance_type,
                    confidence_score=max(e.confidence_score for e in winning_ev),
                    contributing_evidence_ids=[e.evidence_id for e in valid_evidence],
                    has_conflicting_evidence=True,
                    conflict_resolution_notes=(
                        f"Resolved by {policy.value}: {winner_cls} ({best_tier.value}) "
                        f"superseded lower-tier contradictory claims."
                    ),
                    is_train_eligible=True,
                    is_eval_eligible=True,
                    exclusion_reason=None,
                    decision_timestamp=timestamp,
                )

        # Unresolvable equal-tier conflict -> UNKNOWN, excluded from training
        return LabelDecision(
            decision_id=f"dec_{target_def.target_id}_{entity_id}_conflict",
            target_id=target_def.target_id,
            entity_id=entity_id,
            assigned_class="unknown",
            label_tier=LabelTier.UNKNOWN,
            provenance_type=LabelProvenanceType.UNKNOWN,
            confidence_score=0.0,
            contributing_evidence_ids=[e.evidence_id for e in valid_evidence],
            has_conflicting_evidence=True,
            conflict_resolution_notes=(
                f"Unresolvable conflict between {distinct_classes} at equal tier."
            ),
            is_train_eligible=False,
            is_eval_eligible=False,
            exclusion_reason=ExclusionReason.CONFLICTING_LABEL_EVIDENCE,
            decision_timestamp=timestamp,
        )

    @staticmethod
    def _map_claim_to_vocabulary(target_def: TargetDefinition, claim_class: str) -> str:
        """Normalize raw claim string to match target class vocabulary."""
        claim_norm = claim_class.strip().lower()

        # Direct match
        if claim_norm in target_def.class_vocabulary:
            return claim_norm

        # Target: target_industrial_segregation
        if target_def.target_id == "target_industrial_segregation":
            if claim_norm in (
                "flare",
                "industrial_thermal_source",
                "industrial",
                "power_plant",
                "refinery",
            ):
                return "industrial"
            if claim_norm in (
                "vegetation_wildfire",
                "agricultural_burn",
                "wildfire",
                "non_industrial",
            ):
                return "non_industrial"

        # Target: target_thermal_phenomenon
        if target_def.target_id == "target_thermal_phenomenon":
            if claim_norm in ("refinery_flare", "gas_flare"):
                return "flare"
            if claim_norm in ("industrial", "power_plant", "factory"):
                return "industrial_thermal_source"
            if claim_norm in ("wildfire", "forest_fire"):
                return "vegetation_wildfire"
            if claim_norm in ("crop_burn", "stubble_burn"):
                return "agricultural_burn"

        # Target: target_persistent_combustion
        if target_def.target_id == "target_persistent_combustion":
            if claim_norm in ("persistent", "recurring", "flare"):
                return "persistent_source"
            if claim_norm in ("transient", "wildfire", "agricultural_burn"):
                return "transient_event"

        return "unknown"
