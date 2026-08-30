"""Uncertainty representation, confidence calibration, and abstention recommendation."""

from packages.schemas.enums import (
    AttributionStrength,
    EvidenceAvailabilityState,
    PersistenceState,
)
from packages.schemas.event import Event
from packages.schemas.intelligence import (
    EvidenceCompleteness,
    UncertaintyMetric,
)


def calculate_data_quality_score(
    event: Event,
    completeness: EvidenceCompleteness,
) -> float:
    """Calculate composite input data quality score in [0.0, 1.0].

    Evaluates observational sample size, FRP metric validity, and multi-category
    evidence completeness.

    Args:
        event: Canonical Event domain object.
        completeness: Audited evidence completeness structure.

    Returns:
        float: Data quality score between 0.0 and 1.0.
    """
    # 1. Observation robustness (1-3+ detections)
    det_score = min(1.0, float(event.detection_count) / 3.0)

    # 2. FRP measurement completeness
    frp_score = 1.0 if event.mean_frp_mw is not None else 0.5

    # 3. Evidence completeness across categories
    comp_score = completeness.completeness_ratio or 0.0

    # Composite weighted score
    quality = (det_score * 0.4) + (frp_score * 0.2) + (comp_score * 0.4)
    return round(min(1.0, max(0.0, quality)), 4)


def calculate_calibrated_confidence(
    attribution_strength: AttributionStrength,
    persistence_state: PersistenceState,
    data_quality_score: float,
) -> float:
    """Compute post-hoc calibrated confidence score in [0.0, 1.0].

    Integrates spatial attribution proximity, observed temporal persistence,
    and input data quality.

    Args:
        attribution_strength: Classified attribution strength to context.
        persistence_state: Observed temporal persistence state.
        data_quality_score: Evaluated data quality score.

    Returns:
        float: Calibrated confidence score between 0.0 and 1.0.
    """
    attr_weights = {
        AttributionStrength.STRONG: 0.90,
        AttributionStrength.MODERATE: 0.70,
        AttributionStrength.WEAK: 0.50,
        AttributionStrength.UNKNOWN: 0.30,
    }

    pers_weights = {
        PersistenceState.PERSISTENT: 0.90,
        PersistenceState.RECURRING: 0.75,
        PersistenceState.TRANSIENT: 0.60,
        PersistenceState.INSUFFICIENT_HISTORY: 0.35,
    }

    attr_w = attr_weights.get(attribution_strength, 0.30)
    pers_w = pers_weights.get(persistence_state, 0.35)

    confidence = (attr_w * 0.45) + (pers_w * 0.35) + (data_quality_score * 0.20)
    return round(min(1.0, max(0.0, confidence)), 4)


def evaluate_abstention(
    calibrated_confidence: float,
    completeness: EvidenceCompleteness,
    abstention_threshold: float,
) -> tuple[bool, str | None]:
    """Evaluate if the intelligence system should abstain from making a claim.

    CRITICAL SCIENTIFIC INTEGRITY INVARIANT:
    Abstention is a first-class outcome when evidence is insufficient or confidence
    is below the configured abstention threshold.

    Args:
        calibrated_confidence: Calibrated confidence score in [0.0, 1.0].
        completeness: Evidence completeness breakdown.
        abstention_threshold: Configured confidence cutoff for abstention.

    Returns:
        tuple[bool, str | None]: (abstention_recommended, abstention_reason).
    """
    # 1. Provider / critical evidence failure check
    has_unavailable = any(
        c.status == EvidenceAvailabilityState.UNAVAILABLE
        for c in completeness.categories
    )
    if has_unavailable:
        return (
            True,
            "Critical evidence source is unavailable (provider retrieval failure).",
        )

    # 2. Confidence threshold check
    if calibrated_confidence < abstention_threshold:
        return (
            True,
            f"Calibrated confidence ({calibrated_confidence:.2f}) is below "
            f"configured abstention threshold ({abstention_threshold:.2f}).",
        )

    return False, None


def compute_uncertainty_metric(
    event: Event,
    attribution_strength: AttributionStrength,
    persistence_state: PersistenceState,
    completeness: EvidenceCompleteness,
    abstention_threshold: float,
) -> UncertaintyMetric:
    """Compute structured UncertaintyMetric for intelligence result."""
    data_quality = calculate_data_quality_score(event, completeness)
    calibrated_conf = calculate_calibrated_confidence(
        attribution_strength=attribution_strength,
        persistence_state=persistence_state,
        data_quality_score=data_quality,
    )
    abstain, reason = evaluate_abstention(
        calibrated_confidence=calibrated_conf,
        completeness=completeness,
        abstention_threshold=abstention_threshold,
    )

    return UncertaintyMetric(
        model_probability=calibrated_conf,
        calibrated_confidence=calibrated_conf,
        data_quality_score=data_quality,
        abstention_recommended=abstain,
        abstention_reason=reason,
    )
