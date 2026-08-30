"""Candidate reference and ground-truth evidence feasibility analyzer."""

from collections import Counter
from collections.abc import Sequence

from pydantic import Field

from packages.config.scientific import ScientificConfig
from packages.feasibility.models import ReferenceFeasibilityMetrics
from packages.geospatial.distance import haversine_distance_meters
from packages.schemas.common import BaseDomainModel, BoundingBox, Coordinate
from packages.schemas.event import Event


class CandidateReferencePoint(BaseDomainModel):
    """Candidate ground reference record from external reference databases."""

    point_id: str = Field(..., min_length=1)
    source_name: str = Field(
        ...,
        min_length=1,
        description="Originating reference catalog (e.g. 'GGIT_FLARING', 'GEM_POWER').",
    )
    tier: str = Field(
        ...,
        description="Evidence tier level ('TIER_A', 'TIER_B', 'TIER_C').",
    )
    geometry: Coordinate
    facility_name: str | None = None


def filter_reference_points_in_bounds(
    points: Sequence[CandidateReferencePoint],
    bounds: BoundingBox,
) -> list[CandidateReferencePoint]:
    """Filter reference points located within geographic bounding box."""
    return [
        p
        for p in points
        if (
            bounds.min_latitude <= p.geometry.latitude <= bounds.max_latitude
            and bounds.min_longitude <= p.geometry.longitude <= bounds.max_longitude
        )
    ]


def analyze_reference_feasibility(
    events: Sequence[Event],
    reference_points: Sequence[CandidateReferencePoint],
    bounds: BoundingBox,
    config: ScientificConfig,
) -> ReferenceFeasibilityMetrics:
    """Analyze availability and coverage of candidate reference ground-truth.

    CRITICAL SCIENTIFIC INTEGRITY INVARIANT:
    Candidate reference points are evaluated as reference feasibility indicators,
    NOT finalized benchmark ground-truth labels.

    Args:
        events: Derived thermal events within the candidate region.
        reference_points: Candidate reference facilities or known emission points.
        bounds: Geographic boundary of the study area.
        config: Authoritative ScientificConfig instance.

    Returns:
        ReferenceFeasibilityMetrics: Quantitative reference feasibility metrics.
    """
    filtered_points = filter_reference_points_in_bounds(reference_points, bounds)

    if not filtered_points:
        return ReferenceFeasibilityMetrics(
            candidate_reference_points=0,
            reference_by_source={},
            reference_by_tier={},
            events_with_reference_count=0,
            reference_coverage_ratio=0.0,
        )

    sources = Counter(p.source_name for p in filtered_points)
    tiers = Counter(p.tier for p in filtered_points)

    radius_m = config.attribution_radius_meters
    assert radius_m is not None

    events_with_ref = 0
    for event in events:
        matched = any(
            haversine_distance_meters(
                event.centroid_geometry.latitude,
                event.centroid_geometry.longitude,
                p.geometry.latitude,
                p.geometry.longitude,
            )
            <= radius_m
            for p in filtered_points
        )
        if matched:
            events_with_ref += 1

    coverage_ratio = float(events_with_ref) / float(len(events)) if events else 0.0

    return ReferenceFeasibilityMetrics(
        candidate_reference_points=len(filtered_points),
        reference_by_source=dict(sources),
        reference_by_tier=dict(tiers),
        events_with_reference_count=events_with_ref,
        reference_coverage_ratio=round(coverage_ratio, 4),
    )
