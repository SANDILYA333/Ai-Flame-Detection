"""Comprehensive unit and determinism tests for persistent source tracking."""

import random
from datetime import UTC, datetime, timedelta

import pytest

from packages.config.scientific import ScientificConfig
from packages.errors import MissingConfigurationError
from packages.schemas.common import Coordinate
from packages.schemas.enums import PersistenceState
from packages.schemas.event import Event
from packages.sources import (
    classify_persistence_state,
    derive_persistent_sources,
    group_events_into_sources,
)


@pytest.fixture
def calibrated_config() -> ScientificConfig:
    """Fixture providing a complete, calibrated ScientificConfig for testing."""
    return ScientificConfig(
        version="v1.0-test",
        name="test_profile",
        description="Calibrated test configuration profile",
        spatial_cluster_radius_meters=1000.0,  # 1 km
        temporal_window_hours=2.0,  # 2 hours
        persistence_threshold_days=30.0,  # 30 days
        persistence_min_observations=5,  # 5 active days / events
        attribution_radius_meters=1500.0,
        attribution_confidence_threshold=0.7,
        minimum_event_confidence=0.5,
        abstention_confidence_threshold=0.4,
    )


def _make_event(
    event_id: str,
    lat: float,
    lon: float,
    started_at: datetime,
    duration_minutes: float = 30.0,
    detection_count: int = 2,
) -> Event:
    """Helper to construct a valid canonical Event for testing."""
    ended_at = started_at + timedelta(minutes=duration_minutes)
    det_ids = [f"{event_id}-DET-{i}" for i in range(detection_count)]
    return Event(
        event_id=event_id,
        detection_ids=det_ids,
        detection_count=detection_count,
        started_at=started_at,
        ended_at=ended_at,
        centroid_geometry=Coordinate(latitude=lat, longitude=lon),
        formation_configuration_id="test_profile",
        formation_configuration_version="v1.0-test",
        duration_seconds=duration_minutes * 60.0,
    )


class TestPersistenceClassificationLogic:
    """Validate mathematical rules for classifying PersistenceState."""

    def test_single_instantaneous_event_insufficient_history(self) -> None:
        """Single event with 0 duration classifies as INSUFFICIENT_HISTORY."""
        state = classify_persistence_state(
            total_event_count=1,
            active_days_count=1,
            observation_span_days=0.0,
            persistence_threshold_days=30.0,
            persistence_min_observations=5,
        )
        assert state == PersistenceState.INSUFFICIENT_HISTORY

    def test_single_day_multiple_events_transient(self) -> None:
        """Multiple events on the same calendar day classify as TRANSIENT."""
        state = classify_persistence_state(
            total_event_count=3,
            active_days_count=1,
            observation_span_days=0.5,
            persistence_threshold_days=30.0,
            persistence_min_observations=5,
        )
        assert state == PersistenceState.TRANSIENT

    def test_multi_day_activity_below_threshold_recurring(self) -> None:
        """Activity across 3 days over a 5-day span classifies as RECURRING."""
        state = classify_persistence_state(
            total_event_count=3,
            active_days_count=3,
            observation_span_days=5.0,
            persistence_threshold_days=30.0,
            persistence_min_observations=5,
        )
        assert state == PersistenceState.RECURRING

    def test_multi_day_longitudinal_activity_persistent(self) -> None:
        """Activity across 6 active days over a 35-day span classifies as PERSISTENT."""
        state = classify_persistence_state(
            total_event_count=8,
            active_days_count=6,
            observation_span_days=35.0,
            persistence_threshold_days=30.0,
            persistence_min_observations=5,
        )
        assert state == PersistenceState.PERSISTENT

    def test_invalid_parameters_raise_value_error(self) -> None:
        """Invalid counts or negative spans raise ValueError."""
        with pytest.raises(ValueError):
            classify_persistence_state(0, 1, 10.0, 30.0, 5)

        with pytest.raises(ValueError):
            classify_persistence_state(1, 0, 10.0, 30.0, 5)

        with pytest.raises(ValueError):
            classify_persistence_state(1, 1, -1.0, 30.0, 5)


