"""Geospatial distance calculations from Points to Polygons and MultiPolygons.

Provides authoritative geodesic distance computation (in kilometers) from a query
coordinate to the actual boundaries of Polygon and MultiPolygon forest areas.
"""

from typing import Any

from shapely.geometry import MultiPolygon, Point, Polygon, shape
from shapely.ops import nearest_points

from packages.geospatial.coordinates import validate_wgs84_coordinates
from packages.geospatial.distance import haversine_distance_meters
from packages.schemas.common import Coordinate
from packages.schemas.forest import ForestGeometry


def calculate_point_to_polygon_distance_km(
    latitude: float,
    longitude: float,
    geometry: ForestGeometry | dict[str, Any] | Polygon | MultiPolygon,
) -> tuple[float, Coordinate | None]:
    """Calculate shortest geodesic distance in km from a point to a polygon.

    Invariants:
    1. If the query point lies inside or directly on the boundary of the polygon,
       the distance is exactly 0.0 km.
    2. If the query point is outside, the distance is the great-circle Haversine
       distance between the query point and the nearest point on the polygon boundary.
    3. MultiPolygon geometries calculate the minimum distance across all constituent
       polygons.

    Args:
        latitude: Query point latitude in degrees [-90.0, 90.0].
        longitude: Query point longitude in degrees [-180.0, 180.0].
        geometry: Shapely Polygon/MultiPolygon, GeoJSON dictionary, or ForestGeometry.

    Returns:
        tuple[float, Coordinate | None]:
            - distance_km: Geodesic distance in km (0.0 if inside or on boundary).
            - nearest_point: Closest boundary Coordinate (or query point if inside).
    """
    lat, lon = validate_wgs84_coordinates(latitude, longitude)
    query_pt = Point(lon, lat)  # Note: Shapely uses (x=lon, y=lat)

    if isinstance(geometry, (Polygon, MultiPolygon)):
        shapely_geom = geometry
    elif isinstance(geometry, ForestGeometry):
        shapely_geom = shape(geometry.model_dump())
    elif isinstance(geometry, dict):
        shapely_geom = shape(geometry)
    else:
        raise ValueError(
            f"Unsupported geometry type for distance calculation: {type(geometry)}"
        )

    if shapely_geom.is_empty:
        return float("inf"), None

    # 1. Fire inside or touching the forest boundary -> distance = 0.0 km
    if (
        shapely_geom.contains(query_pt)
        or shapely_geom.touches(query_pt)
        or shapely_geom.intersects(query_pt)
    ):
        return 0.0, Coordinate(latitude=lat, longitude=lon)

    # 2. Fire outside the forest -> find closest point on geometry perimeter
    nearest_geom_pt, _ = nearest_points(shapely_geom, query_pt)
    nearest_lon = float(nearest_geom_pt.x)
    nearest_lat = float(nearest_geom_pt.y)

    # 3. Calculate geodesic Haversine distance in meters, convert to km
    dist_meters = haversine_distance_meters(lat, lon, nearest_lat, nearest_lon)
    dist_km = round(dist_meters / 1000.0, 4)

    return dist_km, Coordinate(latitude=nearest_lat, longitude=nearest_lon)
