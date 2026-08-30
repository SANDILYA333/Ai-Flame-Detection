"""Abstention decision engine and selective classification auditing for Phase 4 ML.

Evaluates predictions against calibrated confidence, uncertainty, and evidence
completeness thresholds, ensuring that abstention is a first-class, auditable outcome.
"""

from packages.schemas.ml import (
    AbstentionContract,
    AbstentionReason,
)


class AbstentionDecisionEngine:
    """Engine deciding when an ML model or intelligence pipeline must abstain."""

    @staticmethod
    def evaluate_abstention(
        confidence: float | None,
        uncertainty: float | None,
        evidence_completeness_ratio: float | None,
        contract: AbstentionContract,
    ) -> tuple[bool, AbstentionReason]:
        """Evaluate if an individual prediction should trigger abstention.

        Returns:
            Tuple of (should_abstain, abstention_reason)
        """
        if not contract.allow_abstention:
            return False, AbstentionReason.NONE

        # 1. Evidence Completeness Check
        if contract.require_evidence_completeness:
            if evidence_completeness_ratio is None:
                return True, AbstentionReason.INSUFFICIENT_EVIDENCE
            if (
                contract.min_completeness_ratio is not None
                and evidence_completeness_ratio < contract.min_completeness_ratio
            ):
                return True, AbstentionReason.INSUFFICIENT_EVIDENCE

        # 2. Confidence Cutoff Check
        if contract.confidence_threshold is not None and (
            confidence is None or confidence < contract.confidence_threshold
        ):
            return True, AbstentionReason.LOW_CONFIDENCE

        # 3. Uncertainty Threshold Check
        if contract.uncertainty_threshold is not None and (
            uncertainty is None or uncertainty > contract.uncertainty_threshold
        ):
            return True, AbstentionReason.HIGH_UNCERTAINTY

        return False, AbstentionReason.NONE

    @staticmethod
    def compute_coverage_and_selective_risk(
        y_true: list[str],
        y_pred: list[str],
        abstention_flags: list[bool],
    ) -> tuple[float, float]:
        """Compute dataset coverage fraction and selective classification risk.

        - Coverage = (Non-abstained count) / (Total count)
        - Selective Risk = (Errors among non-abstained) / (Non-abstained count)
        """
        total = len(y_true)
        if total == 0:
            return 0.0, 0.0

        non_abstained_errors = 0
        non_abstained_count = 0

        for true_val, pred_val, is_abstained in zip(
            y_true, y_pred, abstention_flags, strict=False
        ):
            if not is_abstained:
                non_abstained_count += 1
                if true_val != pred_val:
                    non_abstained_errors += 1

        coverage = float(non_abstained_count / total)
        selective_risk = (
            float(non_abstained_errors / non_abstained_count)
            if non_abstained_count > 0
            else 0.0
        )

        return coverage, selective_risk
