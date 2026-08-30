"""Canonical domain job handlers for synchronous execution (WORK-001).

Implements standard job handler abstractions for:
- FIRMS raw observation ingestion
- Spatiotemporal thermal event construction
- Contextual enrichment
- Multi-dimensional intelligence derivation
- End-to-end analytical pipeline runs
"""

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from packages.config.scientific import ScientificConfig
from packages.context.models import ContextFeature
from packages.context.service import enrich_with_context
from packages.data.firms.parser import parse_firms_csv
from packages.data.firms.schemas import RealDetectionDataset
from packages.events.pipeline import (
    RealEventConstructionService,
    get_default_calibrated_scientific_config,
)
from packages.intelligence.service import derive_intelligence
from packages.schemas.detection import Detection
from packages.schemas.event import Event, RealThermalEventDataset
from packages.schemas.job import JobType
from packages.schemas.source import PersistentSource
from services.worker.jobs.context import JobContext
from services.worker.jobs.handler import BaseJobHandler


class FIRMSIngestJobHandler(BaseJobHandler):
    """Synchronous job handler for parsing and validating FIRMS observations."""

    @property
    def job_type(self) -> str:
        return JobType.INGEST.value

    def execute(self, context: JobContext, input_reference: Any) -> dict[str, Any]:
        """Execute synchronous parsing of FIRMS CSV input."""
        context.check_cancellation()
        context.report_progress(10.0, "Parsing FIRMS observation payload")

        detections: list[Detection] = []
        if isinstance(input_reference, dict):
            snapshot_id = str(
                input_reference.get("source_snapshot_id", "snap_firms_default")
            )
            if "csv_text" in input_reference:
                csv_text = str(input_reference["csv_text"])
                detections = parse_firms_csv(
                    csv_text, source_snapshot_id=snapshot_id
                )
            elif "file_path" in input_reference:
                path = Path(input_reference["file_path"])
                detections = parse_firms_csv(path, source_snapshot_id=snapshot_id)
            elif "detections" in input_reference:
                raw_dets = input_reference["detections"]
                detections = [
                    d if isinstance(d, Detection) else Detection.model_validate(d)
                    for d in raw_dets
                ]

        context.check_cancellation()
        context.report_progress(
            100.0, f"Successfully parsed {len(detections)} detections"
        )

        return {
            "detection_count": len(detections),
            "source_ids": sorted({d.source for d in detections}),
            "temporal_range": {
                "min": min((d.acquired_at for d in detections), default=None),
                "max": max((d.acquired_at for d in detections), default=None),
            },
        }


class EventConstructJobHandler(BaseJobHandler):
    """Synchronous job handler for event clustering and source tracking."""

    @property
    def job_type(self) -> str:
        return JobType.EVENT_CONSTRUCTION.value

    def execute(self, context: JobContext, input_reference: Any) -> dict[str, Any]:
        context.check_cancellation()
        context.report_progress(10.0, "Validating scientific configuration")

        config: ScientificConfig | None = None
        detections: list[Detection] = []
        detection_dataset: RealDetectionDataset | None = None

        if isinstance(input_reference, dict):
            if "scientific_config" in input_reference:
                cfg_data = input_reference["scientific_config"]
                if isinstance(cfg_data, ScientificConfig):
                    config = cfg_data
                elif isinstance(cfg_data, dict):
                    config = ScientificConfig.model_validate(cfg_data)

            if "detection_dataset" in input_reference:
                ds = input_reference["detection_dataset"]
                detection_dataset = (
                    ds
                    if isinstance(ds, RealDetectionDataset)
                    else RealDetectionDataset.model_validate(ds)
                )
            elif "detections" in input_reference:
                raw_dets = input_reference["detections"]
                detections = [
                    d if isinstance(d, Detection) else Detection.model_validate(d)
                    for d in raw_dets
                ]

        active_config = config or get_default_calibrated_scientific_config()
        active_config.validate_completeness()

        context.check_cancellation()
        context.report_progress(40.0, "Clustering thermal detections into events")

        result: RealThermalEventDataset
        if detection_dataset is not None:
            result = RealEventConstructionService.construct_events_and_sources(
                detection_dataset=detection_dataset,
                config=active_config,
            )
        else:
            result = RealEventConstructionService.construct_events_and_sources(
                detections=detections,
                config=active_config,
            )

        context.check_cancellation()
        context.report_progress(100.0, "Event construction complete")

        return {
            "dataset_id": result.dataset_id,
            "event_count": len(result.events),
            "persistent_source_count": len(result.persistent_sources),
            "detection_count": sum(e.detection_count for e in result.events),
        }


class ContextEnrichJobHandler(BaseJobHandler):
    """Synchronous job handler for contextual enrichment of thermal events."""

    @property
    def job_type(self) -> str:
        return JobType.ENRICH.value

    def execute(self, context: JobContext, input_reference: Any) -> dict[str, Any]:
        context.check_cancellation()
        context.report_progress(10.0, "Preparing event contextual matching")

        events: list[Event] = []
        context_features: list[ContextFeature] = []
        config: ScientificConfig | None = None

        if isinstance(input_reference, dict):
            if "events" in input_reference:
                events = [
                    e if isinstance(e, Event) else Event.model_validate(e)
                    for e in input_reference["events"]
                ]
            if "context_features" in input_reference:
                context_features = [
                    cf
                    if isinstance(cf, ContextFeature)
                    else ContextFeature.model_validate(cf)
                    for cf in input_reference["context_features"]
                ]
            if "scientific_config" in input_reference:
                cfg_data = input_reference["scientific_config"]
                config = (
                    cfg_data
                    if isinstance(cfg_data, ScientificConfig)
                    else ScientificConfig.model_validate(cfg_data)
                )

        active_config = config or get_default_calibrated_scientific_config()
        active_config.validate_completeness()

        context.check_cancellation()
        context.report_progress(50.0, f"Enriching {len(events)} events with context")

        enriched_evidence = []
        for ev in events:
            context.check_cancellation()
            ev_evidence = enrich_with_context(
                target_id=ev.event_id,
                target_coord=ev.centroid_geometry,
                target_time=ev.started_at,
                candidate_features=context_features,
                config=active_config,
            )
            enriched_evidence.extend(ev_evidence)

        context.check_cancellation()
        context.report_progress(100.0, "Contextual enrichment complete")

        return {
            "enriched_event_count": len(events),
            "evidence_item_count": len(enriched_evidence),
        }


