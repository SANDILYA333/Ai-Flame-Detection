"""Evidence builder and deterministic ID generator for contextual evidence."""

import hashlib

from packages.config.scientific import ScientificConfig
from packages.context.models import ContextFeature
from packages.schemas.common import Coordinate
from packages.schemas.context import ContextEvidence
from packages.schemas.enums import ContextType, EvidenceAvailabilityState


def generate_deterministic_context_id(
    target_id: str,
    provider: str,
    external_feature_id: str,
    config_fingerprint: str,
) -> str:
    """Generate a deterministic, content-addressable context evidence identifier.

    The context ID is derived from the SHA-256 digest of the scientific configuration
    fingerprint, the target entity ID (event or source), the provider, and the
    external feature ID. Given identical inputs, the ID is invariant.

    Args:
        target_id: Identifier of the target Event or PersistentSource.
        provider: Originating provider string (e.g. 'osm', 'wri').
        external_feature_id: External feature identifier.
        config_fingerprint: SHA-256 fingerprint of the scientific configuration.

    Returns:
        str: Canonical context evidence identifier.
    """
    raw_key = (
        f"{config_fingerprint}:ctx:"
        f"{target_id.strip()}:{provider.strip()}:{external_feature_id.strip()}"
    )
    digest = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    return f"ctx_{digest[:24]}"


def build_context_evidence_from_feature(
    target_id: str,
    feature: ContextFeature,
    distance_meters: float,
    config: ScientificConfig,
    source_snapshot_id: str | None = None,
) -> ContextEvidence:
    """Construct a canonical ContextEvidence model from a matched external feature.

    Args:
        target_id: Identifier of the target Event or PersistentSource.
        feature: Normalized external contextual feature.
        distance_meters: Measured geodesic distance in meters from target to feature.
        config: Authoritative ScientificConfig instance.
        source_snapshot_id: Optional snapshot identifier for context dataset lineage.

    Returns:
        ContextEvidence: Canonical validated ContextEvidence domain object.
    """
    config_fingerprint = config.compute_fingerprint()
    context_id = generate_deterministic_context_id(
        target_id=target_id,
        provider=feature.provider,
        external_feature_id=feature.feature_id,
        config_fingerprint=config_fingerprint,
    )

    return ContextEvidence(
        context_id=context_id,
        source_type=feature.provider,
        context_type=feature.context_type,
        geometry=feature.geometry,
        availability_state=EvidenceAvailabilityState.AVAILABLE,
        source_snapshot_id=source_snapshot_id,
        external_facility_id=feature.feature_id,
        facility_name=feature.facility_name,
        bounding_box=feature.bounding_box,
        distance_to_event_meters=distance_meters,
        raw_metadata=feature.raw_metadata,
    )


def build_not_found_evidence(
    target_id: str,
    target_coord: Coordinate,
    provider: str,
    context_type: ContextType,
    config: ScientificConfig,
    source_snapshot_id: str | None = None,
) -> ContextEvidence:
    """Construct an explicit NOT_FOUND_IN_SOURCE ContextEvidence record.

    Explicitly captures evidence of absence of mapped infrastructure in the target
    dataset within the configured search radius.

    Args:
        target_id: Identifier of the target Event or PersistentSource.
        target_coord: Target observation/centroid coordinate.
        provider: Provider queried (e.g. 'osm').
        context_type: Context type queried.
        config: Authoritative ScientificConfig instance.
        source_snapshot_id: Optional snapshot identifier.

    Returns:
        ContextEvidence: Model with NOT_FOUND_IN_SOURCE state.
    """
    config_fingerprint = config.compute_fingerprint()
    context_id = generate_deterministic_context_id(
        target_id=target_id,
        provider=provider,
        external_feature_id="none_found",
        config_fingerprint=config_fingerprint,
    )

    return ContextEvidence(
        context_id=context_id,
        source_type=provider,
        context_type=context_type,
        geometry=target_coord,
        availability_state=EvidenceAvailabilityState.NOT_FOUND_IN_SOURCE,
        source_snapshot_id=source_snapshot_id,
        external_facility_id=None,
        facility_name=None,
        bounding_box=None,
        distance_to_event_meters=None,
        raw_metadata={"search_status": "no_features_within_radius"},
    )
