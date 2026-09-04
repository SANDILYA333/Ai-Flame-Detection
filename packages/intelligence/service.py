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
from packages.intelligence.baseline import TemporalBaselineEngine
from packages.physics.pyrometry import DozierPyrometrySolver
from packages.schemas.context import ContextEvidence
from packages.schemas.detection import Detection
from packages.schemas.enums import PersistenceState
from packages.schemas.event import Event
from packages.schemas.intelligence import (
    FeatureAttributionTelemetry,
    IntelligenceResult,
    PyrometryTelemetry,
    ShapExplanationTelemetry,
    TemporalBaselineTelemetry,
)
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
    historical_events: Sequence[Event] | None = None,
    historical_detections: Sequence[Detection] | None = None,
    temporal_baseline: TemporalBaselineTelemetry | None = None,
    pyrometry: PyrometryTelemetry | None = None,
    xai: ShapExplanationTelemetry | None = None,
) -> IntelligenceResult:
    """Derive an evidence-backed, uncertainty-aware canonical IntelligenceResult.

    CRITICAL SCIENTIFIC INTEGRITY INVARIANTS:
    1. Complete config required; incomplete raises MissingConfigurationError.
    2. Proximity to context infrastructure is NOT proof of causality.
    3. Low confidence triggers first-class abstention recommendation.
    4. Evaluates all 6 orthogonal ontology dimensions simultaneously.
    5. Enriches with 90-day rolling baseline, Planck pyrometry, and SHAP.

    Args:
        event: Canonical Event domain model.
        source: Optional associated PersistentSource domain model.
        context_evidence: Optional sequence of associated ContextEvidence objects.
        config: Authoritative ScientificConfig instance.
        pipeline_run_id: Optional pipeline execution identifier.
        model_version: Inference rules engine or model version string.
        notes: Optional analyst or operational notes.
        historical_events: Optional history of events for 90-day baseline calculation.
        historical_detections: Optional historical raw detections.
        temporal_baseline: Explicit baseline override if pre-computed.
        pyrometry: Explicit pyrometry override if pre-computed.
        xai: Explicit XAI explanation override if pre-computed.

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

    # 5. Compute 90-day baseline if not supplied
    final_baseline: TemporalBaselineTelemetry | None = temporal_baseline
    if final_baseline is None:
        try:
            bl_res = TemporalBaselineEngine.calculate_baseline(
                current_event=event,
                historical_events=historical_events,
                historical_detections=historical_detections,
                window_days=90,
                radius_km=1.0,
            )
            final_baseline = TemporalBaselineTelemetry(
                recurrence_90d=bl_res.recurrence_90d,
                historical_mean_frp=bl_res.historical_mean_frp,
                historical_std_frp=bl_res.historical_std_frp,
                sample_count=bl_res.sample_count,
                active_calendar_days=bl_res.active_calendar_days,
                frp_z_score=bl_res.frp_z_score,
                frp_surge_ratio=bl_res.frp_surge_ratio,
                operational_status=bl_res.operational_status,
                is_critical_anomaly=bl_res.is_critical_anomaly,
                window_days=bl_res.window_days,
                radius_km=bl_res.radius_km,
                is_cold_start=bl_res.is_cold_start,
            )
        except Exception as e:
            logger.warning("Failed to derive temporal baseline: %s", e)
            final_baseline = None

    # 6. Compute pyrometry if not supplied
    final_pyrometry: PyrometryTelemetry | None = pyrometry
    if final_pyrometry is None and historical_detections:
        # Find highest MWIR detection in member detections for this event
        valid_dets = [
            d
            for d in historical_detections
            if d.brightness_ti4_k is not None and d.brightness_ti5_k is not None
        ]
        if valid_dets:
            top_det = max(valid_dets, key=lambda d: d.brightness_ti4_k or 0.0)
            if (top_det.brightness_ti4_k or 0.0) > (top_det.brightness_ti5_k or 0.0):
                p_res = DozierPyrometrySolver.solve(
                    bright_mwir_k=top_det.brightness_ti4_k or 300.0,
                    bright_lwir_k=top_det.brightness_ti5_k or 290.0,
                )
                final_pyrometry = PyrometryTelemetry(
                    available=p_res.is_valid,
                    emitter_temp_k=p_res.emitter_temp_k,
                    emitter_area_m2=p_res.emitter_area_m2,
                    fractional_area_p=p_res.fractional_area_p,
                    background_temp_k=p_res.background_temp_k,
                    mwir_radiance_observed=p_res.mwir_radiance_observed,
                    lwir_radiance_observed=p_res.lwir_radiance_observed,
                    radiance_residual=p_res.radiance_residual,
                    is_valid=p_res.is_valid,
                    convergence_status=p_res.convergence_status,
                    phenomenon_tag=p_res.phenomenon_tag,
                )

    # 7. Build canonical IntelligenceResult
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
        temporal_baseline=final_baseline,
        pyrometry=final_pyrometry,
        xai=xai,
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
