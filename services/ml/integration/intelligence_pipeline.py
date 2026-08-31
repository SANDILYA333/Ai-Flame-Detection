"""Canonical Event -> Context -> Production ML Intelligence Pipeline (NEXT-012).

Integrates:
1. Canonical Thermal Events from NASA FIRMS.
2. Point-in-time Geospatial Context Enrichment & Evidence Attribution.
3. Scientifically honest contextual label adjudication and conflict detection.
4. Authoritative Production ML Runtime (HIGH_PRECISION, HIGH_RECALL, SELECTIVE).
5. Comprehensive ML/Context fusion with explicit uncertainty, abstention preservation,
   and human review triggering.

Guarantees:
- UNKNOWN != NON_INDUSTRIAL under all execution and failure paths.
- Point-in-time temporal cutoff: Zero future context or observation leakage.
- Context is treated as evidence, not absolute ground truth.
- Zero leakage of secrets, API keys, or internal filesystem paths.
"""

from __future__ import annotations

import csv
import hashlib
import io
import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from packages.context.service import enrich_with_context
from packages.data.firms.normalizer import normalize_raw_row_to_detection
from packages.data.firms.schemas import RawFirmsCsvRow
from packages.events.service import derive_thermal_events
from packages.schemas.enums import ContextType
from services.ml.deployment.policy import ProductionOperatingMode
from services.ml.features.extractor import FeatureExtractor
from services.ml.features.standard_set import APPROVED_FEATURES
from services.ml.inference.production_runtime import (
    ProductionMLRuntimeService,
)
from services.ml.integration.firms_pipeline import get_default_scientific_config

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

    from packages.config.scientific import ScientificConfig
    from packages.context.models import ContextFeature
    from packages.schemas.common import UtcDatetime
    from packages.schemas.context import ContextEvidence
    from packages.schemas.detection import Detection
    from packages.schemas.event import Event
    from packages.schemas.source import PersistentSource

logger = logging.getLogger(__name__)

INDUSTRIAL_CONTEXT_TYPES = {
    ContextType.INDUSTRIAL,
    ContextType.OIL_GAS,
    ContextType.POWER,
    ContextType.MINING,
}

NON_INDUSTRIAL_CONTEXT_TYPES = {
    ContextType.AGRICULTURAL,
    ContextType.FOREST_VEGETATION,
}


class IntelligenceAgreementStatus(StrEnum):
    """Categorical agreement status between Production ML and Contextual Evidence."""

    AGREE = "AGREE"
    CONFLICT = "CONFLICT"
    ML_ONLY = "ML_ONLY"
    CONTEXT_ONLY = "CONTEXT_ONLY"
    UNCERTAIN = "UNCERTAIN"


@dataclass(frozen=True)
class ContextAssessment:
    """Structured contextual evidence assessment for an event."""

    context_label: str  # "industrial", "non_industrial", "unknown"
    context_confidence: float  # 0.0 to 1.0
    evidence_count: int
    primary_facility_name: str | None
    primary_context_type: str | None
    primary_distance_meters: float | None
    has_conflicting_context: bool
    evidence_summary: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class EventIntelligenceResult:
    """Canonical Intelligence Result synthesizing Event + Context + Production ML."""

    intelligence_id: str
    event_id: str
    event_timestamp: datetime
    centroid_latitude: float
    centroid_longitude: float
    detection_count: int
    max_frp_mw: float | None
    operating_mode: str

    # ML Assessment
    model_name: str
    model_version: str
    ml_predicted_class: str
    ml_assigned_class: str
    ml_confidence: float
    ml_threshold: float
    ml_class_probabilities: dict[str, float]
    ml_is_abstained: bool
    ml_abstention_reason: str | None

    # Context Assessment
    context_assessment: ContextAssessment

    # Intelligence Synthesis & Decision
    agreement_status: str  # "AGREE", "CONFLICT", "ML_ONLY", "CONTEXT_ONLY", "UNCERTAIN"
    final_classification: str  # "industrial", "non_industrial", "unknown"
    confidence_score: float  # Composite confidence 0.0 to 1.0
    review_required: bool
    review_reasons: list[str]

    # Provenance & Latency
    feature_schema_version: str
    feature_count: int
    event_schema_version: str
    context_schema_version: str
    context_enrichment_latency_ms: float
    feature_extraction_latency_ms: float
    inference_latency_ms: float
    total_latency_ms: float


