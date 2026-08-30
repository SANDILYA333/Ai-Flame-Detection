"""Persistent thermal source derivation and longitudinal tracking package."""

from packages.sources.builder import (
    build_persistent_source_from_events,
    generate_deterministic_source_id,
)
from packages.sources.classification import (
    calculate_active_calendar_days,
    calculate_observation_span_days,
    calculate_recurrence_ratio,
    classify_persistence_state,
)
from packages.sources.service import derive_persistent_sources
from packages.sources.tracking import group_events_into_sources

__all__ = [
    "build_persistent_source_from_events",
    "calculate_active_calendar_days",
    "calculate_observation_span_days",
    "calculate_recurrence_ratio",
    "classify_persistence_state",
    "derive_persistent_sources",
    "generate_deterministic_source_id",
    "group_events_into_sources",
]
