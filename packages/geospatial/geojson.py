"""Canonical GeoJSON (RFC 7946) serializer and spatial foundation (GIS-001).

Guarantees:
1. Coordinate reference system is strictly WGS-84 (EPSG:4326).
2. Coordinate order is strictly [longitude, latitude].
3. Precision is deterministic and finite (default 6 decimal places ~0.1m precision).
4. Missing geometries are handled honestly; no silent (0, 0) default substitution.
5. Direct serialization adapters for domain entities (Event, Detection, Source, etc.).
"""

from typing import Any

from packages.context.models import ContextFeature
from packages.geospatial.coordinates import validate_wgs84_coordinates
from packages.schemas.common import BoundingBox, Coordinate
from packages.schemas.detection import Detection
from packages.schemas.event import Event
from packages.schemas.source import PersistentSource


def to_geojson_point(
    coordinate: Coordinate,
    precision: int = 6,
) -> dict[str, Any]:
    """Serialize Coordinate to canonical RFC 7946 GeoJSON Point geometry.

    Args:
        coordinate: Validated Coordinate domain model in EPSG:4326.
        precision: Decimal places to round coordinate values (default 6).

    Returns:
        dict[str, Any]: GeoJSON Point geometry dictionary.
    """
    lat, lon = validate_wgs84_coordinates(coordinate.latitude, coordinate.longitude)
    return {
        "type": "Point",
        "coordinates": [round(lon, precision), round(lat, precision)],
    }


def to_geojson_bbox_polygon(
    bbox: BoundingBox,
    precision: int = 6,
) -> dict[str, Any]:
    """Serialize BoundingBox to canonical RFC 7946 GeoJSON closed Polygon geometry.

    Notice: Polygon rings follow right-hand rule (counter-clockwise exterior ring).

    Args:
        bbox: Validated BoundingBox model in EPSG:4326.
        precision: Decimal places for rounding coordinates.

    Returns:
        dict[str, Any]: GeoJSON Polygon geometry dictionary.
    """
    min_lat, min_lon = validate_wgs84_coordinates(bbox.min_latitude, bbox.min_longitude)
    max_lat, max_lon = validate_wgs84_coordinates(bbox.max_latitude, bbox.max_longitude)

    p_min_lon = round(min_lon, precision)
    p_min_lat = round(min_lat, precision)
    p_max_lon = round(max_lon, precision)
    p_max_lat = round(max_lat, precision)

    # Closed exterior linear ring: SW -> SE -> NE -> NW -> SW
    coordinates = [
        [
            [p_min_lon, p_min_lat],
            [p_max_lon, p_min_lat],
            [p_max_lon, p_max_lat],
            [p_min_lon, p_max_lat],
            [p_min_lon, p_min_lat],
        ]
    ]

    return {
        "type": "Polygon",
        "coordinates": coordinates,
    }


def to_geojson_feature(
    geometry: dict[str, Any],
    properties: dict[str, Any],
    feature_id: str | None = None,
) -> dict[str, Any]:
    """Serialize geometry and properties into a canonical RFC 7946 GeoJSON Feature.

    Args:
        geometry: Valid GeoJSON geometry object.
        properties: Feature attributes dictionary.
        feature_id: Optional unique canonical identifier.

    Returns:
        dict[str, Any]: GeoJSON Feature dictionary.
    """
    feat: dict[str, Any] = {
        "type": "Feature",
        "geometry": geometry,
        "properties": properties,
    }
    if feature_id is not None:
        feat["id"] = feature_id
    return feat


def to_geojson_feature_collection(
    features: list[dict[str, Any]],
    bbox: list[float] | None = None,
) -> dict[str, Any]:
    """Serialize list of GeoJSON features into a canonical FeatureCollection.

    Args:
        features: List of GeoJSON Feature dictionaries.
        bbox: Optional layer bounding box [min_lon, min_lat, max_lon, max_lat].

    Returns:
        dict[str, Any]: GeoJSON FeatureCollection dictionary.
    """
    fc: dict[str, Any] = {
        "type": "FeatureCollection",
        "features": features,
    }
    if bbox is not None:
        fc["bbox"] = bbox
    return fc


