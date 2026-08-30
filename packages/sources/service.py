"""High-level persistent thermal source derivation service.

Coordinates configuration validation, spatial event association, persistence
state classification, and canonical PersistentSource domain object synthesis.
"""

import logging
from collections.abc import Sequence

from packages.config.scientific import ScientificConfig
from packages.schemas.event import Event
from packages.schemas.source import PersistentSource
from packages.sources.builder import build_persistent_source_from_events
from packages.sources.tracking import group_events_into_sources

logger = logging.getLogger(__name__)


def derive_persistent_sources(
    events: Sequence[Event],
    config: ScientificConfig,
    persistence_run_id: str | None = None,
) -> list[PersistentSource]:
    """Derive canonical Persistent Thermal Sources from input thermal events.

    CRITICAL SCIENTIFIC INTEGRITY INVARIANTS:
    1. The ScientificConfig MUST be complete and calibrated before execution;
       incomplete configurations will explicitly raise MissingConfigurationError.
    2. Spatial association is evaluated using geodesic metric distances in meters.
    3. Output sources are 100% deterministic and content-addressable.
    4. Persistence is an observed temporal characteristic, NOT an attribution.

    Args:
        events: Sequence of canonical Event domain models.
        config: Authoritative ScientificConfig instance.
        persistence_run_id: Optional pipeline run identifier for lineage.

    Returns:
        list[PersistentSource]: List of derived canonical Persistent Thermal Sources.

    Raises:
        MissingConfigurationError: If any required parameter is unset (None).
    """
    # 1. Authoritative configuration completeness check
    config.validate_completeness()

    spatial_radius_m = config.spatial_cluster_radius_meters
    assert spatial_radius_m is not None

    if not events:
        logger.debug(
            "Zero events provided to derive_persistent_sources; returning empty list."
        )
        return []

    # 2. Spatial event association
    clusters = group_events_into_sources(
        events=events,
        spatial_radius_meters=spatial_radius_m,
    )

    # 3. Build canonical PersistentSource domain objects
    sources: list[PersistentSource] = [
        build_persistent_source_from_events(
            cluster=cluster,
            config=config,
            persistence_run_id=persistence_run_id,
        )
        for cluster in clusters
    ]

    logger.info(
        "Derived %d persistent sources from %d events (config: %s, fp: %s)",
        len(sources),
        len(events),
        config.version,
        config.compute_fingerprint()[:8],
    )

    return sources
