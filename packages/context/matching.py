"""Spatial and temporal matching rules for contextual evidence association."""

from datetime import datetime

from packages.context.models import ContextFeature, SpatialMatchRule
from packages.geospatial.distance import haversine_distance_meters
from packages.schemas.common import Coordinate


def evaluate_spatial_association(
    target_coord: Coordinate,
    feature: ContextFeature,
    max_radius_meters: float,
    rule: SpatialMatchRule = SpatialMatchRule.PROXIMITY_RADIUS,
) -> tuple[bool, float]:
    """Evaluate whether an external feature is spatially associated with a target.

    Uses geodesic Haversine metric distance in meters.

    Args:
        target_coord: Target observation/centroid coordinate.
        feature: Normalized external contextual feature.
        max_radius_meters: Maximum geodesic search distance in meters.
        rule: Spatial matching strategy.

    Returns:
        tuple[bool, float]: (is_spatially_associated, distance_in_meters).
    """
    if max_radius_meters < 0:
        raise ValueError(
            f"max_radius_meters must be non-negative, got {max_radius_meters}"
        )

    dist_meters = haversine_distance_meters(
        target_coord.latitude,
        target_coord.longitude,
        feature.geometry.latitude,
        feature.geometry.longitude,
    )

    if rule == SpatialMatchRule.PROXIMITY_RADIUS:
        return dist_meters <= max_radius_meters, dist_meters

    if (
        rule == SpatialMatchRule.CONTAINMENT_ENVELOPE
        and feature.bounding_box is not None
    ):
        bbox = feature.bounding_box
        is_inside_bbox = (
            bbox.min_latitude <= target_coord.latitude <= bbox.max_latitude
            and bbox.min_longitude <= target_coord.longitude <= bbox.max_longitude
        )
        if is_inside_bbox:
            return True, dist_meters
        return dist_meters <= max_radius_meters, dist_meters

    # Default fallback to proximity
    return dist_meters <= max_radius_meters, dist_meters


def evaluate_temporal_validity(
    target_time: datetime,
    feature: ContextFeature,
) -> bool:
    """Evaluate if external feature is temporally valid for target observation.

    CRITICAL INTEGRITY INVARIANT (NO HINDSIGHT LEAKAGE):
    A facility or boundary commissioned after the target observation timestamp
    or decommissioned prior to it is not temporally valid.

    Args:
        target_time: UTC timestamp of the thermal event or observation.
        feature: Normalized external contextual feature.

    Returns:
        bool: True if feature is valid at target_time, False otherwise.
    """
    if feature.valid_from is not None and target_time < feature.valid_from:
        return False
    return not (feature.valid_to is not None and target_time > feature.valid_to)