class IntelligenceClassifyJobHandler(BaseJobHandler):
    """Synchronous job handler for intelligence derivation and classification."""

    @property
    def job_type(self) -> str:
        return JobType.CLASSIFY.value

    def execute(self, context: JobContext, input_reference: Any) -> dict[str, Any]:
        context.check_cancellation()
        context.report_progress(10.0, "Preparing intelligence derivation")

        events: list[Event] = []
        sources: list[PersistentSource] = []
        config: ScientificConfig | None = None

        if isinstance(input_reference, dict):
            if "events" in input_reference:
                events = [
                    e if isinstance(e, Event) else Event.model_validate(e)
                    for e in input_reference["events"]
                ]
            if "sources" in input_reference:
                sources = [
                    s
                    if isinstance(s, PersistentSource)
                    else PersistentSource.model_validate(s)
                    for s in input_reference["sources"]
                ]
            if "scientific_config" in input_reference:
                cfg_data = input_reference["scientific_config"]
                config = (
                    cfg_data
                    if isinstance(cfg_data, ScientificConfig)
                    else ScientificConfig.model_validate(cfg_data)
                )

        active_config = config or get_default_calibrated_scientific_config()
        active_config.validate_completeness()

        source_by_event_id = {
            ev_id: s for s in sources for ev_id in s.linked_event_ids
        }
        results = []

        context.report_progress(40.0, "Deriving multi-dimensional intelligence")
        for i, ev in enumerate(events):
            context.check_cancellation()
            matched_src = source_by_event_id.get(ev.event_id)
            intel = derive_intelligence(
                event=ev,
                source=matched_src,
                context_evidence=None,
                config=active_config,
                pipeline_run_id=context.pipeline_run_id,
            )
            results.append(intel)
            if len(events) > 0 and i % max(1, len(events) // 5) == 0:
                pct = 40.0 + 50.0 * (i / len(events))
                context.report_progress(pct, f"Evaluated {i+1}/{len(events)} events")

        context.check_cancellation()
        context.report_progress(
            100.0, f"Derived intelligence for {len(results)} events"
        )

        return {
            "intelligence_results_count": len(results),
            "phenomenon_distribution": {
                p.value: sum(1 for r in results if r.phenomenon == p)
                for p in {r.phenomenon for r in results}
            },
        }


class EndToEndPipelineJobHandler(BaseJobHandler):
    """Synchronous job handler executing an end-to-end analytical pipeline."""

    @property
    def job_type(self) -> str:
        return JobType.E2E_PIPELINE.value

    def execute(self, context: JobContext, input_reference: Any) -> dict[str, Any]:
        context.check_cancellation()
        context.report_progress(5.0, "Starting E2E Pipeline run")

        detections: Sequence[Detection] = []
        config: ScientificConfig | None = None

        if isinstance(input_reference, dict):
            if "detections" in input_reference:
                detections = [
                    d if isinstance(d, Detection) else Detection.model_validate(d)
                    for d in input_reference["detections"]
                ]
            if "scientific_config" in input_reference:
                cfg_data = input_reference["scientific_config"]
                config = (
                    cfg_data
                    if isinstance(cfg_data, ScientificConfig)
                    else ScientificConfig.model_validate(cfg_data)
                )

        active_config = config or get_default_calibrated_scientific_config()
        active_config.validate_completeness()

        # Step 1: Event construction
        context.check_cancellation()
        context.report_progress(25.0, f"Clustering {len(detections)} detections")
        event_dataset = RealEventConstructionService.construct_events_and_sources(
            detections=detections,
            config=active_config,
        )

        # Step 2: Intelligence classification
        context.check_cancellation()
        context.report_progress(
            60.0, f"Deriving intelligence for {len(event_dataset.events)} events"
        )
        source_by_event_id = {
            ev_id: s
            for s in event_dataset.persistent_sources
            for ev_id in s.linked_event_ids
        }
        intel_results = [
            derive_intelligence(
                event=ev,
                source=source_by_event_id.get(ev.event_id),
                context_evidence=None,
                config=active_config,
                pipeline_run_id=context.pipeline_run_id,
            )
            for ev in event_dataset.events
        ]

        context.check_cancellation()
        context.report_progress(100.0, "E2E Pipeline execution complete")

        return {
            "status": "success",
            "detection_count": len(detections),
            "event_count": len(event_dataset.events),
            "persistent_source_count": len(event_dataset.persistent_sources),
            "intelligence_results_count": len(intel_results),
        }


class CallableJobHandler(BaseJobHandler):
    """Generic adapter wrapping a callable into a BaseJobHandler."""

    def __init__(
        self,
        job_type_str: str,
        fn: Callable[[JobContext, Any], Any],
    ) -> None:
        self._job_type = job_type_str
        self._fn = fn

    @property
    def job_type(self) -> str:
        return self._job_type

    def execute(self, context: JobContext, input_reference: Any) -> Any:
        return self._fn(context, input_reference)
