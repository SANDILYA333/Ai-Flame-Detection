"""Spatiotemporal clustering algorithm for canonical thermal detections.

Clusters discrete satellite observations into coherent thermal event episodes
using deterministic spatiotemporal graph connected components with geodesic
metric distances.
"""

from collections import defaultdict, deque
from collections.abc import Sequence

from packages.geospatial.distance import haversine_distance_meters
from packages.schemas.detection import Detection


def cluster_detections_spatiotemporal(
    detections: Sequence[Detection],
    spatial_radius_meters: float,
    temporal_window_hours: float,
) -> list[list[Detection]]:
    """Group canonical detections into spatiotemporal clusters.

    Two detections are adjacent (belong to the same episode) if:
    1. Geodesic distance (Haversine) <= spatial_radius_meters
    2. Absolute acquisition time delta <= temporal_window_hours

    Transitive connectivity merges chains of proximate observations into
    a single coherent thermal event cluster.

    DETERMINISM GUARANTEE:
    Input detections are deterministically sorted by:
    (acquired_at, latitude, longitude, detection_id)
    prior to clustering, ensuring invariant cluster formation and ordering
    regardless of input collection order.

    Args:
        detections: Sequence of canonical Detection domain objects.
        spatial_radius_meters: Maximum geodesic clustering radius in meters.
        temporal_window_hours: Maximum temporal delta in hours.

    Returns:
        list[list[Detection]]: List of deterministic detection clusters.
    """
    if not detections:
        return []

    if spatial_radius_meters < 0:
        raise ValueError(
            f"spatial_radius_meters must be non-negative, got {spatial_radius_meters}"
        )
    if temporal_window_hours < 0:
        raise ValueError(
            f"temporal_window_hours must be non-negative, got {temporal_window_hours}"
        )

    # 1. Deduplicate detections by detection_id to prevent redundant nodes
    unique_dets: dict[str, Detection] = {}
    for d in detections:
        if d.detection_id not in unique_dets:
            unique_dets[d.detection_id] = d

    if not unique_dets:
        return []

    # 2. Deterministic canonical sorting of all input detections
    sorted_detections = sorted(
        unique_dets.values(),
        key=lambda d: (
            d.acquired_at.timestamp(),
            d.geometry.latitude,
            d.geometry.longitude,
            d.detection_id,
        ),
    )

    n = len(sorted_detections)
    if n == 1:
        return [[sorted_detections[0]]]

    temporal_window_seconds = temporal_window_hours * 3600.0

    # 2. Build adjacency graph
    # Because detections are sorted by time, we can prune pairwise comparisons
    # once temporal delta exceeds the window.
    adj: dict[int, list[int]] = defaultdict(list)

    for i in range(n):
        det_i = sorted_detections[i]
        t_i = det_i.acquired_at.timestamp()
        lat_i = det_i.geometry.latitude
        lon_i = det_i.geometry.longitude

        for j in range(i + 1, n):
            det_j = sorted_detections[j]
            t_j = det_j.acquired_at.timestamp()

            # Temporal pruning: future j will also exceed window
            if (t_j - t_i) > temporal_window_seconds:
                break

            lat_j = det_j.geometry.latitude
            lon_j = det_j.geometry.longitude

            dist_meters = haversine_distance_meters(lat_i, lon_i, lat_j, lon_j)
            if dist_meters <= spatial_radius_meters:
                adj[i].append(j)
                adj[j].append(i)

    # 3. Find connected components using Breadth-First Search (BFS)
    visited: set[int] = set()
    clusters: list[list[Detection]] = []

    for i in range(n):
        if i in visited:
            continue

        component_indices: list[int] = []
        queue: deque[int] = deque([i])
        visited.add(i)

        while queue:
            curr = queue.popleft()
            component_indices.append(curr)

            # Sort neighbor exploration for strict determinism
            for neighbor in sorted(adj[curr]):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        # Build cluster and preserve deterministic order
        cluster_detections = [
            sorted_detections[idx] for idx in sorted(component_indices)
        ]
        clusters.append(cluster_detections)

    # 4. Sort clusters deterministically
    clusters.sort(
        key=lambda c: (
            c[0].acquired_at.timestamp(),
            c[0].geometry.latitude,
            c[0].geometry.longitude,
            c[0].detection_id,
        )
    )

    return clusters
