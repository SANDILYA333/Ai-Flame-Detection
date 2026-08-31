"""Event builder and aggregation functions for thermal event derivation."""

import hashlib
from collections.abc import Sequence

from packages.config.scientific import ScientificConfig
from packages.geospatial.envelope import (
    calculate_bounding_box,
    calculate_spatial_centroid,
    points_to_coordinate,
)
from packages.schemas.detection import Detection
from packages.schemas.event import Event


def generate_deterministic_event_id(
    detection_ids: Sequence[str],
    config_fingerprint: str,
) -> str:
    """Generate a deterministic, content-addressable event identifier.

    The event ID is computed from the SHA-256 digest of the scientific configuration
    fingerprint and the sorted set of member detection IDs. Given identical
    detections and configuration, the ID is invariant.

    Args:
        detection_ids: Sequence of member detection IDs.
        config_fingerprint: SHA-256 fingerprint of the scientific configuration.

    Returns:
        str: Canonical event identifier (e.g. 'evt_a1b2c3d4e5f60718293a4b5c').
    """
    sorted_ids = sorted(d.strip() for d in detection_ids if d and d.strip())
    raw_key = f"{config_fingerprint}:" + ",".join(sorted_ids)
    digest = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    return f"evt_{digest[:24]}"


def build_event_from_cluster(
    cluster: Sequence[Detection],
    config: ScientificConfig,
    formation_run_id: str | None = None,
    notes: str | None = None,
) -> Event:
    """Construct a canonical Event domain model from a cluster of detections.

    Calculates spatiotemporal boundaries, observational centroid, bounding box,
    FRP aggregations, and provenance linkage to member detection IDs and
    the scientific configuration contract.

    Args:
        cluster: Non-empty sequence of member canonical Detection objects.
        config: Authoritative ScientificConfig governing event formation.
        formation_run_id: Optional pipeline execution run identifier.
        notes: Optional operational or scientific notes.

    Returns:
        Event: Canonical validated Event domain model.

    Raises:
        ValueError: If cluster is empty.
    """
    # Deduplicate member detections by detection_id
    unique_members: dict[str, Detection] = {}
    for d in cluster:
        if d.detection_id not in unique_members:
            unique_members[d.detection_id] = d
    unique_cluster = list(unique_members.values())

    if not unique_cluster:
        raise ValueError("Cannot construct an Event from an empty cluster.")

    # Sort member detection IDs deterministically
    detection_ids = sorted(unique_members.keys())
    detection_count = len(detection_ids)

    # 1. Temporal extent
    timestamps = [d.acquired_at for d in unique_cluster]
    started_at = min(timestamps)
    ended_at = max(timestamps)
    duration_seconds = (ended_at - started_at).total_seconds()

    # 2. Spatial extent & centroid
    points = [(d.geometry.latitude, d.geometry.longitude) for d in unique_cluster]
    centroid_lat, centroid_lon = calculate_spatial_centroid(points)
    centroid_geom = points_to_coordinate(centroid_lat, centroid_lon)
    bounding_box = calculate_bounding_box(points)

    # 3. Physical FRP aggregations (instantaneous statistics)
    frp_values = [d.frp_mw for d in unique_cluster if d.frp_mw is not None]
    mean_frp_mw: float | None = None
    max_frp_mw: float | None = None
    if frp_values:
        mean_frp_mw = sum(frp_values) / float(len(frp_values))
        max_frp_mw = max(frp_values)

    # 4. Deterministic event ID & configuration lineage
    config_fingerprint = config.compute_fingerprint()
    event_id = generate_deterministic_event_id(detection_ids, config_fingerprint)

    return Event(
        event_id=event_id,
        detection_ids=detection_ids,
        detection_count=detection_count,
        started_at=started_at,
        ended_at=ended_at,
        centroid_geometry=centroid_geom,
        formation_configuration_id=config.name,
        formation_configuration_version=config.version,
        bounding_box=bounding_box,
        formation_run_id=formation_run_id,
        duration_seconds=duration_seconds,
        mean_frp_mw=mean_frp_mw,
        max_frp_mw=max_frp_mw,
        notes=notes,
    )