def serialize_event_to_geojson(
    event: Event,
    precision: int = 6,
    geometry_type: str = "point",
    classification_state: str | None = None,
    persistence_state: str | None = None,
) -> dict[str, Any]:
    """Serialize canonical Event domain model to GeoJSON Feature.

    Args:
        event: Validated Event domain object.
        precision: Decimal places for coordinates.
        geometry_type: 'point' for centroid, 'envelope' for bbox Polygon.
        classification_state: Optional adjudicated classification.
        persistence_state: Optional observed persistence state.

    Returns:
        dict[str, Any]: GeoJSON Feature.
    """
    if (
        geometry_type.lower() in ("envelope", "polygon")
        and event.bounding_box is not None
    ):
        geometry = to_geojson_bbox_polygon(event.bounding_box, precision=precision)
    else:
        geometry = to_geojson_point(event.centroid_geometry, precision=precision)

    props: dict[str, Any] = {
        "event_id": event.event_id,
        "started_at": event.started_at.isoformat(),
        "ended_at": event.ended_at.isoformat(),
        "detection_count": event.detection_count,
        "mean_frp_mw": event.mean_frp_mw,
        "max_frp_mw": event.max_frp_mw,
        "duration_seconds": event.duration_seconds,
        "classification_state": classification_state,
        "persistence_state": persistence_state,
    }
    if event.bounding_box is not None:
        props["bbox"] = [
            round(event.bounding_box.min_longitude, precision),
            round(event.bounding_box.min_latitude, precision),
            round(event.bounding_box.max_longitude, precision),
            round(event.bounding_box.max_latitude, precision),
        ]
    return to_geojson_feature(
        geometry=geometry,
        properties=props,
        feature_id=event.event_id,
    )


def compute_pixel_footprint_polygon(
    lat: float,
    lon: float,
    scan_km: float | None = None,
    track_km: float | None = None,
    precision: int = 6,
) -> dict[str, Any]:
    """Compute sensor pixel footprint polygon without overclaiming precision.

    Uses along-track and along-scan dimensions (defaulting to nominal VIIRS 375m
    resolution if unspecified) to calculate geodesic bounding footprint.
    """
    import math

    effective_track = track_km if track_km is not None and track_km > 0 else 0.375
    effective_scan = scan_km if scan_km is not None and scan_km > 0 else 0.375

    # 1 deg latitude ≈ 111.32 km
    delta_lat = (effective_track / 111.32) / 2.0

    # 1 deg longitude ≈ 111.32 * cos(lat) km
    lat_rad = math.radians(lat)
    cos_lat = max(math.cos(lat_rad), 0.001)
    delta_lon = (effective_scan / (111.32 * cos_lat)) / 2.0

    min_lat = max(round(lat - delta_lat, precision), -90.0)
    max_lat = min(round(lat + delta_lat, precision), 90.0)
    min_lon = max(round(lon - delta_lon, precision), -180.0)
    max_lon = min(round(lon + delta_lon, precision), 180.0)

    # Closed exterior linear ring: SW -> SE -> NE -> NW -> SW
    coordinates = [
        [
            [min_lon, min_lat],
            [max_lon, min_lat],
            [max_lon, max_lat],
            [min_lon, max_lat],
            [min_lon, min_lat],
        ]
    ]
    return {
        "type": "Polygon",
        "coordinates": coordinates,
    }


