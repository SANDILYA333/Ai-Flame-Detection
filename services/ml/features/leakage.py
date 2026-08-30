"""Leakage audit framework for Phase 4 ML.

Audits feature definitions, derivation rules, and data representations for:
- Direct target leakage (using reference labels as features)
- Temporal leakage (using future observations relative to prediction time)
- Spatial / Source leakage (unpartitioned group statistics across sources)
- Label contamination (encoding target distribution into feature mappings)
"""

from pydantic import Field

from packages.schemas.common import BaseDomainModel
from packages.schemas.ml import (
    FeatureDefinition,
    LeakageRisk,
    TargetDefinition,
)


class LeakageViolation(BaseDomainModel):
    """Specific leakage violation finding."""

    feature_name: str = Field(..., min_length=1)
    risk_type: LeakageRisk = Field(...)
    reason: str = Field(..., min_length=1)
    recommendation: str = Field(..., min_length=1)


class LeakageAuditReport(BaseDomainModel):
    """Audit report summarizing data and feature leakage findings."""

    is_safe: bool = Field(
        ...,
        description="True if zero leakage risks were detected across features.",
    )
    total_audited: int = Field(0, ge=0)
    safe_count: int = Field(0, ge=0)
    violation_count: int = Field(0, ge=0)
    violations: list[LeakageViolation] = Field(default_factory=list)
    safe_features: list[str] = Field(default_factory=list)


class LeakageAuditor:
    """Auditor analyzing features for direct, temporal, spatial, and label leakage."""

    # Disallowed upstream sources for ML features
    DISALLOWED_SOURCE_ENTITIES: frozenset[str] = frozenset(
        {
            "ReferenceLabel",
            "GroundTruth",
            "AnnotationRegistry",
            "AdjudicationResult",
            "TargetDefinition",
        }
    )

    # Keywords in derivations indicating forward-looking or contaminated logic
    SUSPICIOUS_FUTURE_KEYWORDS: frozenset[str] = frozenset(
        {
            "future",
            "next_observation",
            "following_day",
            "subsequent",
            "post_event",
            "hindsight",
            "after_prediction",
        }
    )

    def audit_feature(
        self,
        feature: FeatureDefinition,
        target_definition: TargetDefinition | None = None,
    ) -> list[LeakageViolation]:
        """Audit a single feature definition for leakage risks."""
        violations: list[LeakageViolation] = []

        # 1. Check explicit leakage risk tag
        if feature.leakage_risk in (
            LeakageRisk.DIRECT_LEAKAGE,
            LeakageRisk.INDIRECT_LEAKAGE,
            LeakageRisk.TEMPORAL_LEAKAGE,
            LeakageRisk.SPATIAL_LEAKAGE,
            LeakageRisk.LABEL_CONTAMINATION,
        ):
            reason = (
                feature.leakage_justification
                or f"Feature explicitly categorized with {feature.leakage_risk.value}."
            )
            violations.append(
                LeakageViolation(
                    feature_name=feature.feature_name,
                    risk_type=feature.leakage_risk,
                    reason=reason,
                    recommendation="Remove feature or refactor derivation.",
                )
            )

        # 2. Check source entity for direct label leakage
        if feature.source_entity in self.DISALLOWED_SOURCE_ENTITIES:
            violations.append(
                LeakageViolation(
                    feature_name=feature.feature_name,
                    risk_type=LeakageRisk.DIRECT_LEAKAGE,
                    reason=(
                        f"Feature derives from disallowed reference entity "
                        f"'{feature.source_entity}'."
                    ),
                    recommendation="Disallow feature (allowed_for_training=False).",
                )
            )

        # 3. Check derivation description for forward-looking temporal phrases
        derivation_lower = feature.derivation_description.lower()
        for kw in self.SUSPICIOUS_FUTURE_KEYWORDS:
            if kw in derivation_lower:
                violations.append(
                    LeakageViolation(
                        feature_name=feature.feature_name,
                        risk_type=LeakageRisk.TEMPORAL_LEAKAGE,
                        reason=f"Derivation contains future temporal keyword '{kw}'.",
                        recommendation=(
                            "Utilize only observations prior to event timestamp."
                        ),
                    )
                )
                break

        # 4. Check class vocabulary overlap with feature name or derivation
        if target_definition is not None:
            for cls_name in target_definition.class_vocabulary:
                if (
                    cls_name.lower() in feature.feature_name.lower()
                    and feature.source_entity not in ("Detection", "ContextEvidence")
                    and feature.leakage_risk == LeakageRisk.UNKNOWN
                ):
                    violations.append(
                        LeakageViolation(
                            feature_name=feature.feature_name,
                            risk_type=LeakageRisk.LABEL_CONTAMINATION,
                            reason=(
                                f"Feature name matches target class "
                                f"vocabulary '{cls_name}'."
                            ),
                            recommendation=(
                                "Verify feature is an independent observation."
                            ),
                        )
                    )

        return violations

    def audit_feature_set(
        self,
        features: list[FeatureDefinition],
        target_definition: TargetDefinition | None = None,
    ) -> LeakageAuditReport:
        """Audit an entire set of feature definitions for scientific integrity."""
        all_violations: list[LeakageViolation] = []
        safe_names: list[str] = []

        for feat in features:
            v = self.audit_feature(feat, target_definition=target_definition)
            if v:
                all_violations.extend(v)
            else:
                safe_names.append(feat.feature_name)

        is_safe = len(all_violations) == 0
        return LeakageAuditReport(
            is_safe=is_safe,
            total_audited=len(features),
            safe_count=len(safe_names),
            violation_count=len(all_violations),
            violations=all_violations,
            safe_features=sorted(safe_names),
        )
