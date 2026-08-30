"""Contextual evidence enrichment package for SIH26162."""

from packages.context.builder import (
    build_context_evidence_from_feature,
    build_not_found_evidence,
    generate_deterministic_context_id,
)
from packages.context.matching import (
    evaluate_spatial_association,
    evaluate_temporal_validity,
)
from packages.context.models import ContextFeature, SpatialMatchRule
from packages.context.pipeline import RealContextLabelingService
from packages.context.providers import ContextProvider, InMemoryContextProvider
from packages.context.service import (
    enrich_event_with_context,
    enrich_source_with_context,
    enrich_with_context,
)

__all__ = [
    "ContextFeature",
    "ContextProvider",
    "InMemoryContextProvider",
    "RealContextLabelingService",
    "SpatialMatchRule",
    "build_context_evidence_from_feature",
    "build_not_found_evidence",
    "enrich_event_with_context",
    "enrich_source_with_context",
    "enrich_with_context",
    "evaluate_spatial_association",
    "evaluate_temporal_validity",
    "generate_deterministic_context_id",
]
