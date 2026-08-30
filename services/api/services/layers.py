"""Application service for querying GeoJSON map layers (API-012, GIS-001)."""

from datetime import datetime

from packages.context.models import ContextFeature
from packages.context.pipeline import (
    INDUSTRIAL_CONTEXT_TYPES,
    RealContextLabelingService,
)
from packages.errors import ErrorCode, ValidationError
from packages.geospatial.geojson import (
    serialize_context_feature_to_geojson,
    serialize_detection_to_geojson,
    serialize_event_to_geojson,
    serialize_persistent_source_to_geojson,
    to_geojson_feature_collection,
)
from services.api.schemas.layers import (
    GeoJsonFeature,
    GeoJsonFeatureCollection,
)
from services.api.services.detections import DetectionQueryService
from services.api.services.events import EventQueryService

_CONTEXT_FIXTURE_PATH = "fixtures/context/context_sample_jamnagar.json"


class LayerQueryService:
    """Service providing RFC 7946 GeoJSON map layers for frontend GIS visualization."""

    _cached_context_features: list[ContextFeature] | None = None

    @classmethod
    def _get_context_features(cls) -> list[ContextFeature]:
        """Load and cache external context features from fixture."""
        if cls._cached_context_features is None:
            try:
                features, _ = (
                    RealContextLabelingService.load_context_features_from_fixture(
                        _CONTEXT_FIXTURE_PATH
                    )
                )
                cls._cached_context_features = features
            except FileNotFoundError:
                cls._cached_context_features = []
        return cls._cached_context_features

    @staticmethod
    def _validate_bbox(
        min_lat: float | None,
        max_lat: float | None,
        min_lon: float | None,
        max_lon: float | None,
    ) -> None:
        """Validate bounding box coordinate consistency."""
        if min_lat is not None and max_lat is not None and min_lat > max_lat:
            raise ValidationError(
                message="min_lat cannot be greater than max_lat",
                code=ErrorCode.VALIDATION_ERROR,
                details={"min_lat": min_lat, "max_lat": max_lat},
            )
        if min_lon is not None and max_lon is not None and min_lon > max_lon:
            raise ValidationError(
                message="min_lon cannot be greater than max_lon",
                code=ErrorCode.VALIDATION_ERROR,
                details={"min_lon": min_lon, "max_lon": max_lon},
            )

    @classmethod
    def get_events_layer(
        cls,
        min_lat: float | None = None,
        max_lat: float | None = None,
        min_lon: float | None = None,
        max_lon: float | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        status: str | None = None,
        classification_state: str | None = None,
        min_frp_mw: float | None = None,
        geometry_type: str = "point",
        limit: int = 100,
        offset: int = 0,
    ) -> GeoJsonFeatureCollection:
        """Query and serialize canonical events into a GeoJSON FeatureCollection."""
        cls._validate_bbox(min_lat, max_lat, min_lon, max_lon)
        dataset = EventQueryService.get_canonical_enriched_dataset()
        events = list(dataset.events)

        # Build lookup maps for classification and persistence states
        label_map: dict[str, str] = {}
        for lbl in dataset.reference_labels:
            if lbl.entity_id and lbl.assigned_class:
                label_map[lbl.entity_id] = lbl.assigned_class

        persistence_map: dict[str, str] = {}
        for src in dataset.persistent_sources:
            for eid in src.linked_event_ids:
                persistence_map[eid] = src.persistence_state.value

        # 1. Spatial bounding box filter
        if min_lat is not None:
            events = [e for e in events if e.centroid_geometry.latitude >= min_lat]
        if max_lat is not None:
            events = [e for e in events if e.centroid_geometry.latitude <= max_lat]
        if min_lon is not None:
            events = [e for e in events if e.centroid_geometry.longitude >= min_lon]
        if max_lon is not None:
            events = [e for e in events if e.centroid_geometry.longitude <= max_lon]

        # 2. Temporal filter
        if start_time is not None:
            events = [e for e in events if e.ended_at >= start_time]
        if end_time is not None:
            events = [e for e in events if e.started_at <= end_time]

        # 3. Classification state filter
        if classification_state is not None:
            target_class = classification_state.strip().lower()
            events = [
                e
                for e in events
                if label_map.get(e.event_id, "").lower() == target_class
            ]

        # 4. FRP filter
        if min_frp_mw is not None:
            events = [
                e
                for e in events
                if (e.max_frp_mw is not None and e.max_frp_mw >= min_frp_mw)
                or (e.mean_frp_mw is not None and e.mean_frp_mw >= min_frp_mw)
            ]

        # 5. Deterministic pagination
        paged_events = events[offset : offset + limit]

        # 6. Serialize to GeoJSON Features via canonical serializer
        raw_features = [
            serialize_event_to_geojson(
                ev,
                geometry_type=geometry_type,
                classification_state=label_map.get(ev.event_id),
                persistence_state=persistence_map.get(ev.event_id),
            )
            for ev in paged_events
        ]

        # 7. Compute layer bounding box
        bbox: list[float] | None = None
        if raw_features:
            all_lons: list[float] = []
            all_lats: list[float] = []
            for f in raw_features:
                geom = f["geometry"]
                if geom["type"] == "Point":
                    all_lons.append(geom["coordinates"][0])
                    all_lats.append(geom["coordinates"][1])
                elif geom["type"] == "Polygon" and geom["coordinates"]:
                    for pt in geom["coordinates"][0]:
                        all_lons.append(pt[0])
                        all_lats.append(pt[1])
            if all_lons and all_lats:
                bbox = [min(all_lons), min(all_lats), max(all_lons), max(all_lats)]

        fc_dict = to_geojson_feature_collection(raw_features, bbox=bbox)
        return GeoJsonFeatureCollection(
            type="FeatureCollection",
            features=[GeoJsonFeature.model_validate(f) for f in fc_dict["features"]],
            bbox=fc_dict.get("bbox"),
        )

    @classmethod
    def get_persistent_sources_layer(
        cls,
        min_lat: float | None = None,
        max_lat: float | None = None,
        min_lon: float | None = None,
        max_lon: float | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> GeoJsonFeatureCollection:
        """Query and serialize persistent sources into a GeoJSON FeatureCollection."""
        cls._validate_bbox(min_lat, max_lat, min_lon, max_lon)
        dataset = EventQueryService.get_canonical_enriched_dataset()
        sources = list(dataset.persistent_sources)

        # 1. Spatial bounding box filter
        if min_lat is not None:
            sources = [s for s in sources if s.centroid_geometry.latitude >= min_lat]
        if max_lat is not None:
            sources = [s for s in sources if s.centroid_geometry.latitude <= max_lat]
        if min_lon is not None:
            sources = [s for s in sources if s.centroid_geometry.longitude >= min_lon]
        if max_lon is not None:
            sources = [s for s in sources if s.centroid_geometry.longitude <= max_lon]

        # 2. Pagination
        paged_sources = sources[offset : offset + limit]

        # 3. Serialize to GeoJSON Features via canonical serializer
        raw_features = [
            serialize_persistent_source_to_geojson(s) for s in paged_sources
        ]

        bbox: list[float] | None = None
        if raw_features:
            lons = [f["geometry"]["coordinates"][0] for f in raw_features]
            lats = [f["geometry"]["coordinates"][1] for f in raw_features]
            bbox = [min(lons), min(lats), max(lons), max(lats)]

        fc_dict = to_geojson_feature_collection(raw_features, bbox=bbox)
        return GeoJsonFeatureCollection(
            type="FeatureCollection",
            features=[GeoJsonFeature.model_validate(f) for f in fc_dict["features"]],
            bbox=fc_dict.get("bbox"),
        )

    @classmethod
    def get_industrial_layer(
        cls,
        min_lat: float | None = None,
        max_lat: float | None = None,
        min_lon: float | None = None,
        max_lon: float | None = None,
        context_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> GeoJsonFeatureCollection:
        """Query and serialize industrial contextual infrastructure into GeoJSON."""
        cls._validate_bbox(min_lat, max_lat, min_lon, max_lon)
        all_features = cls._get_context_features()

        # 1. Industrial context filter
        features = [
            f for f in all_features if f.context_type in INDUSTRIAL_CONTEXT_TYPES
        ]

        # 2. Specific context_type filter
        if context_type is not None:
            target = context_type.lower()
            features = [f for f in features if f.context_type.value.lower() == target]

        # 3. Spatial bounding box filter
        if min_lat is not None:
            features = [f for f in features if f.geometry.latitude >= min_lat]
        if max_lat is not None:
            features = [f for f in features if f.geometry.latitude <= max_lat]
        if min_lon is not None:
            features = [f for f in features if f.geometry.longitude >= min_lon]
        if max_lon is not None:
            features = [f for f in features if f.geometry.longitude <= max_lon]

        # 4. Pagination
        paged_features = features[offset : offset + limit]

        # 5. Serialize to GeoJSON Features via canonical serializer
        raw_features = [
            serialize_context_feature_to_geojson(feat) for feat in paged_features
        ]

        bbox: list[float] | None = None
        if raw_features:
            lons = [f["geometry"]["coordinates"][0] for f in raw_features]
            lats = [f["geometry"]["coordinates"][1] for f in raw_features]
            bbox = [min(lons), min(lats), max(lons), max(lats)]

        fc_dict = to_geojson_feature_collection(raw_features, bbox=bbox)
        return GeoJsonFeatureCollection(
            type="FeatureCollection",
            features=[GeoJsonFeature.model_validate(f) for f in fc_dict["features"]],
            bbox=fc_dict.get("bbox"),
        )

    @classmethod
    def get_land_cover_layer(
        cls,
        min_lat: float | None = None,
        max_lat: float | None = None,
        min_lon: float | None = None,
        max_lon: float | None = None,
        context_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> GeoJsonFeatureCollection:
        """Query and serialize land-cover / agricultural / forest features."""
        cls._validate_bbox(min_lat, max_lat, min_lon, max_lon)
        all_features = cls._get_context_features()

        # 1. Non-industrial (land cover / agriculture / vegetation / urban) filter
        features = [
            f for f in all_features if f.context_type not in INDUSTRIAL_CONTEXT_TYPES
        ]

        # 2. Specific context_type filter
        if context_type is not None:
            target = context_type.lower()
            features = [f for f in features if f.context_type.value.lower() == target]

        # 3. Spatial bounding box filter
        if min_lat is not None:
            features = [f for f in features if f.geometry.latitude >= min_lat]
        if max_lat is not None:
            features = [f for f in features if f.geometry.latitude <= max_lat]
        if min_lon is not None:
            features = [f for f in features if f.geometry.longitude >= min_lon]
        if max_lon is not None:
            features = [f for f in features if f.geometry.longitude <= max_lon]

        # 4. Pagination
        paged_features = features[offset : offset + limit]

        # 5. Serialize to GeoJSON Features via canonical serializer
        raw_features = [
            serialize_context_feature_to_geojson(feat) for feat in paged_features
        ]

        bbox: list[float] | None = None
        if raw_features:
            lons = [f["geometry"]["coordinates"][0] for f in raw_features]
            lats = [f["geometry"]["coordinates"][1] for f in raw_features]
            bbox = [min(lons), min(lats), max(lons), max(lats)]

        fc_dict = to_geojson_feature_collection(raw_features, bbox=bbox)
        return GeoJsonFeatureCollection(
            type="FeatureCollection",
            features=[GeoJsonFeature.model_validate(f) for f in fc_dict["features"]],
            bbox=fc_dict.get("bbox"),
        )

    @classmethod
    def get_detections_layer(
        cls,
        min_lat: float | None = None,
        max_lat: float | None = None,
        min_lon: float | None = None,
        max_lon: float | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        source: str | None = None,
        satellite: str | None = None,
        instrument: str | None = None,
        min_frp_mw: float | None = None,
        geometry_type: str = "point",
        limit: int = 100,
        offset: int = 0,
    ) -> GeoJsonFeatureCollection:
        """Query and serialize canonical detections into a GeoJSON FeatureCollection."""
        cls._validate_bbox(min_lat, max_lat, min_lon, max_lon)
        detections = list(DetectionQueryService.get_canonical_detections())

        # 1. Spatial bounding box filter
        if min_lat is not None:
            detections = [d for d in detections if d.geometry.latitude >= min_lat]
        if max_lat is not None:
            detections = [d for d in detections if d.geometry.latitude <= max_lat]
        if min_lon is not None:
            detections = [d for d in detections if d.geometry.longitude >= min_lon]
        if max_lon is not None:
            detections = [d for d in detections if d.geometry.longitude <= max_lon]

        # 2. Temporal filter
        if start_time is not None:
            detections = [d for d in detections if d.acquired_at >= start_time]
        if end_time is not None:
            detections = [d for d in detections if d.acquired_at <= end_time]

        # 3. Satellite / Instrument / Source filter
        if satellite is not None:
            sat_query = satellite.strip().lower()
            detections = [
                d for d in detections if d.satellite.strip().lower() == sat_query
            ]
        if instrument is not None:
            inst_query = instrument.strip().lower()
            detections = [
                d for d in detections if d.instrument.strip().lower() == inst_query
            ]
        if source is not None:
            src_query = source.strip().lower()
            detections = [
                d
                for d in detections
                if src_query in d.source.lower()
                or src_query in d.product_type.lower()
            ]

        # 4. FRP filter
        if min_frp_mw is not None:
            detections = [
                d
                for d in detections
                if d.frp_mw is not None and d.frp_mw >= min_frp_mw
            ]

        # 5. Deterministic sorting & pagination
        detections.sort(key=lambda d: (d.acquired_at, d.detection_id))
        paged_detections = detections[offset : offset + limit]

        # 6. Serialize to GeoJSON Features via canonical serializer
        raw_features = [
            serialize_detection_to_geojson(
                det,
                geometry_type=geometry_type,
            )
            for det in paged_detections
        ]

        # 7. Compute layer bounding box
        bbox: list[float] | None = None
        if raw_features:
            all_lons: list[float] = []
            all_lats: list[float] = []
            for f in raw_features:
                geom = f["geometry"]
                if geom["type"] == "Point":
                    all_lons.append(geom["coordinates"][0])
                    all_lats.append(geom["coordinates"][1])
                elif geom["type"] == "Polygon" and geom["coordinates"]:
                    for pt in geom["coordinates"][0]:
                        all_lons.append(pt[0])
                        all_lats.append(pt[1])
            if all_lons and all_lats:
                bbox = [min(all_lons), min(all_lats), max(all_lons), max(all_lats)]

        fc_dict = to_geojson_feature_collection(raw_features, bbox=bbox)
        return GeoJsonFeatureCollection(
            type="FeatureCollection",
            features=[GeoJsonFeature.model_validate(f) for f in fc_dict["features"]],
            bbox=fc_dict.get("bbox"),
        )
