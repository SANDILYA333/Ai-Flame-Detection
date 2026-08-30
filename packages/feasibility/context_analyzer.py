"""Contextual infrastructure and land-cover availability feasibility analyzer."""

from collections import Counter
from collections.abc import Sequence

from packages.config.scientific import ScientificConfig
from packages.context.matching import evaluate_spatial_association
from packages.context.models import ContextFeature, SpatialMatchRule
from packages.feasibility.models import ContextFeasibilityMetrics
from packages.schemas.common import BoundingBox
from packages.schemas.event import Event


def filter_context_features_in_bounds(
    features: Sequence[ContextFeature],
    bounds: BoundingBox,
) -> list[ContextFeature]:
    """Filter contextual infrastructure features within bounding box."""
    return [
        f
        for f in features
        if (
            bounds.min_latitude <= f.geometry.latitude <= bounds.max_latitude
            and bounds.min_longitude <= f.geometry.longitude <= bounds.max_longitude
        )
    ]


def analyze_context_feasibility(
    events: Sequence[Event],
    context_features: Sequence[ContextFeature],
    bounds: BoundingBox,
    config: ScientificConfig,
) -> ContextFeasibilityMetrics:
    """Analyze the density and spatial proximity coverage of contextual infrastructure.

    Measures what proportion of derived thermal events have nearby contextual
    evidence (e.g. refineries, power stations, industrial parks, agricultural land).

    Args:
        events: Derived thermal events within the candidate region.
        context_features: External contextual features available for analysis.
        bounds: Geographic boundary of the study area.
        config: Authoritative ScientificConfig instance.

    Returns:
        ContextFeasibilityMetrics: Contextual availability and coverage metrics.
    """
    filtered_features = filter_context_features_in_bounds(context_features, bounds)

    if not filtered_features:
        return ContextFeasibilityMetrics(
            total_context_features=0,
            context_by_category={},
            events_with_context_count=0,
            context_coverage_ratio=0.0,
        )

    categories = Counter(f.context_type.value for f in filtered_features)

    radius_m = config.attribution_radius_meters
    assert radius_m is not None

    events_with_context = 0
    for event in events:
        matched = any(
            evaluate_spatial_association(
                target_coord=event.centroid_geometry,
                feature=feat,
                max_radius_meters=radius_m,
                rule=SpatialMatchRule.PROXIMITY_RADIUS,
            )[0]
            for feat in filtered_features
        )
        if matched:
            events_with_context += 1

    coverage_ratio = float(events_with_context) / float(len(events)) if events else 0.0

    return ContextFeasibilityMetrics(
        total_context_features=len(filtered_features),
        context_by_category=dict(categories),
        events_with_context_count=events_with_context,
        context_coverage_ratio=round(coverage_ratio, 4),
    )
