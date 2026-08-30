"""Geospatial distance and spatiotemporal proximity calculations.

Calculates physically accurate geodesic distances over the WGS84 sphere/ellipsoid
in SI meters, eliminating Euclidean degree distortion where 1 deg lat != 1 deg lon.
"""

import math
from datetime import datetime

from packages.geospatial.coordinates import validate_wgs84_coordinates

# IUGG recommended mean Earth radius in meters (R1)
WGS84_MEAN_EARTH_RADIUS_METERS: float = 6371008.8


def haversine_distance_meters(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Calculate the great-circle distance between two points on Earth in meters.

    Uses the Haversine formula with numerical clamping for precision and stability.

    Args:
        lat1: Latitude of point 1 in degrees [-90.0, 90.0].
        lon1: Longitude of point 1 in degrees [-180.0, 180.0].
        lat2: Latitude of point 2 in degrees [-90.0, 90.0].
        lon2: Longitude of point 2 in degrees [-180.0, 180.0].

    Returns:
        float: Geodesic distance in meters (non-negative).
    """
    lat1_v, lon1_v = validate_wgs84_coordinates(lat1, lon1)
    lat2_v, lon2_v = validate_wgs84_coordinates(lat2, lon2)

    # Identical coordinates short-circuit
    if lat1_v == lat2_v and lon1_v == lon2_v:
        return 0.0

    phi1 = math.radians(lat1_v)
    phi2 = math.radians(lat2_v)
    delta_phi = math.radians(lat2_v - lat1_v)
    delta_lambda = math.radians(lon2_v - lon1_v)

    sin_half_dphi = math.sin(delta_phi / 2.0)
    sin_half_dlambda = math.sin(delta_lambda / 2.0)

    a = (sin_half_dphi * sin_half_dphi) + (
        math.cos(phi1) * math.cos(phi2) * sin_half_dlambda * sin_half_dlambda
    )

    # Clamp to [0.0, 1.0] to guard against floating-point rounding errors near antipodes
    a_clamped = min(1.0, max(0.0, a))
    c = 2.0 * math.atan2(math.sqrt(a_clamped), math.sqrt(1.0 - a_clamped))

    return WGS84_MEAN_EARTH_RADIUS_METERS * c


def is_spatiotemporally_proximate(
    lat1: float,
    lon1: float,
    t1: datetime,
    lat2: float,
    lon2: float,
    t2: datetime,
    max_distance_meters: float,
    max_time_difference_hours: float,
) -> bool:
    """Evaluate whether two observations are proximate in both space and time.

    Args:
        lat1: Latitude of observation 1.
        lon1: Longitude of observation 1.
        t1: Timestamp of observation 1.
        lat2: Latitude of observation 2.
        lon2: Longitude of observation 2.
        t2: Timestamp of observation 2.
        max_distance_meters: Maximum spatial radius in meters.
        max_time_difference_hours: Maximum temporal delta in hours.

    Returns:
        bool: True if spatial distance <= radius AND time delta <= window.
    """
    if max_distance_meters < 0:
        raise ValueError(
            f"max_distance_meters must be non-negative, got {max_distance_meters}"
        )
    if max_time_difference_hours < 0:
        msg = (
            f"max_time_difference_hours must be non-negative, "
            f"got {max_time_difference_hours}"
        )
        raise ValueError(msg)

    # Check temporal threshold first (fast scalar comparison)
    time_diff_seconds = abs((t2 - t1).total_seconds())
    max_time_seconds = max_time_difference_hours * 3600.0
    if time_diff_seconds > max_time_seconds:
        return False

    # Check spatial threshold using geodesic distance
    distance_meters = haversine_distance_meters(lat1, lon1, lat2, lon2)
    return distance_meters <= max_distance_meters