def serialize_detection_to_geojson(
    detection: Detection,
    precision: int = 6,
    geometry_type: str = "point",
) -> dict[str, Any]:
    """Serialize Detection domain model to GeoJSON Feature.

    Args:
        detection: Validated raw detection domain object.
        precision: Decimal places for coordinates.
        geometry_type: 'point' for centroid, 'footprint' for pixel envelope Polygon.

    Returns:
        dict[str, Any]: GeoJSON Feature.
    """
    lat, lon = validate_wgs84_coordinates(
        detection.geometry.latitude, detection.geometry.longitude
    )
    if geometry_type.lower() in ("footprint", "pixel", "polygon"):
        geometry = compute_pixel_footprint_polygon(
            lat=lat,
            lon=lon,
            scan_km=detection.scan_km,
            track_km=detection.track_km,
            precision=precision,
        )
    else:
        geometry = to_geojson_point(detection.geometry, precision=precision)

    props: dict[str, Any] = {
        "detection_id": detection.detection_id,
        "source": detection.source,
        "satellite": detection.satellite,
        "instrument": detection.instrument,
        "product_type": detection.product_type,
        "product_version": detection.product_version,
        "acquired_at": detection.acquired_at.isoformat(),
        "brightness_ti4_k": detection.brightness_ti4_k,
        "brightness_ti5_k": detection.brightness_ti5_k,
        "frp_mw": detection.frp_mw,
        "confidence": detection.confidence,
        "day_night": detection.day_night.value if detection.day_night else None,
        "scan_km": detection.scan_km,
        "track_km": detection.track_km,
        "precision_note": (
            "Observational pixel centroid / footprint; not ground truth."
        ),
    }
    return to_geojson_feature(
        geometry=geometry,
        properties=props,
        feature_id=detection.detection_id,
    )


def serialize_persistent_source_to_geojson(
    source: PersistentSource,
    precision: int = 6,
) -> dict[str, Any]:
    """Serialize PersistentSource domain model to GeoJSON Feature.

    Args:
        source: Validated PersistentSource domain object.
        precision: Decimal places for coordinates.

    Returns:
        dict[str, Any]: GeoJSON Feature.
    """
    geometry = to_geojson_point(source.centroid_geometry, precision=precision)
    props: dict[str, Any] = {
        "source_id": source.source_id,
        "persistence_state": source.persistence_state.value,
        "total_event_count": source.total_event_count,
        "active_days_count": source.active_days_count,
        "recurrence_ratio": source.recurrence_ratio,
        "first_seen_at": source.first_seen_at.isoformat(),
        "last_seen_at": source.last_seen_at.isoformat(),
        "linked_event_ids": source.linked_event_ids,
    }
    if source.bounding_box is not None:
        props["bbox"] = [
            round(source.bounding_box.min_longitude, precision),
            round(source.bounding_box.min_latitude, precision),
            round(source.bounding_box.max_longitude, precision),
            round(source.bounding_box.max_latitude, precision),
        ]
    return to_geojson_feature(
        geometry=geometry,
        properties=props,
        feature_id=source.source_id,
    )


def serialize_context_feature_to_geojson(
    feature: ContextFeature,
    precision: int = 6,
) -> dict[str, Any]:
    """Serialize ContextFeature domain model to GeoJSON Feature.

    Args:
        feature: Validated ContextFeature domain object.
        precision: Decimal places for coordinates.

    Returns:
        dict[str, Any]: GeoJSON Feature.
    """
    geometry = to_geojson_point(feature.geometry, precision=precision)
    props: dict[str, Any] = {
        "feature_id": feature.feature_id,
        "facility_name": feature.facility_name,
        "context_type": feature.context_type.value,
        "provider": feature.provider,
        "dataset_name": feature.dataset_name,
        "dataset_version": feature.dataset_version,
        "raw_metadata": feature.raw_metadata or {},
    }
    if feature.bounding_box is not None:
        props["bbox"] = [
            round(feature.bounding_box.min_longitude, precision),
            round(feature.bounding_box.min_latitude, precision),
            round(feature.bounding_box.max_longitude, precision),
            round(feature.bounding_box.max_latitude, precision),
        ]
    return to_geojson_feature(
        geometry=geometry,
        properties=props,
        feature_id=feature.feature_id,
    )
