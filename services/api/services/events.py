"""Application service for querying canonical thermal events (API-006)."""

from datetime import UTC, datetime

from packages.context.pipeline import RealContextLabelingService
from packages.errors import ErrorCode, NotFoundError, ValidationError
from packages.events.pipeline import (
    RealEventConstructionService,
    get_default_calibrated_scientific_config,
)
from packages.geospatial.distance import haversine_distance_meters
from packages.intelligence.service import derive_intelligence
from packages.schemas.event import RealEnrichedEventDataset
from packages.schemas.intelligence import IntelligenceResult
from services.api.schemas.events import (
    EventDetailResponse,
    EventEvidenceResponse,
    EventPagination,
    EventResponse,
    EventsResponse,
    EventTimelineResponse,
    TimelineObservation,
)
from services.api.services.detections import DetectionQueryService

_CONTEXT_FIXTURE_PATH = "fixtures/context/context_sample_jamnagar.json"


class EventQueryService:
    """Service orchestrating querying, filtering, and pagination of events."""

    _cached_dataset: RealEnrichedEventDataset | None = None

    @classmethod
    def get_canonical_enriched_dataset(cls) -> RealEnrichedEventDataset:
        """Load and cache canonical enriched event dataset."""
        if cls._cached_dataset is None:
            # 1. Fetch raw detections
            detections = DetectionQueryService.get_canonical_detections()

            # 2. Derive thermal events & persistent sources
            thermal_dataset = RealEventConstructionService.construct_events_and_sources(
                detections=detections,
            )

            # 3. Load context features
            try:
                candidate_features, hashes = (
                    RealContextLabelingService.load_context_features_from_fixture(
                        _CONTEXT_FIXTURE_PATH
                    )
                )
            except FileNotFoundError:
                candidate_features = []
                hashes = {}

            # 4. Enrich & adjudicate labels
            enriched_dataset = RealContextLabelingService.enrich_and_adjudicate_dataset(
                event_dataset=thermal_dataset,
                candidate_features=candidate_features,
                snapshot_hashes=hashes,
            )

            cls._cached_dataset = enriched_dataset

        return cls._cached_dataset

    @classmethod
    def set_mock_dataset(cls, dataset: RealEnrichedEventDataset | None) -> None:
        """Override cached dataset for testing purposes."""
        cls._cached_dataset = dataset

    @classmethod
    def query_events(
        cls,
        *,
        min_lat: float | None = None,
        max_lat: float | None = None,
        min_lon: float | None = None,
        max_lon: float | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        status: str | None = None,
        classification_state: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> EventsResponse:
        """Query canonical events with spatial, temporal, and semantic filters."""
        # 1. Validate bounding box coordinates
        bbox_coords = [min_lat, max_lat, min_lon, max_lon]
        has_any_bbox = any(c is not None for c in bbox_coords)
        has_all_bbox = all(c is not None for c in bbox_coords)

        if has_any_bbox and not has_all_bbox:
            raise ValidationError(
                "Bounding box query requires all four coordinates: "
                "min_lat, max_lat, min_lon, max_lon."
            )

        if has_all_bbox:
            assert min_lat is not None and max_lat is not None
            assert min_lon is not None and max_lon is not None
            if min_lat > max_lat:
                raise ValidationError("Bounding box min_lat cannot exceed max_lat.")
            if min_lon > max_lon:
                raise ValidationError("Bounding box min_lon cannot exceed max_lon.")

        # 2. Validate time range boundaries
        if start_time is not None and start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=UTC)
        if end_time is not None and end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=UTC)

        if start_time is not None and end_time is not None and start_time > end_time:
            raise ValidationError("start_time cannot be later than end_time.")

        # 3. Retrieve canonical dataset
        dataset = cls.get_canonical_enriched_dataset()

        # Build quick lookups for filtering
        label_lookup = {
            lbl.entity_id: lbl.assigned_class for lbl in dataset.reference_labels
        }
        # Remove unused source_lookup
        event_to_persistence = {}
        for src in dataset.persistent_sources:
            for ev_id in src.linked_event_ids:
                event_to_persistence[ev_id] = src.persistence_state.value

        # 4. Apply filtering
        filtered: list[EventResponse] = []
        for ev in dataset.events:
            # Spatial filter (centroid)
            if has_all_bbox:
                assert min_lat is not None and max_lat is not None
                assert min_lon is not None and max_lon is not None
                lat = ev.centroid_geometry.latitude
                lon = ev.centroid_geometry.longitude
                if not (min_lat <= lat <= max_lat and min_lon <= lon <= max_lon):
                    continue

            # Temporal filter (overlap logic: event started before window ended
            # AND ended after window started)
            if start_time is not None and ev.ended_at < start_time:
                continue
            if end_time is not None and ev.started_at > end_time:
                continue

            # Classification state filter
            assigned_class = label_lookup.get(ev.event_id)
            if (
                classification_state is not None
                and assigned_class != classification_state
            ):
                continue

            # Status filter (mapping to persistence state)
            pers_state = event_to_persistence.get(ev.event_id)
            if status is not None and status != pers_state:
                continue

            filtered.append(
                EventResponse(
                    event_id=ev.event_id,
                    started_at=ev.started_at,
                    ended_at=ev.ended_at,
                    duration_seconds=ev.duration_seconds,
                    centroid_latitude=ev.centroid_geometry.latitude,
                    centroid_longitude=ev.centroid_geometry.longitude,
                    detection_count=ev.detection_count,
                    mean_frp_mw=ev.mean_frp_mw,
                    max_frp_mw=ev.max_frp_mw,
                    classification_state=assigned_class,
                    persistence_state=pers_state,
                )
            )

        # 5. Deterministic sorting: started_at ascending, then event_id ascending
        filtered.sort(key=lambda d: (d.started_at, d.event_id))

        # 6. Apply pagination
        total_count = len(filtered)
        paginated_events = filtered[offset : offset + limit]
        has_next = (offset + limit) < total_count

        pagination = EventPagination(
            total_count=total_count,
            limit=limit,
            offset=offset,
            has_next=has_next,
        )

        return EventsResponse(
            service="sih26162-api",
            pagination=pagination,
            events=paginated_events,
        )

    @classmethod
    def get_event(cls, event_id: str) -> EventDetailResponse:
        """Retrieve canonical event detail (API-007)."""
        dataset = cls.get_canonical_enriched_dataset()

        target_event = next(
            (ev for ev in dataset.events if ev.event_id == event_id), None
        )
        if target_event is None:
            raise NotFoundError(
                message=f"Thermal event '{event_id}' not found.",
                code=ErrorCode.RESOURCE_NOT_FOUND,
            )

        label = next(
            (lbl for lbl in dataset.reference_labels if lbl.entity_id == event_id), None
        )

        context_status = (
            "AVAILABLE" if label and label.contributing_evidence_ids else "UNAVAILABLE"
        )
        intelligence_status = label.assigned_class if label else None

        return EventDetailResponse(
            event_id=target_event.event_id,
            geometry={
                "type": "Point",
                "coordinates": [
                    target_event.centroid_geometry.longitude,
                    target_event.centroid_geometry.latitude,
                ],
            },
            started_at=target_event.started_at,
            ended_at=target_event.ended_at,
            duration_seconds=target_event.duration_seconds,
            detection_count=target_event.detection_count,
            context_status=context_status,
            intelligence_status=intelligence_status,
        )

    @classmethod
    def get_event_timeline(cls, event_id: str) -> EventTimelineResponse:
        """Retrieve canonical event timeline (API-008)."""
        dataset = cls.get_canonical_enriched_dataset()

        target_event = next(
            (ev for ev in dataset.events if ev.event_id == event_id), None
        )
        if target_event is None:
            raise NotFoundError(
                message=f"Thermal event '{event_id}' not found.",
                code=ErrorCode.RESOURCE_NOT_FOUND,
            )

        # Retrieve canonical detections
        all_detections = DetectionQueryService.get_canonical_detections()
        event_det_ids = set(target_event.detection_ids)

        member_detections = [
            d for d in all_detections if d.detection_id in event_det_ids
        ]

        timeline = [
            TimelineObservation(
                timestamp=d.acquired_at,
                detection_id=d.detection_id,
                latitude=d.geometry.latitude,
                longitude=d.geometry.longitude,
                source=d.source,
                frp_mw=d.frp_mw,
                confidence=d.confidence,
            )
            for d in member_detections
        ]

        # Deterministic sorting (acquired_at, then detection_id)
        timeline.sort(key=lambda t: (t.timestamp, t.detection_id))

        return EventTimelineResponse(
            event_id=target_event.event_id,
            started_at=target_event.started_at,
            ended_at=target_event.ended_at,
            timeline=timeline,
        )

    @classmethod
    def get_event_evidence(cls, event_id: str) -> EventEvidenceResponse:
        """Retrieve canonical event evidence (API-009)."""
        dataset = cls.get_canonical_enriched_dataset()

        target_event = next(
            (ev for ev in dataset.events if ev.event_id == event_id), None
        )
        if target_event is None:
            raise NotFoundError(
                message=f"Thermal event '{event_id}' not found.",
                code=ErrorCode.RESOURCE_NOT_FOUND,
            )

        config = get_default_calibrated_scientific_config()

        context_evidence = [
            ce
            for ce in dataset.context_evidence
            if haversine_distance_meters(
                target_event.centroid_geometry.latitude,
                target_event.centroid_geometry.longitude,
                ce.geometry.latitude,
                ce.geometry.longitude,
            )
            <= (config.attribution_radius_meters or 1500.0)
        ]
        reference_evidence = [
            re for re in dataset.reference_evidence if re.entity_id == event_id
        ]

        return EventEvidenceResponse(
            event_id=event_id,
            context_evidence=context_evidence,
            reference_evidence=reference_evidence,
        )

    @classmethod
    def get_event_intelligence(cls, event_id: str) -> IntelligenceResult:
        """Retrieve canonical event intelligence (API-011)."""
        dataset = cls.get_canonical_enriched_dataset()

        target_event = next(
            (ev for ev in dataset.events if ev.event_id == event_id), None
        )
        if target_event is None:
            raise NotFoundError(
                message=f"Thermal event '{event_id}' not found.",
                code=ErrorCode.RESOURCE_NOT_FOUND,
            )

        source = next(
            (s for s in dataset.persistent_sources if event_id in s.linked_event_ids),
            None,
        )

        config = get_default_calibrated_scientific_config()

        context_evidence = [
            ce
            for ce in dataset.context_evidence
            if haversine_distance_meters(
                target_event.centroid_geometry.latitude,
                target_event.centroid_geometry.longitude,
                ce.geometry.latitude,
                ce.geometry.longitude,
            )
            <= (config.attribution_radius_meters or 1500.0)
        ]

        return derive_intelligence(
            event=target_event,
            source=source,
            context_evidence=context_evidence,
            config=config,
            pipeline_run_id=None,
        )
