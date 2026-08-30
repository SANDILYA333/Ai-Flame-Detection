"""Builder and aggregation functions for persistent thermal source derivation."""

import hashlib
from collections.abc import Sequence

from packages.config.scientific import ScientificConfig
from packages.geospatial.envelope import (
    calculate_bounding_box,
    calculate_spatial_centroid,
    points_to_coordinate,
)
from packages.schemas.event import Event
from packages.schemas.source import PersistentSource
from packages.sources.classification import (
    calculate_active_calendar_days,
    calculate_observation_span_days,
    calculate_recurrence_ratio,
    classify_persistence_state,
)


def generate_deterministic_source_id(
    event_ids: Sequence[str],
    config_fingerprint: str,
) -> str:
    """Generate a deterministic, content-addressable source identifier.

    The source ID is derived from the SHA-256 digest of the scientific configuration
    fingerprint and the sorted set of member event IDs. Given identical
    events and configuration, the ID is invariant.

    Args:
        event_ids: Sequence of associated thermal event IDs.
        config_fingerprint: SHA-256 fingerprint of the scientific configuration.

    Returns:
        str: Canonical persistent source identifier.
    """
    sorted_ids = sorted(e.strip() for e in event_ids if e and e.strip())
    raw_key = f"{config_fingerprint}:src:" + ",".join(sorted_ids)
    digest = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    return f"src_{digest[:24]}"


def build_persistent_source_from_events(
    cluster: Sequence[Event],
    config: ScientificConfig,
    persistence_run_id: str | None = None,
    notes: str | None = None,
) -> PersistentSource:
    """Construct a canonical PersistentSource domain model from associated events.

    Calculates longitudinal spatial centroid, bounding box, active calendar days,
    temporal span, recurrence ratio, and classified persistence state.

    Args:
        cluster: Non-empty sequence of member canonical Event objects.
        config: Authoritative ScientificConfig governing persistence derivation.
        persistence_run_id: Optional pipeline execution run identifier.
        notes: Optional operational or scientific notes.

    Returns:
        PersistentSource: Canonical validated PersistentSource domain model.

    Raises:
        ValueError: If cluster is empty.
    """
    if not cluster:
        raise ValueError(
            "Cannot construct a PersistentSource from an empty event cluster."
        )

    # Guaranteed non-null after validate_completeness()
    persistence_threshold_d = config.persistence_threshold_days
    persistence_min_obs = config.persistence_min_observations
    assert persistence_threshold_d is not None
    assert persistence_min_obs is not None

    # Sort member event IDs deterministically
    linked_event_ids = sorted(e.event_id for e in cluster)
    total_event_count = len(linked_event_ids)

    # 1. Temporal extent & active calendar days
    first_seen_at = min(e.started_at for e in cluster)
    last_seen_at = max(e.ended_at for e in cluster)
    all_timestamps = [e.started_at for e in cluster] + [e.ended_at for e in cluster]
    active_days_count = calculate_active_calendar_days(all_timestamps)
    obs_span_days = calculate_observation_span_days(first_seen_at, last_seen_at)
    recurrence_ratio = calculate_recurrence_ratio(
        active_days_count, first_seen_at, last_seen_at
    )

    # 2. Spatial extent & representative centroid
    points = [
        (e.centroid_geometry.latitude, e.centroid_geometry.longitude) for e in cluster
    ]
    centroid_lat, centroid_lon = calculate_spatial_centroid(points)
    centroid_geom = points_to_coordinate(centroid_lat, centroid_lon)
    bounding_box = calculate_bounding_box(points)

    # 3. Persistence classification
    persistence_state = classify_persistence_state(
        total_event_count=total_event_count,
        active_days_count=active_days_count,
        observation_span_days=obs_span_days,
        persistence_threshold_days=persistence_threshold_d,
        persistence_min_observations=persistence_min_obs,
    )

    # 4. Deterministic source ID & configuration lineage
    config_fingerprint = config.compute_fingerprint()
    source_id = generate_deterministic_source_id(linked_event_ids, config_fingerprint)

    return PersistentSource(
        source_id=source_id,
        linked_event_ids=linked_event_ids,
        total_event_count=total_event_count,
        centroid_geometry=centroid_geom,
        first_seen_at=first_seen_at,
        last_seen_at=last_seen_at,
        active_days_count=active_days_count,
        persistence_state=persistence_state,
        persistence_configuration_id=config.name,
        persistence_configuration_version=config.version,
        bounding_box=bounding_box,
        persistence_run_id=persistence_run_id,
        recurrence_ratio=recurrence_ratio,
        notes=notes,
    )
