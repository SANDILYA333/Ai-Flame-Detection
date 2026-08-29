"""Shared domain contracts and canonical schemas for SIH26162.

This package defines the canonical internal domain models and enumerations
used across services, pipelines, and future API/database layers.
"""

from packages.schemas.common import (
    BaseDomainModel,
    BoundingBox,
    Coordinate,
    ProvenanceReference,
    UtcDatetime,
)
from packages.schemas.context import ContextEvidence
from packages.schemas.detection import Detection
from packages.schemas.enums import (
    AttributionStrength,
    ContextType,
    DayNight,
    EvidenceAvailabilityState,
    PersistenceState,
    PhenomenonType,
)
from packages.schemas.event import Event
from packages.schemas.intelligence import (
    EvidenceCategoryState,
    EvidenceCompleteness,
    IntelligenceResult,
    UncertaintyMetric,
)
from packages.schemas.source import PersistentSource

__all__ = [
    "AttributionStrength",
    "BaseDomainModel",
    "BoundingBox",
    "ContextEvidence",
    "ContextType",
    "Coordinate",
    "DayNight",
    "Detection",
    "Event",
    "EvidenceAvailabilityState",
    "EvidenceCategoryState",
    "EvidenceCompleteness",
    "IntelligenceResult",
    "PersistenceState",
    "PersistentSource",
    "PhenomenonType",
    "ProvenanceReference",
    "UncertaintyMetric",
    "UtcDatetime",
]
