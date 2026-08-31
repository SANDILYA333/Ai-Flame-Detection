"""Tests for GIS-001 (GeoJSON Serializer & Spatial API Foundation)."""

from datetime import UTC, datetime

import pytest

from packages.context.models import ContextFeature
from packages.errors import InvalidCoordinateError
from packages.geospatial.geojson import (
    serialize_context_feature_to_geojson,
    serialize_detection_to_geojson,
    serialize_event_to_geojson,
    serialize_persistent_source_to_geojson,
    to_geojson_bbox_polygon,
    to_geojson_feature,
    to_geojson_feature_collection,
    to_geojson_point,
)
from packages.schemas.common import BoundingBox, Coordinate
from packages.schemas.detection import Detection
from packages.schemas.enums import ContextType, DayNight, PersistenceState
from packages.schemas.event import Event
from packages.schemas.source import PersistentSource


def test_gis_001_to_geojson_point_coordinate_order_and_precision() -> None:
    """GIS-001: Verify point coordinate ordering is strictly [lon, lat]."""
    coord = Coordinate(latitude=22.45021234, longitude=70.05125678)
    geom = to_geojson_point(coord, precision=4)

    assert geom["type"] == "Point"
    # RFC 7946: [lon, lat]
    lon, lat = geom["coordinates"]
    assert lon == 70.0513
    assert lat == 22.4502


def test_gis_001_to_geojson_point_invalid_coordinates_raise_error() -> None:
    """GIS-001: Verify invalid coordinates raise error without substitution."""
    with pytest.raises(InvalidCoordinateError):
        # Lat > 90
        to_geojson_point(Coordinate.model_construct(latitude=95.0, longitude=70.0))

    with pytest.raises(InvalidCoordinateError):
        # Lon > 180
        to_geojson_point(Coordinate.model_construct(latitude=20.0, longitude=190.0))


def test_gis_001_to_geojson_bbox_polygon_structure() -> None:
    """GIS-001: Verify BoundingBox produces a closed RFC 7946 Polygon linear ring."""
    bbox = BoundingBox(
        min_latitude=22.4300,
        max_latitude=22.4700,
        min_longitude=70.0300,
        max_longitude=70.0700,
    )
    geom = to_geojson_bbox_polygon(bbox, precision=4)

    assert geom["type"] == "Polygon"
    coords = geom["coordinates"]
    assert len(coords) == 1  # 1 exterior ring
    ring = coords[0]
    assert len(ring) == 5  # 5 positions (closed ring)

    # First and last coordinate must be identical
    assert ring[0] == ring[4]
    # Coordinates must be [lon, lat]
    assert ring[0] == [70.03, 22.43]
    assert ring[1] == [70.07, 22.43]
    assert ring[2] == [70.07, 22.47]
    assert ring[3] == [70.03, 22.47]
    assert ring[4] == [70.03, 22.43]


def test_gis_001_to_geojson_feature_and_collection() -> None:
    """GIS-001: Verify Feature and FeatureCollection assembly."""
    geom = {"type": "Point", "coordinates": [70.05, 22.45]}
    props = {"name": "Test Feature", "value": 42}
    feat = to_geojson_feature(geom, props, feature_id="feat_001")

    assert feat["type"] == "Feature"
    assert feat["id"] == "feat_001"
    assert feat["geometry"] == geom
    assert feat["properties"] == props

    fc = to_geojson_feature_collection([feat], bbox=[70.0, 22.0, 71.0, 23.0])
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) == 1
    assert fc["bbox"] == [70.0, 22.0, 71.0, 23.0]


def test_gis_001_serialize_event_to_geojson() -> None:
    """GIS-001: Verify domain Event model serialization."""
    now = datetime.now(UTC)
    event = Event(
        event_id="evt_test_101",
        detection_ids=["det_1", "det_2"],
        detection_count=2,
        started_at=now,
        ended_at=now,
        centroid_geometry=Coordinate(latitude=22.45, longitude=70.05),
        formation_configuration_id="cfg_001",
        formation_configuration_version="v1.0",
        mean_frp_mw=45.2,
        max_frp_mw=60.1,
        duration_seconds=120.0,
    )
    feat = serialize_event_to_geojson(event)

    assert feat["type"] == "Feature"
    assert feat["id"] == "evt_test_101"
    assert feat["geometry"]["type"] == "Point"
    assert feat["geometry"]["coordinates"] == [70.05, 22.45]
    assert feat["properties"]["event_id"] == "evt_test_101"
    assert feat["properties"]["detection_count"] == 2
    assert feat["properties"]["mean_frp_mw"] == 45.2


def test_gis_001_serialize_detection_to_geojson() -> None:
    """GIS-001: Verify domain Detection model serialization."""
    now = datetime.now(UTC)
    det = Detection(
        detection_id="det_firms_001",
        source="firms",
        source_snapshot_id="snap_firms_001",
        satellite="NOAA-20",
        instrument="VIIRS",
        product_type="nrt",
        product_version="v1.0",
        raw_hash="a" * 64,
        geometry=Coordinate(latitude=22.451, longitude=70.052),
        acquired_at=now,
        brightness_ti4_k=350.5,
        brightness_ti5_k=295.2,
        frp_mw=12.4,
        confidence="95",
        day_night=DayNight.NIGHT,
    )
    feat = serialize_detection_to_geojson(det)

    assert feat["type"] == "Feature"
    assert feat["id"] == "det_firms_001"
    assert feat["geometry"]["type"] == "Point"
    assert feat["geometry"]["coordinates"] == [70.052, 22.451]
    assert feat["properties"]["satellite"] == "NOAA-20"
    assert feat["properties"]["frp_mw"] == 12.4


def test_gis_001_serialize_persistent_source_to_geojson() -> None:
    """GIS-001: Verify domain PersistentSource model serialization."""
    now = datetime.now(UTC)
    source = PersistentSource(
        source_id="src_persistent_001",
        linked_event_ids=["evt_001", "evt_002"],
        total_event_count=2,
        centroid_geometry=Coordinate(latitude=22.45, longitude=70.05),
        first_seen_at=now,
        last_seen_at=now,
        active_days_count=5,
        persistence_state=PersistenceState.PERSISTENT,
        persistence_configuration_id="p_cfg_001",
        persistence_configuration_version="v1.0",
        recurrence_ratio=0.85,
    )
    feat = serialize_persistent_source_to_geojson(source)

    assert feat["type"] == "Feature"
    assert feat["id"] == "src_persistent_001"
    assert feat["geometry"]["type"] == "Point"
    assert feat["geometry"]["coordinates"] == [70.05, 22.45]
    assert feat["properties"]["persistence_state"] == "persistent"
    assert feat["properties"]["total_event_count"] == 2


def test_gis_001_serialize_context_feature_to_geojson() -> None:
    """GIS-001: Verify domain ContextFeature model serialization."""
    feat_domain = ContextFeature(
        feature_id="osm_refinery_01",
        provider="osm",
        dataset_name="planet_osm_polygon",
        dataset_version="2026-08-01",
        context_type=ContextType.OIL_GAS,
        geometry=Coordinate(latitude=22.4506, longitude=70.0516),
        facility_name="Jamnagar Flare Stack Array",
    )
    feat = serialize_context_feature_to_geojson(feat_domain)

    assert feat["type"] == "Feature"
    assert feat["id"] == "osm_refinery_01"
    assert feat["geometry"]["type"] == "Point"
    assert feat["geometry"]["coordinates"] == [70.0516, 22.4506]
    assert feat["properties"]["context_type"] == "oil_gas"
    assert feat["properties"]["facility_name"] == "Jamnagar Flare Stack Array"
