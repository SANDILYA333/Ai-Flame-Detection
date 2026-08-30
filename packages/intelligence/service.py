"""High-level thermal intelligence and inference derivation service.

Synthesizes the complete Phase 3 scientific derivation chain:
DETECTIONS -> EVENT -> SOURCE -> CONTEXT -> INTELLIGENCE
"""

import logging
from collections.abc import Sequence

from packages.config.scientific import ScientificConfig
from packages.intelligence.builder import build_intelligence_result
from packages.intelligence.completeness import evaluate_evidence_completeness
from packages.intelligence.reasoning import (
    infer_attribution_strength,
    infer_context_type,
    infer_phenomenon_type,
)
from packages.intelligence.uncertainty import compute_uncertainty_metric
from packages.schemas.context import ContextEvidence
from packages.schemas.enums import PersistenceState
from packages.schemas.event import Event
from packages.schemas.intelligence import IntelligenceResult
from packages.schemas.source import PersistentSource

logger = logging.getLogger(__name__)


def derive_intelligence(
    event: Event,
    source: PersistentSource | None,
    context_evidence: Sequence[ContextEvidence] | None,
    config: ScientificConfig,
    pipeline_run_id: str | None = None,
    model_version: str | None = "v1.0-rules-engine",
    notes: str | None = None,
) -> IntelligenceResult:
    """Derive an evidence-backed, uncertainty-aware canonical IntelligenceResult.

    CRITICAL SCIENTIFIC INTEGRITY INVARIANTS:
    1. Complete config required; incomplete raises MissingConfigurationError.
    2. Proximity to context infrastructure is NOT proof of causality.
    3. Low confidence triggers first-class abstention recommendation.
    4. Evaluates all 6 orthogonal ontology dimensions simultaneously.

    Args:
        event: Canonical Event domain model.
        source: Optional associated PersistentSource domain model.
        context_evidence: Optional sequence of associated ContextEvidence objects.
        config: Authoritative ScientificConfig instance.
        pipeline_run_id: Optional pipeline execution identifier.
        model_version: Inference rules engine or model version string.
        notes: Optional analyst or operational notes.

    Returns:
        IntelligenceResult: Canonical validated IntelligenceResult domain model.

    Raises:
        MissingConfigurationError: If any required scientific parameter is unset.
    """
    # 1. Authoritative configuration completeness check
    config.validate_completeness()

    attr_radius_m = config.attribution_radius_meters
    abstain_thresh = config.abstention_confidence_threshold
    assert attr_radius_m is not None
    assert abstain_thresh is not None

    # 2. Audit multi-category evidence completeness
    completeness = evaluate_evidence_completeness(
        event=event,
        source=source,
        context_evidence=context_evidence,
    )

    # 3. Resolve orthogonal dimensions
    persistence_state = (
        source.persistence_state
        if source is not None
        else (
            PersistenceState.INSUFFICIENT_HISTORY
            if event.duration_seconds == 0.0 and event.detection_count == 1
            else PersistenceState.TRANSIENT
        )
    )

    context_type = infer_context_type(context_evidence)

    attribution_strength = infer_attribution_strength(
        context_evidence=context_evidence,
        attribution_radius_meters=attr_radius_m,
    )

    phenomenon_type = infer_phenomenon_type(
        persistence_state=persistence_state,
        context_type=context_type,
        event=event,
    )

    # 4. Compute uncertainty and abstention recommendation
    uncertainty = compute_uncertainty_metric(
        event=event,
        attribution_strength=attribution_strength,
        persistence_state=persistence_state,
        completeness=completeness,
        abstention_threshold=abstain_thresh,
    )

    # 5. Build canonical IntelligenceResult
    result = build_intelligence_result(
        event=event,
        source=source,
        context_evidence=context_evidence,
        phenomenon=phenomenon_type,
        context_type=context_type,
        persistence_state=persistence_state,
        attribution_strength=attribution_strength,
        uncertainty=uncertainty,
        completeness=completeness,
        config=config,
        pipeline_run_id=pipeline_run_id,
        model_version=model_version,
        notes=notes,
    )

    logger.info(
        "Derived intelligence %s for event %s (phenomenon: %s, context: %s, "
        "attribution: %s, abstain: %s)",
        result.intelligence_id,
        event.event_id,
        result.phenomenon,
        result.context,
        result.attribution,
        result.uncertainty.abstention_recommended,
    )

    return result
