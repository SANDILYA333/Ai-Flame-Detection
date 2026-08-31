"""Live NASA FIRMS -> Production ML End-to-End Integration Service (NEXT-010).

Connects the NASA FIRMS data ingestion pipeline with point-in-time feature
extraction and the NEXT-009 Production ML Runtime Service.

Guarantees:
1. Strict point-in-time feature extraction without future-data leakage.
2. Canonical feat_v1.0.0 schema enforcement (exactly 30 features).
3. Delegation to ProductionMLRuntimeService (HIGH_PRECISION, HIGH_RECALL, SELECTIVE).
4. UNKNOWN != NON_INDUSTRIAL invariant preservation across all paths.
5. Zero leakage of filesystem paths, API keys, or private tokens.
"""

from __future__ import annotations

import csv
import io
import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from packages.config.scientific import ScientificConfig
from packages.data.firms.normalizer import normalize_raw_row_to_detection
from packages.data.firms.schemas import (
    FirmsCountryRequest,
    RawFirmsCsvRow,
)
from packages.events.service import derive_thermal_events
from services.ml.deployment.policy import ProductionOperatingMode
from services.ml.features.extractor import FeatureExtractor
from services.ml.features.standard_set import APPROVED_FEATURES
from services.ml.inference.production_runtime import (
    ProductionMLRuntimeService,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

    from packages.data.firms.client import FirmsClient
    from packages.data.firms.schemas import FirmsAreaRequest
    from packages.schemas.common import UtcDatetime
    from packages.schemas.context import ContextEvidence
    from packages.schemas.detection import Detection
    from packages.schemas.event import Event
    from packages.schemas.source import PersistentSource

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FirmsMLPredictionResult:
    """Structured end-to-end result representing a FIRMS thermal event prediction."""

    event_id: str
    source: str
    event_timestamp: datetime
    centroid_latitude: float
    centroid_longitude: float
    detection_count: int
    max_frp_mw: float | None
    operating_mode: str
    feature_schema_version: str
    feature_count: int
    model_name: str
    model_version: str
    predicted_class: str
    assigned_class: str
    confidence: float
    threshold: float
    class_probabilities: dict[str, float]
    is_abstained: bool
    review_required: bool
    abstention_reason: str | None
    feature_extraction_latency_ms: float
    inference_latency_ms: float
    total_latency_ms: float


def get_default_scientific_config() -> ScientificConfig:
    """Provide calibrated ScientificConfig for real FIRMS event clustering."""
    return ScientificConfig(
        version="v1.0.0-production",
        name="production_thermal_event_clustering",
        description="Calibrated clustering configuration for production FIRMS events",
        spatial_cluster_radius_meters=1000.0,
        temporal_window_hours=2.0,
        persistence_threshold_days=30.0,
        persistence_min_observations=5,
        attribution_radius_meters=1500.0,
        attribution_confidence_threshold=0.7,
        minimum_event_confidence=0.5,
        abstention_confidence_threshold=0.4,
    )


class FirmsProductionMLIntegrationService:
    """Orchestrates NASA FIRMS data ingestion -> Features -> Production ML Runtime."""

    @classmethod
    def evaluate_event(
        cls,
        event: Event,
        member_detections: Sequence[Detection],
        mode: ProductionOperatingMode | str = ProductionOperatingMode.HIGH_PRECISION,
        as_of_time: UtcDatetime | None = None,
        preceding_events: Sequence[Event] | None = None,
        source: PersistentSource | None = None,
        context_evidence: Sequence[ContextEvidence] | None = None,
    ) -> FirmsMLPredictionResult:
        """Evaluate a canonical physical thermal event through point-in-time inference.

        Args:
            event: Canonical thermal event.
            member_detections: Associated detections.
            mode: Operating mode (HIGH_PRECISION, HIGH_RECALL, SELECTIVE).
            as_of_time: UTC temporal cutoff (defaults to event.ended_at).
            preceding_events: Historical events knowable strictly before as_of_time.
            source: Associated persistent thermal source if knowable.
            context_evidence: Matched contextual evidence.

        Returns:
            Structured FirmsMLPredictionResult.
        """
        t_start = time.perf_counter()
        cutoff = as_of_time or event.ended_at

        # 1. Point-in-time feature extraction
        t_feat_0 = time.perf_counter()
        extractor = FeatureExtractor()
        feature_record = extractor.extract_features_for_event(
            event=event,
            member_detections=member_detections,
            as_of_time=cutoff,
            preceding_events=preceding_events,
            source=source,
            context_evidence=context_evidence,
        )
        t_feat_ms = (time.perf_counter() - t_feat_0) * 1000.0

        # 2. Canonical feature contract verification
        features = feature_record.features
        if len(features) != len(APPROVED_FEATURES):
            msg = (
                f"Feature count mismatch: Expected {len(APPROVED_FEATURES)} "
                f"features, got {len(features)}."
            )
            raise ValueError(msg)

        # 3. Delegate to Production ML Runtime Service
        t_inf_0 = time.perf_counter()
        pred_res = ProductionMLRuntimeService.predict_features(
            features=features,
            entity_id=event.event_id,
            mode=mode,
            as_of_time=cutoff,
        )
        t_inf_ms = (time.perf_counter() - t_inf_0) * 1000.0
        t_total_ms = (time.perf_counter() - t_start) * 1000.0

        logger.info(
            "FIRMS ML prediction completed for event %s: class=%s (conf=%.4f, mode=%s)",
            event.event_id,
            pred_res.assigned_class,
            pred_res.confidence,
            pred_res.operating_mode,
        )

        return FirmsMLPredictionResult(
            event_id=event.event_id,
            source="NASA_FIRMS",
            event_timestamp=event.started_at,
            centroid_latitude=event.centroid_geometry.latitude,
            centroid_longitude=event.centroid_geometry.longitude,
            detection_count=len(member_detections),
            max_frp_mw=event.max_frp_mw,
            operating_mode=pred_res.operating_mode,
            feature_schema_version=pred_res.feature_schema_version,
            feature_count=pred_res.feature_count,
            model_name=pred_res.model_name,
            model_version=pred_res.model_version,
            predicted_class=pred_res.predicted_class,
            assigned_class=pred_res.assigned_class,
            confidence=pred_res.confidence,
            threshold=pred_res.threshold,
            class_probabilities=pred_res.class_probabilities,
            is_abstained=pred_res.is_abstained,
            review_required=pred_res.review_required,
            abstention_reason=pred_res.abstention_reason,
            feature_extraction_latency_ms=round(t_feat_ms, 3),
            inference_latency_ms=round(t_inf_ms, 3),
            total_latency_ms=round(t_total_ms, 3),
        )

    @classmethod
    def evaluate_detections(
        cls,
        detections: Sequence[Detection],
        mode: ProductionOperatingMode | str = ProductionOperatingMode.HIGH_PRECISION,
        config: ScientificConfig | None = None,
        preceding_events: Sequence[Event] | None = None,
        sources: Sequence[PersistentSource] | None = None,
        context_evidence: Sequence[ContextEvidence] | None = None,
    ) -> list[FirmsMLPredictionResult]:
        """Cluster raw detections into canonical events and execute batch ML evaluation.

        Args:
            detections: Input Detection instances.
            mode: Target operating mode.
            config: Optional ScientificConfig.
            preceding_events: Historical events for context.
            sources: Known persistent sources.
            context_evidence: Environmental/facility context.

        Returns:
            List of FirmsMLPredictionResult objects for derived events.
        """
        if not detections:
            return []

        active_config = config or get_default_scientific_config()
        events = derive_thermal_events(
            detections=detections,
            config=active_config,
            formation_run_id=f"run_firms_ml_{int(time.time())}",
        )

        results: list[FirmsMLPredictionResult] = []
        for event in events:
            # Match member detections
            member_ids = set(event.detection_ids)
            members = [d for d in detections if d.detection_id in member_ids]
            if not members:
                continue

            # Resolve associated source if applicable
            matched_source = None
            if sources:
                for s in sources:
                    if (
                        s.centroid_geometry.latitude
                        == event.centroid_geometry.latitude
                        and s.centroid_geometry.longitude
                        == event.centroid_geometry.longitude
                    ):
                        matched_source = s
                        break

            res = cls.evaluate_event(
                event=event,
                member_detections=members,
                mode=mode,
                as_of_time=event.ended_at,
                preceding_events=preceding_events,
                source=matched_source,
                context_evidence=context_evidence,
            )
            results.append(res)

        return results

    @classmethod
    def parse_firms_csv_to_detections(
        cls,
        csv_content: str | bytes,
        source_snapshot_id: str = "snap_firms_live",
    ) -> list[Detection]:
        """Parse raw NASA FIRMS CSV rows into canonical Detection objects.

        Args:
            csv_content: CSV text or bytes from NASA FIRMS API or file.
            source_snapshot_id: Lineage identifier.

        Returns:
            List of canonical Detection objects.
        """
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

            # Helper float parser
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
                source_snapshot_id=source_snapshot_id,
            )
            detections.append(det)
        return detections

    @classmethod
    def evaluate_firms_csv(
        cls,
        csv_content: str | bytes,
        mode: ProductionOperatingMode | str = ProductionOperatingMode.HIGH_PRECISION,
        config: ScientificConfig | None = None,
    ) -> list[FirmsMLPredictionResult]:
        """Process raw NASA FIRMS CSV end-to-end to produce ML predictions.

        Args:
            csv_content: NASA FIRMS CSV payload.
            mode: Operating mode.
            config: Optional ScientificConfig.

        Returns:
            List of FirmsMLPredictionResult objects.
        """
        detections = cls.parse_firms_csv_to_detections(csv_content)
        return cls.evaluate_detections(detections=detections, mode=mode, config=config)

    @classmethod
    def fetch_and_evaluate_live(
        cls,
        client: FirmsClient,
        request: FirmsAreaRequest | FirmsCountryRequest,
        mode: ProductionOperatingMode | str = ProductionOperatingMode.HIGH_PRECISION,
        config: ScientificConfig | None = None,
    ) -> list[FirmsMLPredictionResult]:
        """Fetch live detections from NASA FIRMS API and evaluate through ML pipeline.

        Args:
            client: Authenticated FirmsClient instance.
            request: Area or Country query specification.
            mode: Target operating mode.
            config: Optional ScientificConfig.

        Returns:
            List of FirmsMLPredictionResult objects.
        """
        if isinstance(request, FirmsCountryRequest):
            real_url, safe_url = client.build_country_url(request)
        else:
            real_url, safe_url = client.build_area_url(request)

        _, _, csv_bytes = client.execute_request(real_url, safe_url)
        return cls.evaluate_firms_csv(
            csv_content=csv_bytes,
            mode=mode,
            config=config,
        )
