"""Quantitative NASA FIRMS thermal anomaly observation data feasibility analyzer."""

from collections import Counter
from collections.abc import Sequence

from packages.feasibility.models import FirmsFeasibilityMetrics
from packages.schemas.common import BoundingBox
from packages.schemas.detection import Detection


def filter_detections_in_bounds(
    detections: Sequence[Detection],
    bounds: BoundingBox,
) -> list[Detection]:
    """Filter detections strictly located within the geographic bounding envelope."""
    return [
        d
        for d in detections
        if (
            bounds.min_latitude <= d.geometry.latitude <= bounds.max_latitude
            and bounds.min_longitude <= d.geometry.longitude <= bounds.max_longitude
        )
    ]


def analyze_firms_feasibility(
    detections: Sequence[Detection],
    bounds: BoundingBox,
    approx_area_sqkm: float,
) -> FirmsFeasibilityMetrics:
    """Analyze the observational volume, temporal continuity, and sensor coverage.

    Args:
        detections: Candidate detection records.
        bounds: Geographic boundary of the study area.
        approx_area_sqkm: Approximate regional surface area in sq km.

    Returns:
        FirmsFeasibilityMetrics: Quantitative observational metrics.
    """
    filtered = filter_detections_in_bounds(detections, bounds)

    if not filtered:
        return FirmsFeasibilityMetrics(
            total_detections=0,
            unique_observation_dates=0,
            temporal_span_days=0.0,
            sensor_breakdown={},
            day_night_breakdown={},
            frp_mean_mw=None,
            frp_max_mw=None,
            missing_frp_count=0,
            spatial_density_per_sqkm=0.0,
        )

    # 1. Temporal metrics
    timestamps = [d.acquired_at for d in filtered]
    min_time = min(timestamps)
    max_time = max(timestamps)
    temporal_span_days = max(0.0, (max_time - min_time).total_seconds() / 86400.0)
    unique_dates = len({t.date() for t in timestamps})

    # 2. Sensor and platform breakdown
    sensors = Counter(f"{d.satellite}_{d.instrument}" for d in filtered)
    day_night = Counter(
        d.day_night.value if d.day_night is not None else "unknown" for d in filtered
    )

    # 3. FRP measurements
    frp_values = [d.frp_mw for d in filtered if d.frp_mw is not None]
    missing_frp_count = len(filtered) - len(frp_values)
    frp_mean_mw = round(sum(frp_values) / len(frp_values), 2) if frp_values else None
    frp_max_mw = round(max(frp_values), 2) if frp_values else None

    # 4. Spatial density
    spatial_density = round(len(filtered) / approx_area_sqkm, 4)

    return FirmsFeasibilityMetrics(
        total_detections=len(filtered),
        unique_observation_dates=unique_dates,
        temporal_span_days=round(temporal_span_days, 2),
        sensor_breakdown=dict(sensors),
        day_night_breakdown=dict(day_night),
        frp_mean_mw=frp_mean_mw,
        frp_max_mw=frp_max_mw,
        missing_frp_count=missing_frp_count,
        spatial_density_per_sqkm=spatial_density,
    )
