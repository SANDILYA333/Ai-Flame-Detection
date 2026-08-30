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
