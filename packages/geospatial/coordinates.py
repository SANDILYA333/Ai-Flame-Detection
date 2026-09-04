"""Geospatial coordinate validation and WKT formatting utilities.

Enforces EPSG:4326 canonical conventions:
- Geographic coordinates: Latitude in [-90.0, 90.0], Longitude in [-180.0, 180.0].
- WKT representation: POINT(longitude latitude) according to OGC and PostGIS standards.
"""

import math
import re

from packages.errors import InvalidCoordinateError

_POINT_WKT_REGEX = re.compile(
    r"^POINT\s*\(\s*([+-]?\d+(?:\.\d+)?)\s+([+-]?\d+(?:\.\d+)?)\s*\)$",
    re.IGNORECASE,
)


def validate_wgs84_coordinates(
    latitude: float, longitude: float
) -> tuple[float, float]:
    """Validate latitude and longitude against WGS-84 (EPSG:4326) bounds.

    Args:
        latitude: Latitude in decimal degrees [-90.0, 90.0].
        longitude: Longitude in decimal degrees [-180.0, 180.0].

    Returns:
        tuple[float, float]: Validated (latitude, longitude).

    Raises:
        InvalidCoordinateError: If coordinates are non-finite or outside bounds.
    """
    if not math.isfinite(latitude) or not math.isfinite(longitude):
        msg = (
            f"Coordinates must be finite numbers, got latitude={latitude}, "
            f"longitude={longitude}"
        )
        raise InvalidCoordinateError(
            msg,
            details={"latitude": latitude, "longitude": longitude},
        )

    if not (-90.0 <= latitude <= 90.0):
        raise InvalidCoordinateError(
            f"Latitude must be between -90.0 and 90.0 degrees, got {latitude}",
            details={"latitude": latitude, "longitude": longitude},
        )

    if not (-180.0 <= longitude <= 180.0):
        raise InvalidCoordinateError(
            f"Longitude must be between -180.0 and 180.0 degrees, got {longitude}",
            details={"latitude": latitude, "longitude": longitude},
        )

    return float(latitude), float(longitude)


def format_wkt_point(latitude: float, longitude: float) -> str:
    """Format latitude and longitude into canonical WKT POINT(longitude latitude).

    Notice: OGC WKT standard specifies X (longitude) followed by Y (latitude).

    Args:
        latitude: Latitude in decimal degrees [-90.0, 90.0].
        longitude: Longitude in decimal degrees [-180.0, 180.0].

    Returns:
        str: WKT representation e.g. "POINT(77.209 28.6139)".
    """
    lat, lon = validate_wgs84_coordinates(latitude, longitude)
    # Format with clean representation avoiding trailing zeros if not present
    return f"POINT({lon:g} {lat:g})"


def parse_wkt_point(wkt: str) -> tuple[float, float]:
    """Parse WKT string into (latitude, longitude) tuple.

    Args:
        wkt: WKT string e.g. "POINT(77.209 28.6139)".

    Returns:
        tuple[float, float]: (latitude, longitude).

    Raises:
        InvalidCoordinateError: If WKT is malformed or coordinates are out of bounds.
    """
    match = _POINT_WKT_REGEX.match(wkt.strip())
    if not match:
        raise InvalidCoordinateError(
            f"Malformed Point WKT: '{wkt}'. Expected format: 'POINT(lon lat)'",
            details={"wkt": wkt},
        )

    lon_str, lat_str = match.groups()
    try:
        lon = float(lon_str)
        lat = float(lat_str)
    except ValueError as exc:
        raise InvalidCoordinateError(
            f"Could not parse numeric coordinates from WKT: '{wkt}'",
            details={"wkt": wkt},
        ) from exc

    return validate_wgs84_coordinates(lat, lon)


def project_coordinate(
    latitude: float,
    longitude: float,
    distance_km: float,
    bearing_deg: float,
    earth_radius_km: float = 6371.0,
) -> tuple[float, float]:
    """Project a starting geographic point along a geodesic bearing and distance.

    Args:
        latitude: Origin latitude in decimal degrees [-90.0, 90.0].
        longitude: Origin longitude in decimal degrees [-180.0, 180.0].
        distance_km: Distance to travel in kilometers (>= 0).
        bearing_deg: Travel bearing measured clockwise from true north (0-360°).
        earth_radius_km: Mean spherical Earth radius in km (default 6371.0).

    Returns:
        tuple[float, float]: Destination (latitude, longitude) rounded to 6 decimals.
    """
    lat, lon = validate_wgs84_coordinates(latitude, longitude)
    if not math.isfinite(distance_km) or distance_km < 0:
        raise ValueError(f"Distance must be a finite non-negative number, got {distance_km}")

    if distance_km == 0.0:
        return lat, lon

    rad_lat = math.radians(lat)
    rad_lon = math.radians(lon)
    rad_bearing = math.radians(bearing_deg % 360.0)
    ang_dist = distance_km / earth_radius_km

    lat2 = math.asin(
        math.sin(rad_lat) * math.cos(ang_dist)
        + math.cos(rad_lat) * math.sin(ang_dist) * math.cos(rad_bearing)
    )
    lon2 = rad_lon + math.atan2(
        math.sin(rad_bearing) * math.sin(ang_dist) * math.cos(rad_lat),
        math.cos(ang_dist) - math.sin(rad_lat) * math.sin(lat2),
    )

    deg_lat2 = math.degrees(lat2)
    deg_lon2 = (math.degrees(lon2) + 540.0) % 360.0 - 180.0

    return round(deg_lat2, 6), round(deg_lon2, 6)


def calculate_geodesic_bearing(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Calculate the initial forward geodesic bearing from point 1 to point 2 in degrees (0-360°).

    Args:
        lat1: Origin latitude in decimal degrees [-90.0, 90.0].
        lon1: Origin longitude in decimal degrees [-180.0, 180.0].
        lat2: Target latitude in decimal degrees [-90.0, 90.0].
        lon2: Target longitude in decimal degrees [-180.0, 180.0].

    Returns:
        float: Initial bearing in degrees clockwise from true north [0.0, 360.0).
    """
    v_lat1, v_lon1 = validate_wgs84_coordinates(lat1, lon1)
    v_lat2, v_lon2 = validate_wgs84_coordinates(lat2, lon2)

    if math.isclose(v_lat1, v_lat2, abs_tol=1e-7) and math.isclose(v_lon1, v_lon2, abs_tol=1e-7):
        return 0.0

    phi1 = math.radians(v_lat1)
    phi2 = math.radians(v_lat2)
    delta_lambda = math.radians(v_lon2 - v_lon1)

    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)

    bearing_rad = math.atan2(y, x)
    bearing_deg = (math.degrees(bearing_rad) + 360.0) % 360.0

    return round(bearing_deg, 2)

