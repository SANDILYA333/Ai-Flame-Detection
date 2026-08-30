"""Spatial tracking and event association algorithm for persistent thermal sources."""

from collections import defaultdict, deque
from collections.abc import Sequence

from packages.geospatial.distance import haversine_distance_meters
from packages.schemas.event import Event


def group_events_into_sources(
    events: Sequence[Event],
    spatial_radius_meters: float,
) -> list[list[Event]]:
    """Group independent Thermal Events into spatial source clusters.

    Associates thermal events that occur within spatial_radius_meters geodesic
    distance of each other over longitudinal time.

    DETERMINISM GUARANTEE:
    Input events are deterministically sorted by:
    (started_at, centroid_latitude, centroid_longitude, event_id)
    prior to graph construction, guaranteeing invariant source formation
    regardless of input collection ordering.

    Args:
        events: Sequence of canonical Event domain objects.
        spatial_radius_meters: Maximum geodesic distance in meters between centroids.

    Returns:
        list[list[Event]]: List of event clusters, each sorted deterministically.
    """
    if not events:
        return []

    if spatial_radius_meters < 0:
        raise ValueError(
            f"spatial_radius_meters must be non-negative, got {spatial_radius_meters}"
        )

    # 1. Deterministic canonical sorting of all input events
    sorted_events = sorted(
        events,
        key=lambda e: (
            e.started_at.timestamp(),
            e.centroid_geometry.latitude,
            e.centroid_geometry.longitude,
            e.event_id,
        ),
    )

    n = len(sorted_events)
    if n == 1:
        return [[sorted_events[0]]]

    # 2. Build spatial adjacency graph
    adj: dict[int, list[int]] = defaultdict(list)

    for i in range(n):
        ev_i = sorted_events[i]
        lat_i = ev_i.centroid_geometry.latitude
        lon_i = ev_i.centroid_geometry.longitude

        for j in range(i + 1, n):
            ev_j = sorted_events[j]
            lat_j = ev_j.centroid_geometry.latitude
            lon_j = ev_j.centroid_geometry.longitude

            dist_meters = haversine_distance_meters(lat_i, lon_i, lat_j, lon_j)
            if dist_meters <= spatial_radius_meters:
                adj[i].append(j)
                adj[j].append(i)

    # 3. Find connected components using Breadth-First Search (BFS)
    visited: set[int] = set()
    clusters: list[list[Event]] = []

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

        # Build cluster with deterministic element ordering
        cluster_events = [sorted_events[idx] for idx in sorted(component_indices)]
        clusters.append(cluster_events)

    # 4. Sort clusters deterministically
    clusters.sort(
        key=lambda c: (
            c[0].started_at.timestamp(),
            c[0].centroid_geometry.latitude,
            c[0].centroid_geometry.longitude,
            c[0].event_id,
        )
    )

    return clusters
