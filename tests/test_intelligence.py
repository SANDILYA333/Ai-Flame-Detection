"""Unit, adversarial, and determinism tests for thermal intelligence."""

import random
from datetime import UTC, datetime, timedelta

import pytest

from packages.config.scientific import ScientificConfig
from packages.errors import MissingConfigurationError
from packages.intelligence import (
    calculate_calibrated_confidence,
    derive_intelligence,
    evaluate_abstention,
    evaluate_evidence_completeness,
    infer_attribution_strength,
    infer_phenomenon_type,
)
from packages.schemas.common import Coordinate
from packages.schemas.context import ContextEvidence
from packages.schemas.enums import (
    AttributionStrength,
    ContextType,
    EvidenceAvailabilityState,
    PersistenceState,
    PhenomenonType,
)
from packages.schemas.event import Event
from packages.schemas.source import PersistentSource


@pytest.fixture
def calibrated_config() -> ScientificConfig:
    """Fixture providing a complete, calibrated ScientificConfig for testing."""
    return ScientificConfig(
        version="v1.0-test",
        name="test_profile",
        description="Calibrated test configuration profile",
        spatial_cluster_radius_meters=1000.0,
        temporal_window_hours=2.0,
        persistence_threshold_days=30.0,
        persistence_min_observations=5,
        attribution_radius_meters=1500.0,
        attribution_confidence_threshold=0.7,
        minimum_event_confidence=0.5,
        abstention_confidence_threshold=0.4,
    )


def _make_event(
    event_id: str = "EVT-001",
    lat: float = 28.6139,
    lon: float = 77.2090,
    started_at: datetime | None = None,
    duration_seconds: float = 1800.0,
    detection_count: int = 2,
    mean_frp_mw: float | None = 25.0,
) -> Event:
    """Helper to create a canonical Event domain object."""
    t0 = started_at or datetime(2026, 8, 1, 10, 0, 0, tzinfo=UTC)
    t1 = t0 + timedelta(seconds=duration_seconds)
    return Event(
        event_id=event_id,
        detection_ids=[f"{event_id}-D{i}" for i in range(detection_count)],
        detection_count=detection_count,
        started_at=t0,
        ended_at=t1,
        centroid_geometry=Coordinate(latitude=lat, longitude=lon),
        formation_configuration_id="test_profile",
        formation_configuration_version="v1.0-test",
        duration_seconds=duration_seconds,
        mean_frp_mw=mean_frp_mw,
    )


def _make_source(
    source_id: str = "SRC-001",
    lat: float = 28.6139,
    lon: float = 77.2090,
    persistence_state: PersistenceState = PersistenceState.PERSISTENT,
    active_days: int = 6,
) -> PersistentSource:
    """Helper to create a canonical PersistentSource domain object."""
    t0 = datetime(2026, 7, 1, 10, 0, 0, tzinfo=UTC)
    t1 = datetime(2026, 8, 5, 10, 0, 0, tzinfo=UTC)
    return PersistentSource(
        source_id=source_id,
        linked_event_ids=["EVT-1", "EVT-2"],
        total_event_count=2,
        centroid_geometry=Coordinate(latitude=lat, longitude=lon),
        first_seen_at=t0,
        last_seen_at=t1,
        active_days_count=active_days,
        persistence_state=persistence_state,
        persistence_configuration_id="test_profile",
        persistence_configuration_version="v1.0-test",
    )


def _make_context_evidence(
    context_id: str = "CTX-001",
    context_type: ContextType = ContextType.OIL_GAS,
    distance_meters: float = 400.0,
    availability_state: EvidenceAvailabilityState = (
        EvidenceAvailabilityState.AVAILABLE
    ),
) -> ContextEvidence:
    """Helper to create a canonical ContextEvidence domain object."""
    return ContextEvidence(
        context_id=context_id,
        source_type="osm",
        context_type=context_type,
        geometry=Coordinate(latitude=28.6170, longitude=77.2090),
        availability_state=availability_state,
        distance_to_event_meters=distance_meters,
        facility_name="Northern Petrochemical Complex",
    )