class TestSourceDerivationService:
    """Validate high-level source derivation and spatial tracking."""

    def test_zero_events_returns_empty_list(
        self, calibrated_config: ScientificConfig
    ) -> None:
        """Zero events produces zero persistent sources."""
        sources = derive_persistent_sources([], calibrated_config)
        assert sources == []

        groups = group_events_into_sources([], 1000.0)
        assert groups == []

    def test_single_event_source_formation(
        self, calibrated_config: ScientificConfig
    ) -> None:
        """Single event produces one source with matched properties."""
        t0 = datetime(2026, 8, 1, 10, 0, 0, tzinfo=UTC)
        ev = _make_event("EVT-001", 28.6139, 77.2090, t0, duration_minutes=60.0)

        sources = derive_persistent_sources([ev], calibrated_config)
        assert len(sources) == 1
        src = sources[0]

        assert src.total_event_count == 1
        assert src.linked_event_ids == ["EVT-001"]
        assert src.first_seen_at == t0
        assert src.last_seen_at == t0 + timedelta(minutes=60.0)
        assert src.active_days_count == 1
        assert src.persistence_state == PersistenceState.TRANSIENT
        assert src.centroid_geometry.latitude == 28.6139
        assert src.centroid_geometry.longitude == 77.2090

    def test_adversarial_single_day_burst_not_persistent(
        self, calibrated_config: ScientificConfig
    ) -> None:
        """ADVERSARIAL: 100 detections in 1 large event on 1 day is NOT persistent."""
        t0 = datetime(2026, 8, 1, 10, 0, 0, tzinfo=UTC)
        large_event = _make_event(
            "EVT-BIG-FIRE",
            28.6139,
            77.2090,
            t0,
            duration_minutes=120.0,
            detection_count=100,
        )

        sources = derive_persistent_sources([large_event], calibrated_config)
        assert len(sources) == 1
        src = sources[0]

        # Must NOT be persistent despite 100 detections
        assert src.persistence_state != PersistenceState.PERSISTENT
        assert src.persistence_state == PersistenceState.TRANSIENT
        assert src.active_days_count == 1

    def test_multi_day_longitudinal_source_persistent(
        self, calibrated_config: ScientificConfig
    ) -> None:
        """Events spanning 35 days across 6 dates form a PERSISTENT source."""
        base_time = datetime(2026, 8, 1, 10, 0, 0, tzinfo=UTC)
        events: list[Event] = []

        # 6 events at the same facility/location across 35 days
        day_offsets = [0, 5, 12, 20, 28, 35]
        for idx, offset in enumerate(day_offsets):
            ev_time = base_time + timedelta(days=offset)
            events.append(_make_event(f"EVT-FLARE-{idx}", 28.6139, 77.2090, ev_time))

        sources = derive_persistent_sources(events, calibrated_config)
        assert len(sources) == 1
        src = sources[0]

        assert src.total_event_count == 6
        assert src.active_days_count == 6
        assert src.persistence_state == PersistenceState.PERSISTENT
        assert src.recurrence_ratio is not None
        # 6 active days / 36 calendar days span = ~0.1667
        assert 0.15 < src.recurrence_ratio < 0.18

    def test_spatially_separate_events_form_distinct_sources(
        self, calibrated_config: ScientificConfig
    ) -> None:
        """Events at distinct geographic sites (> 1 km) form distinct sources."""
        t0 = datetime(2026, 8, 1, 10, 0, 0, tzinfo=UTC)
        t1 = datetime(2026, 8, 10, 10, 0, 0, tzinfo=UTC)

        # Delhi vs Mumbai (~1148 km)
        ev_delhi = _make_event("EVT-DELHI", 28.6139, 77.2090, t0)
        ev_mumbai = _make_event("EVT-MUMBAI", 19.0760, 72.8777, t1)

        sources = derive_persistent_sources([ev_delhi, ev_mumbai], calibrated_config)
        assert len(sources) == 2
        # Deterministically ordered
        source_event_ids = [s.linked_event_ids for s in sources]
        assert ["EVT-DELHI"] in source_event_ids
        assert ["EVT-MUMBAI"] in source_event_ids