class EventIntelligencePipelineService:
    """Orchestrates Canonical Event -> Context Enrichment -> ML -> Intelligence."""

    @classmethod
    def adjudicate_context_evidence(
        cls,
        evidence_items: Sequence[ContextEvidence],
        attribution_radius_meters: float = 1500.0,
    ) -> ContextAssessment:
        """Adjudicate context evidence into an explainable contextual assessment."""
        if not evidence_items:
            return ContextAssessment(
                context_label="unknown",
                context_confidence=0.0,
                evidence_count=0,
                primary_facility_name=None,
                primary_context_type=None,
                primary_distance_meters=None,
                has_conflicting_context=False,
                evidence_summary=[],
            )

        industrial_items = [
            e for e in evidence_items if e.context_type in INDUSTRIAL_CONTEXT_TYPES
        ]
        non_industrial_items = [
            e for e in evidence_items if e.context_type in NON_INDUSTRIAL_CONTEXT_TYPES
        ]

        has_conflict = bool(industrial_items and non_industrial_items)

        # Build summary dicts for inspectability
        summary = [
            {
                "context_id": e.context_id,
                "source_type": e.source_type,
                "context_type": e.context_type.value,
                "facility_name": e.facility_name,
                "distance_meters": round(e.distance_to_event_meters or 0.0, 1),
            }
            for e in evidence_items
        ]

        # Closest item determines primary reference
        closest = min(
            evidence_items,
            key=lambda e: e.distance_to_event_meters
            if e.distance_to_event_meters is not None
            else 999999.0,
        )

        # Adjudication logic
        if has_conflict:
            return ContextAssessment(
                context_label="unknown",
                context_confidence=0.40,
                evidence_count=len(evidence_items),
                primary_facility_name=closest.facility_name,
                primary_context_type=closest.context_type.value,
                primary_distance_meters=closest.distance_to_event_meters,
                has_conflicting_context=True,
                evidence_summary=summary,
            )

        if industrial_items:
            dist = closest.distance_to_event_meters or 0.0
            proximity_factor = max(
                0.60, 1.0 - (dist / (attribution_radius_meters * 1.5))
            )
            return ContextAssessment(
                context_label="industrial",
                context_confidence=round(min(0.98, proximity_factor), 4),
                evidence_count=len(evidence_items),
                primary_facility_name=closest.facility_name,
                primary_context_type=closest.context_type.value,
                primary_distance_meters=closest.distance_to_event_meters,
                has_conflicting_context=False,
                evidence_summary=summary,
            )

        if non_industrial_items:
            return ContextAssessment(
                context_label="non_industrial",
                context_confidence=0.90,
                evidence_count=len(evidence_items),
                primary_facility_name=closest.facility_name,
                primary_context_type=closest.context_type.value,
                primary_distance_meters=closest.distance_to_event_meters,
                has_conflicting_context=False,
                evidence_summary=summary,
            )

        return ContextAssessment(
            context_label="unknown",
            context_confidence=0.30,
            evidence_count=len(evidence_items),
            primary_facility_name=closest.facility_name,
            primary_context_type=closest.context_type.value,
            primary_distance_meters=closest.distance_to_event_meters,
            has_conflicting_context=False,
            evidence_summary=summary,
        )

    @classmethod
    def evaluate_event_intelligence(
        cls,
        event: Event,
        member_detections: Sequence[Detection],
        candidate_features: Sequence[ContextFeature] | None = None,
        mode: ProductionOperatingMode | str = ProductionOperatingMode.HIGH_PRECISION,
        as_of_time: UtcDatetime | None = None,
        preceding_events: Sequence[Event] | None = None,
        source: PersistentSource | None = None,
        config: ScientificConfig | None = None,
    ) -> EventIntelligenceResult:
        """Evaluate a single thermal event through the complete intelligence pipeline.

        Args:
            event: Canonical Event domain model.
            member_detections: Associated detections.
            candidate_features: Available geospatial context features.
            mode: Production ML operating mode.
            as_of_time: Prediction cutoff timestamp (UTC).
            preceding_events: Historical events strictly before as_of_time.
            source: Associated persistent thermal source.
            config: Scientific configuration.

        Returns:
            EventIntelligenceResult synthesizing ML, context, and operational decisions.
        """
        t_start = time.perf_counter()
        cutoff = as_of_time or event.ended_at
        active_config = config or get_default_scientific_config()

        # 1. Point-in-Time Context Enrichment
        t_ctx_0 = time.perf_counter()
        matched_context: list[ContextEvidence] = []
        if candidate_features:
            matched_context = enrich_with_context(
                target_id=event.event_id,
                target_coord=event.centroid_geometry,
                target_time=cutoff,
                candidate_features=candidate_features,
                config=active_config,
            )
        t_ctx_ms = (time.perf_counter() - t_ctx_0) * 1000.0

        # 2. Context Label Adjudication
        context_eval = cls.adjudicate_context_evidence(
            evidence_items=matched_context,
            attribution_radius_meters=active_config.attribution_radius_meters or 1500.0,
        )

        # 3. Point-in-Time Feature Extraction (30 canonical features)
        t_feat_0 = time.perf_counter()
        extractor = FeatureExtractor()
        feature_record = extractor.extract_features_for_event(
            event=event,
            member_detections=member_detections,
            as_of_time=cutoff,
            preceding_events=preceding_events,
            source=source,
            context_evidence=matched_context,
        )
        t_feat_ms = (time.perf_counter() - t_feat_0) * 1000.0

        # Validate canonical feature contract
        features = feature_record.features
        if len(features) != len(APPROVED_FEATURES):
            msg = (
                f"Feature count mismatch: Expected {len(APPROVED_FEATURES)} "
                f"features, got {len(features)}."
            )
            raise ValueError(msg)

        # 4. Production ML Runtime Inference
        t_inf_0 = time.perf_counter()
        ml_res = ProductionMLRuntimeService.predict_features(
            features=features,
            entity_id=event.event_id,
            mode=mode,
            as_of_time=cutoff,
        )
        t_inf_ms = (time.perf_counter() - t_inf_0) * 1000.0
        t_total_ms = (time.perf_counter() - t_start) * 1000.0

        # 5. Synthesize ML + Context Agreement & Decision Policy
        ml_class = ml_res.assigned_class  # "industrial", "non_industrial", "unknown"
        ctx_class = context_eval.context_label

        review_reasons: list[str] = []
        review_required = False

        if ml_res.is_abstained:
            review_reasons.append(
                f"ML_ABSTAINED: Model confidence ({ml_res.confidence:.4f}) below "
                f"threshold ({ml_res.threshold:.2f})."
            )

        if context_eval.has_conflicting_context:
            review_reasons.append(
                "CONTEXT_CONFLICT: Contradictory geospatial context features matched."
            )

        # Determine Agreement Status
        agreement_status: IntelligenceAgreementStatus
        final_classification: str
        confidence_score: float

        if ml_class != "unknown" and ctx_class != "unknown":
            if ml_class == ctx_class:
                agreement_status = IntelligenceAgreementStatus.AGREE
                final_classification = ml_class
                confidence_score = round(
                    (ml_res.confidence + context_eval.context_confidence) / 2.0, 4
                )
                review_required = ml_res.review_required
            else:
                agreement_status = IntelligenceAgreementStatus.CONFLICT
                final_classification = "unknown"
                confidence_score = round(
                    min(ml_res.confidence, context_eval.context_confidence), 4
                )
                review_required = True
                review_reasons.append(
                    f"ML_CONTEXT_DISAGREEMENT: ML model assigned '{ml_class}' "
                    f"(conf={ml_res.confidence:.2f}) while Context indicated "
                    f"'{ctx_class}' (conf={context_eval.context_confidence:.2f})."
                )

        elif ml_class != "unknown" and ctx_class == "unknown":
            agreement_status = IntelligenceAgreementStatus.ML_ONLY
            final_classification = ml_class
            confidence_score = ml_res.confidence
            review_required = (
                ml_res.review_required or context_eval.has_conflicting_context
            )

        elif ml_class == "unknown" and ctx_class != "unknown":
            agreement_status = IntelligenceAgreementStatus.CONTEXT_ONLY
            final_classification = ctx_class
            # Discounted confidence because ML abstained
            confidence_score = round(context_eval.context_confidence * 0.80, 4)
            review_required = True
            review_reasons.append(
                f"ML_ABSTAINED_CONTEXT_INDICATED: ML abstained; context suggests "
                f"'{ctx_class}'. Operator confirmation required."
            )

        else:
            agreement_status = IntelligenceAgreementStatus.UNCERTAIN
            final_classification = "unknown"
            confidence_score = 0.0
            review_required = True
            review_reasons.append(
                "INSUFFICIENT_EVIDENCE: Both ML model and context are uncertain."
            )

        # Deterministic Intelligence ID
        raw_key = (
            f"intel:{event.event_id}:{active_config.compute_fingerprint()}:"
            f"{ml_res.model_version}:{ml_res.operating_mode}"
        )
        digest = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        intelligence_id = f"intel_{digest[:24]}"

        logger.info(
            "Event intelligence evaluated for %s: final=%s, agreement=%s, review=%s",
            event.event_id,
            final_classification,
            agreement_status.value,
            review_required,
        )

        return EventIntelligenceResult(
            intelligence_id=intelligence_id,
            event_id=event.event_id,
            event_timestamp=event.started_at,
            centroid_latitude=event.centroid_geometry.latitude,
            centroid_longitude=event.centroid_geometry.longitude,
            detection_count=len(member_detections),
            max_frp_mw=event.max_frp_mw,
            operating_mode=ml_res.operating_mode,
            model_name=ml_res.model_name,
            model_version=ml_res.model_version,
            ml_predicted_class=ml_res.predicted_class,
            ml_assigned_class=ml_res.assigned_class,
            ml_confidence=ml_res.confidence,
            ml_threshold=ml_res.threshold,
            ml_class_probabilities=ml_res.class_probabilities,
            ml_is_abstained=ml_res.is_abstained,
            ml_abstention_reason=ml_res.abstention_reason,
            context_assessment=context_eval,
            agreement_status=agreement_status.value,
            final_classification=final_classification,
            confidence_score=confidence_score,
            review_required=review_required,
            review_reasons=review_reasons,
            feature_schema_version=ml_res.feature_schema_version,
            feature_count=ml_res.feature_count,
            event_schema_version=event.formation_configuration_version,
            context_schema_version="v1.0.0-production",
            context_enrichment_latency_ms=round(t_ctx_ms, 3),
            feature_extraction_latency_ms=round(t_feat_ms, 3),
            inference_latency_ms=round(t_inf_ms, 3),
            total_latency_ms=round(t_total_ms, 3),
        )

    @classmethod
    def evaluate_detections_intelligence(
        cls,
        detections: Sequence[Detection],
        candidate_features: Sequence[ContextFeature] | None = None,
        mode: ProductionOperatingMode | str = ProductionOperatingMode.HIGH_PRECISION,
        config: ScientificConfig | None = None,
        preceding_events: Sequence[Event] | None = None,
        sources: Sequence[PersistentSource] | None = None,
    ) -> list[EventIntelligenceResult]:
        """Cluster raw detections and evaluate intelligence for all derived events."""
        if not detections:
            return []

        active_config = config or get_default_scientific_config()
        events = derive_thermal_events(
            detections=detections,
            config=active_config,
            formation_run_id=f"run_intel_{int(time.time())}",
        )

        results: list[EventIntelligenceResult] = []
        for ev in events:
            member_ids = set(ev.detection_ids)
            members = [d for d in detections if d.detection_id in member_ids]
            if not members:
                continue

            matched_source = None
            if sources:
                for s in sources:
                    if (
                        s.centroid_geometry.latitude == ev.centroid_geometry.latitude
                        and s.centroid_geometry.longitude
                        == ev.centroid_geometry.longitude
                    ):
                        matched_source = s
                        break

            res = cls.evaluate_event_intelligence(
                event=ev,
                member_detections=members,
                candidate_features=candidate_features,
                mode=mode,
                as_of_time=ev.ended_at,
                preceding_events=preceding_events,
                source=matched_source,
                config=active_config,
            )
            results.append(res)

        return results

    @classmethod
    def evaluate_firms_csv_intelligence(
        cls,
        csv_content: str | bytes,
        candidate_features: Sequence[ContextFeature] | None = None,
        mode: ProductionOperatingMode | str = ProductionOperatingMode.HIGH_PRECISION,
        config: ScientificConfig | None = None,
    ) -> list[EventIntelligenceResult]:
        """Parse raw NASA FIRMS CSV and run complete intelligence evaluation."""
        text = (
            csv_content.decode("utf-8", errors="replace")
            if isinstance(csv_content, bytes)
            else csv_content
        )
        reader = csv.DictReader(io.StringIO(text))
        detections: list[Detection] = []
        for row in reader:
            if not row or not row.get("latitude"):
                continue

            def _to_float(val: Any) -> float | None:
                if val is None or val == "":
                    return None
                try:
                    return float(val)
                except ValueError:
                    return None

            raw_row = RawFirmsCsvRow(
                latitude=float(row["latitude"]),
                longitude=float(row["longitude"]),
                acq_date=str(row.get("acq_date", "")).strip(),
                acq_time=str(row.get("acq_time", "")).strip(),
                satellite=str(row.get("satellite", "")).strip(),
                instrument=str(row.get("instrument", "")).strip() or None,
                confidence=str(row.get("confidence", "")).strip() or None,
                version=str(row.get("version", "")).strip() or None,
                bright_ti4=_to_float(row.get("bright_ti4", row.get("brightness"))),
                bright_ti5=_to_float(row.get("bright_ti5", row.get("bright_t31"))),
                scan=_to_float(row.get("scan")),
                track=_to_float(row.get("track")),
                frp=_to_float(row.get("frp")),
                daynight=str(row.get("daynight", "")).strip() or None,
            )
            det = normalize_raw_row_to_detection(
                row=raw_row,
                raw_dict=dict(row),
                source_snapshot_id="snap_firms_intel_live",
            )
            detections.append(det)

        return cls.evaluate_detections_intelligence(
            detections=detections,
            candidate_features=candidate_features,
            mode=mode,
            config=config,
        )
