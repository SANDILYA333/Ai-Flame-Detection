"""High-level contextual evidence enrichment service.

Coordinates spatial and temporal matching against candidate external features,
enforcing configuration completeness, deterministic ordering, and provenance.
"""

import logging
from collections.abc import Sequence
from datetime import datetime

from packages.config.scientific import ScientificConfig
from packages.context.builder import build_context_evidence_from_feature
from packages.context.matching import (
    evaluate_spatial_association,
    evaluate_temporal_validity,
)
from packages.context.models import ContextFeature, SpatialMatchRule
from packages.schemas.common import Coordinate
from packages.schemas.context import ContextEvidence
from packages.schemas.event import Event
from packages.schemas.source import PersistentSource

logger = logging.getLogger(__name__)


def enrich_with_context(
    target_id: str,
    target_coord: Coordinate,
    target_time: datetime,
    candidate_features: Sequence[ContextFeature],
    config: ScientificConfig,
    rule: SpatialMatchRule = SpatialMatchRule.PROXIMITY_RADIUS,
    source_snapshot_id: str | None = None,
) -> list[ContextEvidence]:
    """Enrich a target spatial entity with nearby contextual evidence.

    CRITICAL SCIENTIFIC INTEGRITY INVARIANTS:
    1. Complete ScientificConfig required; incomplete raises MissingConfigurationError.
    2. Proximity is EVIDENCE only; does NOT imply attribution/causation.
    3. Output evidence records are 100% deterministic and content-addressable.
    4. Temporal validity prevents hindsight leakage.

    Args:
        target_id: Canonical identifier of target entity (Event ID or Source ID).
        target_coord: Representative coordinate of target entity.
        target_time: UTC observation timestamp of target entity.
        candidate_features: Sequence of candidate external ContextFeature objects.
        config: Authoritative ScientificConfig instance.
        rule: Spatial matching rule (proximity radius vs containment).
        source_snapshot_id: Optional context dataset snapshot ID for provenance.

    Returns:
        list[ContextEvidence]: List of canonical ContextEvidence objects.

    Raises:
        MissingConfigurationError: If any required scientific parameter is unset.
    """
    config.validate_completeness()

    radius_meters = config.attribution_radius_meters
    assert radius_meters is not None

    if not candidate_features:
        logger.debug("Zero candidate features provided for target %s", target_id)
        return []

    matched_pairs: list[tuple[ContextFeature, float]] = []

    for feature in candidate_features:
        # 1. Temporal validity filter
        if not evaluate_temporal_validity(target_time, feature):
            continue

        # 2. Spatial association evaluation
        is_matched, dist_m = evaluate_spatial_association(
            target_coord=target_coord,
            feature=feature,
            max_radius_meters=radius_meters,
            rule=rule,
        )

        if is_matched:
            matched_pairs.append((feature, dist_m))

    # 3. Deterministic canonical sorting: (distance, provider, feature_id)
    matched_pairs.sort(
        key=lambda pair: (
            pair[1],
            pair[0].provider,
            pair[0].feature_id,
        )
    )

    # 4. Synthesize canonical ContextEvidence objects
    evidence_list: list[ContextEvidence] = [
        build_context_evidence_from_feature(
            target_id=target_id,
            feature=feat,
            distance_meters=dist,
            config=config,
            source_snapshot_id=source_snapshot_id,
        )
        for feat, dist in matched_pairs
    ]

    logger.info(
        "Enriched target %s with %d context evidence items (config: %s, fp: %s)",
        target_id,
        len(evidence_list),
        config.version,
        config.compute_fingerprint()[:8],
    )

    return evidence_list


def enrich_event_with_context(
    event: Event,
    candidate_features: Sequence[ContextFeature],
    config: ScientificConfig,
    rule: SpatialMatchRule = SpatialMatchRule.PROXIMITY_RADIUS,
    source_snapshot_id: str | None = None,
) -> list[ContextEvidence]:
    """Enrich a canonical Event with nearby contextual evidence."""
    return enrich_with_context(
        target_id=event.event_id,
        target_coord=event.centroid_geometry,
        target_time=event.started_at,
        candidate_features=candidate_features,
        config=config,
        rule=rule,
        source_snapshot_id=source_snapshot_id,
    )


def enrich_source_with_context(
    source: PersistentSource,
    candidate_features: Sequence[ContextFeature],
    config: ScientificConfig,
    rule: SpatialMatchRule = SpatialMatchRule.PROXIMITY_RADIUS,
    source_snapshot_id: str | None = None,
) -> list[ContextEvidence]:
    """Enrich a canonical PersistentSource with nearby contextual evidence."""
    return enrich_with_context(
        target_id=source.source_id,
        target_coord=source.centroid_geometry,
        target_time=source.last_seen_at,
        candidate_features=candidate_features,
        config=config,
        rule=rule,
        source_snapshot_id=source_snapshot_id,
    )