class TestConfigurationAndDeterminism:
    """Validate config enforcement and 100% permutation determinism."""

    def test_uncalibrated_config_raises_error(self) -> None:
        """Incomplete scientific config raises MissingConfigurationError."""
        uncalibrated = ScientificConfig(version="uncalibrated-v1")
        ev = _make_event("EVT-001", 28.6139, 77.2090, datetime(2026, 8, 1, tzinfo=UTC))

        with pytest.raises(MissingConfigurationError) as exc_info:
            derive_persistent_sources([ev], uncalibrated)

        assert "is incomplete" in str(exc_info.value)
        missing = exc_info.value.details["missing_parameters"]
        assert "persistence_threshold_days" in missing

    def test_permutation_invariance_20_trials(
        self, calibrated_config: ScientificConfig
    ) -> None:
        """20 random orderings yield identical persistent sources."""
        base_time = datetime(2026, 8, 1, 8, 0, 0, tzinfo=UTC)
        events: list[Event] = []

        # 3 distinct geographic clusters
        # Site 1: 5 events across 40 days
        for i in range(5):
            events.append(
                _make_event(
                    f"EVT-SITE1-{i}",
                    28.6139 + i * 0.001,
                    77.2090 + i * 0.001,
                    base_time + timedelta(days=i * 10),
                )
            )

        # Site 2: 3 events across 15 days
        for i in range(3):
            events.append(
                _make_event(
                    f"EVT-SITE2-{i}",
                    19.0760 + i * 0.001,
                    72.8777 + i * 0.001,
                    base_time + timedelta(days=i * 5),
                )
            )

        # Site 3: 2 events on same day
        for i in range(2):
            events.append(
                _make_event(
                    f"EVT-SITE3-{i}",
                    22.5726 + i * 0.001,
                    88.3639 + i * 0.001,
                    base_time + timedelta(hours=i * 4),
                )
            )

        # Baseline derivation
        baseline_sources = derive_persistent_sources(events, calibrated_config)
        assert len(baseline_sources) == 3

        baseline_ids = [s.source_id for s in baseline_sources]
        baseline_member_sets = [s.linked_event_ids for s in baseline_sources]
        baseline_centroids = [
            (s.centroid_geometry.latitude, s.centroid_geometry.longitude)
            for s in baseline_sources
        ]
        baseline_states = [s.persistence_state for s in baseline_sources]

        # Test 20 randomized permutations
        rng = random.Random(42)
        for trial in range(20):
            shuffled = list(events)
            rng.shuffle(shuffled)

            trial_sources = derive_persistent_sources(shuffled, calibrated_config)
            assert len(trial_sources) == 3

            trial_ids = [s.source_id for s in trial_sources]
            trial_member_sets = [s.linked_event_ids for s in trial_sources]
            trial_centroids = [
                (s.centroid_geometry.latitude, s.centroid_geometry.longitude)
                for s in trial_sources
            ]
            trial_states = [s.persistence_state for s in trial_sources]

            assert trial_ids == baseline_ids, f"Source IDs diverged in trial {trial}"
            assert trial_member_sets == baseline_member_sets, (
                f"Member sets diverged in trial {trial}"
            )
            assert trial_centroids == baseline_centroids, (
                f"Centroids diverged in trial {trial}"
            )
            assert trial_states == baseline_states, f"States diverged in trial {trial}"

    def test_configuration_change_changes_source_id(
        self, calibrated_config: ScientificConfig
    ) -> None:
        """Changing configuration version produces a distinct source ID."""
        t0 = datetime(2026, 8, 1, 10, 0, 0, tzinfo=UTC)
        ev = _make_event("EVT-001", 28.6139, 77.2090, t0)

        sources_v1 = derive_persistent_sources([ev], calibrated_config)

        config_v2 = calibrated_config.model_copy(update={"version": "v2.0-calibrated"})
        sources_v2 = derive_persistent_sources([ev], config_v2)

        assert sources_v1[0].source_id != sources_v2[0].source_id
        assert sources_v1[0].persistence_configuration_version == "v1.0-test"
        assert sources_v2[0].persistence_configuration_version == "v2.0-calibrated"
