"""Shared geospatial utilities, distance metrics, and coordinate operations."""

from packages.geospatial.coordinates import (
    format_wkt_point,
    parse_wkt_point,
    validate_wgs84_coordinates,
)
from packages.geospatial.distance import (
    WGS84_MEAN_EARTH_RADIUS_METERS,
    haversine_distance_meters,
    is_spatiotemporally_proximate,
)
from packages.geospatial.envelope import (
    calculate_bounding_box,
    calculate_spatial_centroid,
    points_to_coordinate,
)
from packages.geospatial.geojson import (
    compute_pixel_footprint_polygon,
    serialize_context_feature_to_geojson,
    serialize_detection_to_geojson,
    serialize_event_to_geojson,
    serialize_persistent_source_to_geojson,
    to_geojson_bbox_polygon,
    to_geojson_feature,
    to_geojson_feature_collection,
    to_geojson_point,
)

__all__ = [
    "WGS84_MEAN_EARTH_RADIUS_METERS",
    "calculate_bounding_box",
    "calculate_spatial_centroid",
    "compute_pixel_footprint_polygon",
    "format_wkt_point",
    "haversine_distance_meters",
    "is_spatiotemporally_proximate",
    "parse_wkt_point",
    "points_to_coordinate",
    "serialize_context_feature_to_geojson",
    "serialize_detection_to_geojson",
    "serialize_event_to_geojson",
    "serialize_persistent_source_to_geojson",
    "to_geojson_bbox_polygon",
    "to_geojson_feature",
    "to_geojson_feature_collection",
    "to_geojson_point",
    "validate_wgs84_coordinates",
]