class TestOrthogonalReasoningRules:
    """Validate multi-dimensional orthogonal ontology reasoning."""

    def test_persistent_oil_gas_classified_as_flare(self) -> None:
        """Persistent thermal source in oil/gas context is classified as FLARE."""
        ev = _make_event()
        phenom = infer_phenomenon_type(
            persistence_state=PersistenceState.PERSISTENT,
            context_type=ContextType.OIL_GAS,
            event=ev,
        )
        assert phenom == PhenomenonType.FLARE

    def test_persistent_power_plant_classified_as_industrial_source(self) -> None:
        """Persistent thermal source in power context is INDUSTRIAL_THERMAL_SOURCE."""
        ev = _make_event()
        phenom = infer_phenomenon_type(
            persistence_state=PersistenceState.PERSISTENT,
            context_type=ContextType.POWER,
            event=ev,
        )
        assert phenom == PhenomenonType.INDUSTRIAL_THERMAL_SOURCE

    def test_transient_agricultural_burn(self) -> None:
        """Transient event in agricultural context is AGRICULTURAL_BURN."""
        ev = _make_event()
        phenom = infer_phenomenon_type(
            persistence_state=PersistenceState.TRANSIENT,
            context_type=ContextType.AGRICULTURAL,
            event=ev,
        )
        assert phenom == PhenomenonType.AGRICULTURAL_BURN

    def test_transient_forest_vegetation_wildfire(self) -> None:
        """Transient event in forest/vegetation context is VEGETATION_WILDFIRE."""
        ev = _make_event()
        phenom = infer_phenomenon_type(
            persistence_state=PersistenceState.TRANSIENT,
            context_type=ContextType.FOREST_VEGETATION,
            event=ev,
        )
        assert phenom == PhenomenonType.VEGETATION_WILDFIRE

    def test_attribution_distance_decay_partitioning(self) -> None:
        """Spatial distance partitions into STRONG, MODERATE, WEAK."""
        radius = 1500.0  # cutoffs at 500m and 1000m

        ctx_strong = [_make_context_evidence(distance_meters=300.0)]
        ctx_mod = [_make_context_evidence(distance_meters=750.0)]
        ctx_weak = [_make_context_evidence(distance_meters=1200.0)]
        ctx_out = [_make_context_evidence(distance_meters=1800.0)]

        assert (
            infer_attribution_strength(ctx_strong, radius) == AttributionStrength.STRONG
        )
        assert (
            infer_attribution_strength(ctx_mod, radius) == AttributionStrength.MODERATE
        )
        assert infer_attribution_strength(ctx_weak, radius) == AttributionStrength.WEAK
        assert (
            infer_attribution_strength(ctx_out, radius) == AttributionStrength.UNKNOWN
        )
        assert infer_attribution_strength([], radius) == AttributionStrength.UNKNOWN


class TestUncertaintyAndAbstention:
    """Validate uncertainty metrics and abstention recommendation."""

    def test_high_confidence_no_abstention(self) -> None:
        """High evidence confidence produces abstention_recommended=False."""
        conf = calculate_calibrated_confidence(
            attribution_strength=AttributionStrength.STRONG,
            persistence_state=PersistenceState.PERSISTENT,
            data_quality_score=0.9,
        )
        assert conf >= 0.85

        ev = _make_event()
        completeness = evaluate_evidence_completeness(
            ev, _make_source(), [_make_context_evidence()]
        )
        abstain, reason = evaluate_abstention(
            conf, completeness, abstention_threshold=0.4
        )

        assert abstain is False
        assert reason is None

    def test_low_confidence_triggers_abstention(self) -> None:
        """Low confidence below cutoff triggers abstention recommendation."""
        conf = calculate_calibrated_confidence(
            attribution_strength=AttributionStrength.UNKNOWN,
            persistence_state=PersistenceState.INSUFFICIENT_HISTORY,
            data_quality_score=0.2,
        )
        assert conf < 0.40

        ev = _make_event()
        completeness = evaluate_evidence_completeness(ev, None, [])
        abstain, reason = evaluate_abstention(
            conf, completeness, abstention_threshold=0.4
        )

        assert abstain is True
        assert reason is not None
        assert "below configured abstention threshold" in reason

    def test_provider_failure_triggers_abstention(self) -> None:
        """Critical evidence provider failure triggers abstention."""
        ev = _make_event()
        ctx_fail = _make_context_evidence(
            availability_state=EvidenceAvailabilityState.UNAVAILABLE
        )
        completeness = evaluate_evidence_completeness(ev, None, [ctx_fail])

        abstain, reason = evaluate_abstention(
            0.8, completeness, abstention_threshold=0.4
        )
        assert abstain is True
        assert "provider retrieval failure" in str(reason)


