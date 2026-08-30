"""Orthogonal ontology reasoning engine for evidence-based intelligence inference."""

from collections.abc import Sequence

from packages.schemas.context import ContextEvidence
from packages.schemas.enums import (
    AttributionStrength,
    ContextType,
    EvidenceAvailabilityState,
    PersistenceState,
    PhenomenonType,
)
from packages.schemas.event import Event


def infer_context_type(
    context_evidence: Sequence[ContextEvidence] | None,
) -> ContextType:
    """Infer the primary site context classification from nearest available evidence.

    Args:
        context_evidence: Optional sequence of associated ContextEvidence objects.

    Returns:
        ContextType: Nearest contextual land-use or infrastructure type, or UNKNOWN.
    """
    if not context_evidence:
        return ContextType.UNKNOWN

    available = [
        c
        for c in context_evidence
        if c.availability_state == EvidenceAvailabilityState.AVAILABLE
        and c.distance_to_event_meters is not None
    ]
    if not available:
        return ContextType.UNKNOWN

    # Pre-sort by distance to pick the geographically closest context feature
    available.sort(
        key=lambda c: (c.distance_to_event_meters or float("inf"), c.context_id)
    )
    return available[0].context_type


def infer_attribution_strength(
    context_evidence: Sequence[ContextEvidence] | None,
    attribution_radius_meters: float,
) -> AttributionStrength:
    """Compute physical spatial association strength to nearest contextual facility.

    CRITICAL SCIENTIFIC INTEGRITY INVARIANT:
    Attribution strength represents spatial association confidence, NOT proof
    of physical causation, fire severity, or legal culpability.

    Distance Decay Partitioning:
    - STRONG: d <= (1/3) * radius
    - MODERATE: (1/3) * radius < d <= (2/3) * radius
    - WEAK: (2/3) * radius < d <= radius
    - UNKNOWN: No available contextual feature within radius.

    Args:
        context_evidence: Optional sequence of associated ContextEvidence objects.
        attribution_radius_meters: Maximum search radius in meters.

    Returns:
        AttributionStrength: Classified attribution strength.
    """
    if not context_evidence:
        return AttributionStrength.UNKNOWN

    available = [
        c
        for c in context_evidence
        if c.availability_state == EvidenceAvailabilityState.AVAILABLE
        and c.distance_to_event_meters is not None
    ]
    if not available:
        return AttributionStrength.UNKNOWN

    min_dist = min(
        c.distance_to_event_meters
        for c in available
        if c.distance_to_event_meters is not None
    )

    if min_dist > attribution_radius_meters:
        return AttributionStrength.UNKNOWN

    strong_cutoff = attribution_radius_meters / 3.0
    moderate_cutoff = (2.0 * attribution_radius_meters) / 3.0

    if min_dist <= strong_cutoff:
        return AttributionStrength.STRONG
    if min_dist <= moderate_cutoff:
        return AttributionStrength.MODERATE
    return AttributionStrength.WEAK


def infer_phenomenon_type(
    persistence_state: PersistenceState,
    context_type: ContextType,
    event: Event,
) -> PhenomenonType:
    """Infer physical thermal anomaly phenomenon from orthogonal dimensions.

    Combines temporal persistence state, site context, and observation intensity.

    Args:
        persistence_state: Observed temporal persistence pattern.
        context_type: Primary contextual site environment.
        event: Canonical Event domain model.

    Returns:
        PhenomenonType: Classified physical phenomenon.
    """
    # 1. Long-term recurring / persistent activity
    if persistence_state in (PersistenceState.PERSISTENT, PersistenceState.RECURRING):
        if context_type == ContextType.OIL_GAS:
            return PhenomenonType.FLARE
        if context_type in (
            ContextType.INDUSTRIAL,
            ContextType.POWER,
            ContextType.MINING,
        ):
            return PhenomenonType.INDUSTRIAL_THERMAL_SOURCE
        if context_type == ContextType.AGRICULTURAL:
            return PhenomenonType.AGRICULTURAL_BURN
        return PhenomenonType.OTHER_THERMAL_ANOMALY

    # 2. Transient activity (single event or single calendar date)
    if persistence_state == PersistenceState.TRANSIENT:
        if context_type == ContextType.AGRICULTURAL:
            return PhenomenonType.AGRICULTURAL_BURN
        if context_type == ContextType.FOREST_VEGETATION:
            return PhenomenonType.VEGETATION_WILDFIRE
        if context_type in (
            ContextType.OIL_GAS,
            ContextType.INDUSTRIAL,
            ContextType.POWER,
        ):
            return PhenomenonType.INDUSTRIAL_THERMAL_SOURCE
        return PhenomenonType.FIRE

    # 3. Insufficient observation history
    if context_type == ContextType.AGRICULTURAL:
        return PhenomenonType.AGRICULTURAL_BURN
    if context_type == ContextType.FOREST_VEGETATION:
        return PhenomenonType.VEGETATION_WILDFIRE

    return PhenomenonType.UNKNOWN
