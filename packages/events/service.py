"""High-level thermal event derivation service.

Coordinates configuration validation, filtering, spatiotemporal clustering,
and canonical Event domain object synthesis.
"""

import logging
from collections.abc import Sequence

from packages.config.scientific import ScientificConfig
from packages.events.builder import build_event_from_cluster
from packages.events.clustering import cluster_detections_spatiotemporal
from packages.schemas.detection import Detection
from packages.schemas.event import Event

logger = logging.getLogger(__name__)


def derive_thermal_events(
    detections: Sequence[Detection],
    config: ScientificConfig,
    formation_run_id: str | None = None,
) -> list[Event]:
    """Derive canonical Thermal Events from input remote-sensing detections.

    CRITICAL SCIENTIFIC INTEGRITY INVARIANTS:
    1. The ScientificConfig MUST be complete and calibrated before execution;
       incomplete configurations will explicitly raise MissingConfigurationError.
    2. Spatial distance is computed in geodesic meters, not planar degrees.
    3. Output events are 100% deterministic and content-addressable.

    Args:
        detections: Sequence of canonical Detection domain models.
        config: Authoritative ScientificConfig instance.
        formation_run_id: Optional pipeline run identifier for lineage.

    Returns:
        list[Event]: List of derived canonical Thermal Events.

    Raises:
        MissingConfigurationError: If any required scientific parameter is unset (None).
    """
    # 1. Authoritative configuration completeness check
    config.validate_completeness()

    # Guaranteed non-null after validate_completeness()
    spatial_radius_m = config.spatial_cluster_radius_meters
    temporal_window_h = config.temporal_window_hours
    assert spatial_radius_m is not None
    assert temporal_window_h is not None

    if not detections:
        logger.debug(
            "Zero detections provided to derive_thermal_events; returning empty list."
        )
        return []

    # 2. Spatiotemporal clustering
    clusters = cluster_detections_spatiotemporal(
        detections=detections,
        spatial_radius_meters=spatial_radius_m,
        temporal_window_hours=temporal_window_h,
    )

    # 3. Build canonical Event objects
    events: list[Event] = [
        build_event_from_cluster(
            cluster=cluster,
            config=config,
            formation_run_id=formation_run_id,
        )
        for cluster in clusters
    ]

    logger.info(
        "Derived %d events from %d detections (config: %s, fp: %s)",
        len(events),
        len(detections),
        config.version,
        config.compute_fingerprint()[:8],
    )

    return events