class TestIntelligenceDerivationService:
    """Validate end-to-end intelligence derivation service."""

    def test_full_pipeline_derivation_persistent_flare(
        self, calibrated_config: ScientificConfig
    ) -> None:
        """End-to-end intelligence synthesis for persistent flare."""
        ev = _make_event(event_id="EVT-FLARE-1", detection_count=3, mean_frp_mw=45.0)
        src = _make_source(
            source_id="SRC-FLARE-1",
            persistence_state=PersistenceState.PERSISTENT,
        )
        ctx = [
            _make_context_evidence("CTX-1", ContextType.OIL_GAS, distance_meters=350.0)
        ]

        result = derive_intelligence(
            event=ev,
            source=src,
            context_evidence=ctx,
            config=calibrated_config,
        )

        assert result.event_id == "EVT-FLARE-1"
        assert result.source_id == "SRC-FLARE-1"
        assert result.phenomenon == PhenomenonType.FLARE
        assert result.context == ContextType.OIL_GAS
        assert result.persistence == PersistenceState.PERSISTENT
        assert result.attribution == AttributionStrength.STRONG
        assert result.uncertainty.abstention_recommended is False
        assert result.uncertainty.calibrated_confidence is not None
        assert result.uncertainty.calibrated_confidence > 0.70
        assert result.evidence_completeness.available_count == 3
        assert result.evidence_completeness.completeness_ratio == 1.0

    def test_isolated_event_derivation_abstention(
        self, calibrated_config: ScientificConfig
    ) -> None:
        """Single isolated event with no context triggers abstention."""
        ev = _make_event(event_id="EVT-ISO-1", detection_count=1, duration_seconds=0.0)

        result = derive_intelligence(
            event=ev,
            source=None,
            context_evidence=[],
            config=calibrated_config,
        )

        assert result.persistence == PersistenceState.INSUFFICIENT_HISTORY
        assert result.context == ContextType.UNKNOWN
        assert result.attribution == AttributionStrength.UNKNOWN
        assert result.phenomenon == PhenomenonType.UNKNOWN
        assert result.uncertainty.abstention_recommended is True


class TestConfigurationAndDeterminism:
    """Validate config completeness enforcement and 100% permutation determinism."""

    def test_uncalibrated_config_raises_error(self) -> None:
        """Incomplete scientific config raises MissingConfigurationError."""
        uncalibrated = ScientificConfig(version="uncalibrated-v1")
        ev = _make_event()

        with pytest.raises(MissingConfigurationError) as exc_info:
            derive_intelligence(ev, None, [], uncalibrated)

        assert "is incomplete" in str(exc_info.value)
        missing = exc_info.value.details["missing_parameters"]
        assert "abstention_confidence_threshold" in missing

    def test_permutation_invariance_20_trials(
        self, calibrated_config: ScientificConfig
    ) -> None:
        """20 random orderings of context produce identical intelligence results."""
        ev = _make_event("EVT-PERM")
        src = _make_source("SRC-PERM")
        ctx_list = [
            _make_context_evidence(
                f"CTX-{i}",
                ContextType.INDUSTRIAL,
                distance_meters=300.0 + i * 100.0,
            )
            for i in range(5)
        ]

        baseline = derive_intelligence(ev, src, ctx_list, calibrated_config)

        rng = random.Random(42)
        for _trial in range(20):
            shuffled = list(ctx_list)
            rng.shuffle(shuffled)

            trial_result = derive_intelligence(ev, src, shuffled, calibrated_config)

            assert trial_result.intelligence_id == baseline.intelligence_id
            assert trial_result.phenomenon == baseline.phenomenon
            assert trial_result.context == baseline.context
            assert trial_result.persistence == baseline.persistence
            assert trial_result.attribution == baseline.attribution
            assert (
                trial_result.uncertainty.calibrated_confidence
                == baseline.uncertainty.calibrated_confidence
            )

    def test_configuration_change_changes_intelligence_id(
        self, calibrated_config: ScientificConfig
    ) -> None:
        """Changing configuration version changes intelligence_id."""
        ev = _make_event("EVT-LINEAGE")
        src = _make_source("SRC-LINEAGE")

        res_v1 = derive_intelligence(ev, src, [], calibrated_config)

        config_v2 = calibrated_config.model_copy(update={"version": "v2.0-calibrated"})
        res_v2 = derive_intelligence(ev, src, [], config_v2)

        assert res_v1.intelligence_id != res_v2.intelligence_id
        assert res_v1.configuration_version == "v1.0-test"
        assert res_v2.configuration_version == "v2.0-calibrated"
