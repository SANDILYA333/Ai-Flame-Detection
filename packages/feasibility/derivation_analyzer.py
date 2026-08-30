"""Phase 3 Event and Persistent Source derivation feasibility analyzer."""

from collections import Counter
from collections.abc import Sequence

from packages.config.scientific import ScientificConfig
from packages.events.service import derive_thermal_events
from packages.feasibility.models import DerivationFeasibilityMetrics
from packages.schemas.detection import Detection
from packages.sources.service import derive_persistent_sources


def analyze_derivation_feasibility(
    detections: Sequence[Detection],
    config: ScientificConfig,
    approx_area_sqkm: float,
) -> DerivationFeasibilityMetrics:
    """Analyze event clustering and longitudinal persistence tracking feasibility.

    Reuses Phase 3 canonical derivation engines directly to measure how effectively
    raw detections form spatiotemporally coherent events and persistent sources.

    Args:
        detections: Filtered detection records within the study area.
        config: Authoritative ScientificConfig instance.
        approx_area_sqkm: Surface area in square kilometers.

    Returns:
        DerivationFeasibilityMetrics: Event clustering and persistence metrics.
    """
    if not detections:
        return DerivationFeasibilityMetrics(
            candidate_events_count=0,
            mean_detections_per_event=0.0,
            candidate_sources_count=0,
            persistence_state_breakdown={},
            persistent_source_density=0.0,
        )

    # 1. Derive canonical Thermal Events
    events = derive_thermal_events(detections, config)

    if not events:
        return DerivationFeasibilityMetrics(
            candidate_events_count=0,
            mean_detections_per_event=0.0,
            candidate_sources_count=0,
            persistence_state_breakdown={},
            persistent_source_density=0.0,
        )

    mean_det = sum(e.detection_count for e in events) / len(events)

    # 2. Derive canonical Persistent Sources
    sources = derive_persistent_sources(events, config)

    persistence_counts = Counter(s.persistence_state.value for s in sources)

    # Sources per 1,000 sq km
    source_density = (len(sources) / approx_area_sqkm) * 1000.0

    return DerivationFeasibilityMetrics(
        candidate_events_count=len(events),
        mean_detections_per_event=round(mean_det, 2),
        candidate_sources_count=len(sources),
        persistence_state_breakdown=dict(persistence_counts),
        persistent_source_density=round(source_density, 4),
    )
