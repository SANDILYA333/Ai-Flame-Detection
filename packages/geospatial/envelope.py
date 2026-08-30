"""Spatial aggregation, centroid computation, and bounding envelope utilities."""

import math
from collections.abc import Sequence

from packages.geospatial.coordinates import validate_wgs84_coordinates
from packages.schemas.common import BoundingBox, Coordinate


def calculate_spatial_centroid(
    points: Sequence[tuple[float, float]],
) -> tuple[float, float]:
    """Calculate representative geographic centroid from a collection of coordinates.

    Uses 3D Cartesian spherical coordinate averaging to avoid distortion near
    extreme latitudes or coordinate singularities.

    Args:
        points: Non-empty sequence of (latitude, longitude) tuples.

    Returns:
        tuple[float, float]: (centroid_latitude, centroid_longitude).

    Raises:
        ValueError: If points sequence is empty.
    """
    if not points:
        raise ValueError("Cannot calculate spatial centroid of an empty sequence.")

    if len(points) == 1:
        lat, lon = points[0]
        return validate_wgs84_coordinates(lat, lon)

    sum_x = 0.0
    sum_y = 0.0
    sum_z = 0.0

    for lat, lon in points:
        lat_v, lon_v = validate_wgs84_coordinates(lat, lon)
        phi = math.radians(lat_v)
        lam = math.radians(lon_v)

        sum_x += math.cos(phi) * math.cos(lam)
        sum_y += math.cos(phi) * math.sin(lam)
        sum_z += math.sin(phi)

    n = float(len(points))
    avg_x = sum_x / n
    avg_y = sum_y / n
    avg_z = sum_z / n

    # Longitude from atan2(y, x)
    lon_rad = math.atan2(avg_y, avg_x)
    hyp = math.sqrt(avg_x * avg_x + avg_y * avg_y)
    lat_rad = math.atan2(avg_z, hyp)

    centroid_lat = math.degrees(lat_rad)
    centroid_lon = math.degrees(lon_rad)

    return validate_wgs84_coordinates(centroid_lat, centroid_lon)


def calculate_bounding_box(points: Sequence[tuple[float, float]]) -> BoundingBox:
    """Calculate geographic minimum bounding box encompassing all points.

    Args:
        points: Non-empty sequence of (latitude, longitude) tuples.

    Returns:
        BoundingBox: Enclosing spatial envelope.

    Raises:
        ValueError: If points sequence is empty.
    """
    if not points:
        raise ValueError("Cannot calculate bounding box of an empty sequence.")

    first_lat, first_lon = validate_wgs84_coordinates(points[0][0], points[0][1])
    min_lat = first_lat
    max_lat = first_lat
    min_lon = first_lon
    max_lon = first_lon

    for lat, lon in points[1:]:
        lat_v, lon_v = validate_wgs84_coordinates(lat, lon)
        if lat_v < min_lat:
            min_lat = lat_v
        if lat_v > max_lat:
            max_lat = lat_v
        if lon_v < min_lon:
            min_lon = lon_v
        if lon_v > max_lon:
            max_lon = lon_v

    return BoundingBox(
        min_latitude=min_lat,
        max_latitude=max_lat,
        min_longitude=min_lon,
        max_longitude=max_lon,
    )


def points_to_coordinate(lat: float, lon: float) -> Coordinate:
    """Helper to construct a validated Coordinate schema model."""
    lat_v, lon_v = validate_wgs84_coordinates(lat, lon)
    return Coordinate(latitude=lat_v, longitude=lon_v)
