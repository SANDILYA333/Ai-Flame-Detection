"""Deterministic duplicate detection and co-location analysis for industrial assets."""

import math
import re
from collections import defaultdict
from collections.abc import Sequence

from packages.schemas.industrial_asset import DuplicateCandidate, IndustrialAsset


def haversine_distance_meters(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Calculate geodesic distance between points in meters via Haversine."""
    r_earth = 6371000.0  # Mean radius of Earth in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r_earth * c


def _tokenize_name(name: str) -> set[str]:
    """Tokenize and stem facility name for lexical overlap comparison."""
    # Filter out generic industrial stop words
    stop_words = {
        "power",
        "plant",
        "station",
        "facility",
        "complex",
        "ltd",
        "limited",
        "private",
        "pvt",
        "india",
        "gt",
        "ccpp",
        "ccgt",
        "tps",
        "thermal",
        "solar",
        "wind",
        "hydro",
        "unit",
        "project",
        "gas",
        "oil",
    }
    tokens = re.findall(r"[a-zA-Z0-9]+", name.lower())
    meaningful = {t for t in tokens if t not in stop_words and len(t) > 2}
    return meaningful if meaningful else set(tokens)


def compute_name_similarity(name1: str, name2: str) -> float:
    """Compute Jaccard similarity over distinctive lexical tokens in facility names."""
    tokens1 = _tokenize_name(name1)
    tokens2 = _tokenize_name(name2)

    if not tokens1 or not tokens2:
        return 0.0

    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    return len(intersection) / len(union)


def find_duplicate_candidates(
    assets: Sequence[IndustrialAsset],
    max_distance_meters: float = 1000.0,
) -> list[DuplicateCandidate]:
    """Detect potential duplicate or co-located industrial facilities.

    Uses spatial grid bucketing (~0.01 degree cells ≈ 1.1km) for efficient retrieval.

    Args:
        assets: Sequence of normalized IndustrialAsset instances.
        max_distance_meters: Maximum spatial proximity threshold in meters.

    Returns:
        list[DuplicateCandidate]: Deterministically sorted list of duplicate candidates.
    """
    grid_size = 0.015  # ~1.6 km grid cells
    buckets: dict[tuple[int, int], list[IndustrialAsset]] = defaultdict(list)

    for asset in assets:
        if not asset.is_map_eligible:
            continue
        cell_x = math.floor(asset.longitude / grid_size)
        cell_y = math.floor(asset.latitude / grid_size)
        buckets[(cell_x, cell_y)].append(asset)

    candidates: list[DuplicateCandidate] = []
    seen_pairs: set[tuple[str, str]] = set()

    for (cx, cy), cell_assets in buckets.items():
        # Check current cell and adjacent 8 neighbor cells
        neighbor_assets: list[IndustrialAsset] = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                neighbor_assets.extend(buckets.get((cx + dx, cy + dy), []))

        for a1 in cell_assets:
            for a2 in neighbor_assets:
                if a1.id >= a2.id:
                    continue  # Ensure unique pair evaluation (a1.id < a2.id)

                pair_key = (a1.id, a2.id)
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                dist = haversine_distance_meters(
                    a1.latitude, a1.longitude, a2.latitude, a2.longitude
                )

                if dist <= max_distance_meters:
                    reasons: list[str] = []
                    score = 0.0

                    # 1. Spatial proximity scoring
                    if dist <= 10.0:
                        reasons.append("Exact or near-identical coordinates (<= 10m)")
                        score += 0.50
                    elif dist <= 100.0:
                        reasons.append(f"Immediate co-location ({dist:.1f}m)")
                        score += 0.35
                    elif dist <= 500.0:
                        reasons.append(f"Close industrial proximity ({dist:.1f}m)")
                        score += 0.20
                    else:
                        reasons.append(f"Area co-location ({dist:.1f}m)")
                        score += 0.10

                    # 2. Name similarity
                    name_sim = compute_name_similarity(a1.name, a2.name)
                    if name_sim >= 0.80:
                        reasons.append(f"High name similarity ({name_sim:.2f})")
                        score += 0.40
                    elif name_sim >= 0.40:
                        reasons.append(
                            f"Shared distinctive name token ({name_sim:.2f})"
                        )
                        score += 0.25

                    # 3. Cross-provider registry match (e.g. WRI vs GEM)
                    if a1.source != a2.source and a1.industry == a2.industry:
                        reasons.append(
                            f"Cross-provider registry co-location "
                            f"({a1.source} vs {a2.source})"
                        )
                        score += 0.15

                    # 4. Capacity alignment
                    if (
                        a1.capacity is not None
                        and a2.capacity is not None
                        and a1.capacity > 0
                        and a2.capacity > 0
                    ):
                        ratio = min(a1.capacity, a2.capacity) / max(
                            a1.capacity, a2.capacity
                        )
                        if ratio >= 0.95:
                            reasons.append("Identical generation capacity")
                            score += 0.20
                        elif ratio >= 0.80:
                            reasons.append("Similar generation capacity")
                            score += 0.10

                    confidence = min(round(score, 2), 1.0)
                    if confidence >= 0.40:
                        candidates.append(
                            DuplicateCandidate(
                                primary_asset_id=a1.id,
                                candidate_asset_id=a2.id,
                                distance_meters=round(dist, 2),
                                match_reasons=reasons,
                                confidence=confidence,
                            )
                        )

    # Deterministic sorting
    candidates.sort(
        key=lambda c: (
            -c.confidence,
            c.distance_meters,
            c.primary_asset_id,
            c.candidate_asset_id,
        )
    )
    return candidates


def link_duplicate_records(
    assets: list[IndustrialAsset],
    candidates: list[DuplicateCandidate],
    link_threshold: float = 0.70,
) -> list[IndustrialAsset]:
    """Non-destructively link high-confidence duplicate source IDs.

    Args:
        assets: Input list of IndustrialAsset models.
        candidates: Detected duplicate candidates.
        link_threshold: Minimum confidence required to link IDs.

    Returns:
        list[IndustrialAsset]: Updated assets with cross-source identifiers linked.
    """
    links: dict[str, set[str]] = defaultdict(set)
    for c in candidates:
        if c.confidence >= link_threshold:
            links[c.primary_asset_id].add(c.candidate_asset_id)
            links[c.candidate_asset_id].add(c.primary_asset_id)

    updated: list[IndustrialAsset] = []
    for a in assets:
        linked = set(a.linked_source_ids)
        for other_id in links.get(a.id, set()):
            linked.add(other_id)

        if len(linked) != len(a.linked_source_ids):
            # Model is frozen, so create updated instance via model_dump
            data = a.model_dump()
            data["linked_source_ids"] = sorted(linked)
            updated.append(IndustrialAsset.model_validate(data))
        else:
            updated.append(a)

    return updated
