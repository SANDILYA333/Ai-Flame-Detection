"""Comprehensive unit and determinism tests for EVENT clustering engine."""

import random
from datetime import UTC, datetime, timedelta

import pytest

from packages.config.scientific import ScientificConfig
from packages.errors import MissingConfigurationError
from packages.events import (
    cluster_detections_spatiotemporal,
    derive_thermal_events,
)
from packages.schemas.common import Coordinate
from packages.schemas.detection import Detection


@pytest.fixture
def calibrated_config() -> ScientificConfig:
    """Fixture providing a complete, calibrated ScientificConfig for testing."""
    return ScientificConfig(
        version="v1.0-test",
        name="test_profile",
        description="Calibrated test configuration profile",
        spatial_cluster_radius_meters=1000.0,  # 1 km
        temporal_window_hours=2.0,  # 2 hours
        persistence_threshold_days=30.0,
        persistence_min_observations=5,
        attribution_radius_meters=1500.0,
        attribution_confidence_threshold=0.7,
        minimum_event_confidence=0.5,
        abstention_confidence_threshold=0.4,
    )


def _make_detection(
    detection_id: str,
    lat: float,
    lon: float,
    acquired_at: datetime,
    frp_mw: float | None = 10.0,
) -> Detection:
    """Helper to create a canonical Detection instance for testing."""
    return Detection(
        detection_id=detection_id,
        source="firms",
        source_snapshot_id="snap-001",
        acquired_at=acquired_at,
        geometry=Coordinate(latitude=lat, longitude=lon),
        satellite="NOAA-20",
        instrument="VIIRS",
        product_type="nrt",
        product_version="v1.0",
        raw_hash="a" * 64,
        frp_mw=frp_mw,
    )


class TestEventClusteringAlgorithm:
    """Validate core spatiotemporal clustering behavior."""

    def test_zero_detections_returns_empty_list(
        self, calibrated_config: ScientificConfig
    ) -> None:
        """Zero input detections produces zero clusters / events."""
        events = derive_thermal_events([], calibrated_config)
        assert events == []

        clusters = cluster_detections_spatiotemporal([], 1000.0, 2.0)
        assert clusters == []

    def test_single_detection_cluster_and_event(
        self, calibrated_config: ScientificConfig
    ) -> None:
        """Single detection forms an event with duration 0.0 and 1 member."""
        t0 = datetime(2026, 8, 29, 12, 0, 0, tzinfo=UTC)
        det = _make_detection("DET-001", 28.6139, 77.2090, t0, frp_mw=25.0)

        events = derive_thermal_events([det], calibrated_config)
        assert len(events) == 1
        event = events[0]

        assert event.detection_count == 1
        assert event.detection_ids == ["DET-001"]
        assert event.started_at == t0
        assert event.ended_at == t0
        assert event.duration_seconds == 0.0
        assert event.mean_frp_mw == 25.0
        assert event.max_frp_mw == 25.0
        assert event.centroid_geometry.latitude == 28.6139
        assert event.centroid_geometry.longitude == 77.2090

    def test_nearby_detections_merge_into_single_event(
        self, calibrated_config: ScientificConfig
    ) -> None:
        """Two detections within 1 km and 1 hour merge into one thermal event."""
        t0 = datetime(2026, 8, 29, 10, 0, 0, tzinfo=UTC)
        t1 = datetime(2026, 8, 29, 10, 45, 0, tzinfo=UTC)

        # ~500m apart
        det1 = _make_detection("DET-001", 28.6139, 77.2090, t0, frp_mw=10.0)
        det2 = _make_detection("DET-002", 28.6184, 77.2090, t1, frp_mw=30.0)

        events = derive_thermal_events([det1, det2], calibrated_config)
        assert len(events) == 1
        event = events[0]

        assert event.detection_count == 2
        assert event.detection_ids == ["DET-001", "DET-002"]
        assert event.started_at == t0
        assert event.ended_at == t1
        assert event.duration_seconds == 2700.0  # 45 minutes
        assert event.mean_frp_mw == 20.0
        assert event.max_frp_mw == 30.0

    def test_nearby_space_distant_time_separates_events(
        self, calibrated_config: ScientificConfig
    ) -> None:
        """Detections close in space but separated by > 2 hours form separate events."""
        t0 = datetime(2026, 8, 29, 10, 0, 0, tzinfo=UTC)
        t1 = datetime(2026, 8, 29, 14, 0, 0, tzinfo=UTC)  # 4 hours later

        det1 = _make_detection("DET-001", 28.6139, 77.2090, t0)
        det2 = _make_detection("DET-002", 28.6140, 77.2090, t1)

        events = derive_thermal_events([det1, det2], calibrated_config)
        assert len(events) == 2
        assert events[0].detection_ids == ["DET-001"]
        assert events[1].detection_ids == ["DET-002"]

    def test_distant_space_same_time_separates_events(
        self, calibrated_config: ScientificConfig
    ) -> None:
        """Detections at the same time but separated by > 1 km form separate events."""
        t0 = datetime(2026, 8, 29, 10, 0, 0, tzinfo=UTC)

        # Delhi vs Mumbai (~1148 km)
        det1 = _make_detection("DET-DELHI", 28.6139, 77.2090, t0)
        det2 = _make_detection("DET-MUMBAI", 19.0760, 72.8777, t0)

        events = derive_thermal_events([det1, det2], calibrated_config)
        assert len(events) == 2
        # Deterministically sorted by (acquired_at, latitude, longitude)
        assert events[0].detection_ids == ["DET-MUMBAI"]  # lat 19.0760
        assert events[1].detection_ids == ["DET-DELHI"]  # lat 28.6139

    def test_transitive_connectivity_chain(
        self, calibrated_config: ScientificConfig
    ) -> None:
        """Transitive chain A -> B -> C forms one merged event.

        A is 600m from B, B is 600m from C (A to C is 1200m > 1000m radius).
        Because A connects to B and B connects to C, all 3 belong to one cluster.
        """
        t0 = datetime(2026, 8, 29, 10, 0, 0, tzinfo=UTC)
        t1 = datetime(2026, 8, 29, 10, 30, 0, tzinfo=UTC)
        t2 = datetime(2026, 8, 29, 11, 0, 0, tzinfo=UTC)

        det_a = _make_detection("DET-A", 28.6139, 77.2090, t0, frp_mw=10.0)
        det_b = _make_detection("DET-B", 28.6190, 77.2090, t1, frp_mw=20.0)
        det_c = _make_detection("DET-C", 28.6245, 77.2090, t2, frp_mw=30.0)

        events = derive_thermal_events([det_a, det_b, det_c], calibrated_config)
        assert len(events) == 1
        event = events[0]

        assert event.detection_count == 3
        assert event.detection_ids == ["DET-A", "DET-B", "DET-C"]
        assert event.started_at == t0
        assert event.ended_at == t2
        assert event.duration_seconds == 3600.0
        assert event.mean_frp_mw == 20.0
        assert event.max_frp_mw == 30.0

    def test_frp_null_handling(self, calibrated_config: ScientificConfig) -> None:
        """Detections with null FRP are handled without raising errors."""
        t0 = datetime(2026, 8, 29, 10, 0, 0, tzinfo=UTC)
        det1 = _make_detection("DET-001", 28.6139, 77.2090, t0, frp_mw=None)
        det2 = _make_detection("DET-002", 28.6140, 77.2090, t0, frp_mw=15.0)

        events = derive_thermal_events([det1, det2], calibrated_config)
        assert len(events) == 1
        assert events[0].mean_frp_mw == 15.0
        assert events[0].max_frp_mw == 15.0


class TestScientificConfigurationEnforcement:
    """Validate that uncalibrated configurations are strictly rejected."""

    def test_uncalibrated_config_raises_missing_configuration_error(self) -> None:
        """Incomplete scientific config raises MissingConfigurationError."""
        # Uncalibrated config with all fields None
        uncalibrated = ScientificConfig(version="uncalibrated-v1")
        det = _make_detection(
            "DET-001", 28.6139, 77.2090, datetime(2026, 8, 29, 10, 0, 0, tzinfo=UTC)
        )

        with pytest.raises(MissingConfigurationError) as exc_info:
            derive_thermal_events([det], uncalibrated)

        assert "is incomplete" in str(exc_info.value)
        assert (
            "spatial_cluster_radius_meters"
            in exc_info.value.details["missing_parameters"]
        )


class TestDeterminismAndProvenance:
    """Validate 100% deterministic output under arbitrary input permutations."""

    def test_permutation_invariance(self, calibrated_config: ScientificConfig) -> None:
        """Shuffling input detections in 20 random orders yields identical events."""
        base_time = datetime(2026, 8, 29, 8, 0, 0, tzinfo=UTC)
        detections: list[Detection] = []

        # Create 12 detections across 3 distinct spatio-temporal clusters
        # Cluster 1: Delhi area (4 detections)
        for i in range(4):
            detections.append(
                _make_detection(
                    f"DET-DELHI-{i}",
                    28.6139 + i * 0.002,
                    77.2090 + i * 0.002,
                    base_time + timedelta(minutes=i * 20),
                    frp_mw=10.0 + i * 5,
                )
            )

        # Cluster 2: Mumbai area (4 detections)
        for i in range(4):
            detections.append(
                _make_detection(
                    f"DET-MUMBAI-{i}",
                    19.0760 + i * 0.002,
                    72.8777 + i * 0.002,
                    base_time + timedelta(minutes=i * 15),
                    frp_mw=20.0 + i * 5,
                )
            )

        # Cluster 3: Kolkata area 1 day later (4 detections)
        for i in range(4):
            detections.append(
                _make_detection(
                    f"DET-KOLKATA-{i}",
                    22.5726 + i * 0.002,
                    88.3639 + i * 0.002,
                    base_time + timedelta(days=1, minutes=i * 10),
                    frp_mw=15.0 + i * 2,
                )
            )

        # Baseline run
        baseline_events = derive_thermal_events(detections, calibrated_config)
        assert len(baseline_events) == 3

        baseline_ids = [e.event_id for e in baseline_events]
        baseline_member_sets = [e.detection_ids for e in baseline_events]
        baseline_centroids = [
            (e.centroid_geometry.latitude, e.centroid_geometry.longitude)
            for e in baseline_events
        ]

        # Test 20 randomized shuffles
        rng = random.Random(42)
        for trial in range(20):
            shuffled = list(detections)
            rng.shuffle(shuffled)

            trial_events = derive_thermal_events(shuffled, calibrated_config)
            assert len(trial_events) == 3

            trial_ids = [e.event_id for e in trial_events]
            trial_member_sets = [e.detection_ids for e in trial_events]
            trial_centroids = [
                (e.centroid_geometry.latitude, e.centroid_geometry.longitude)
                for e in trial_events
            ]

            assert trial_ids == baseline_ids, f"Event IDs diverged in trial {trial}"
            assert trial_member_sets == baseline_member_sets, (
                f"Member sets diverged in trial {trial}"
            )
            assert trial_centroids == baseline_centroids, (
                f"Centroids diverged in trial {trial}"
            )

    def test_configuration_change_changes_event_id(
        self, calibrated_config: ScientificConfig
    ) -> None:
        """Changing configuration version or parameters produces a distinct event ID."""
        t0 = datetime(2026, 8, 29, 10, 0, 0, tzinfo=UTC)
        det = _make_detection("DET-001", 28.6139, 77.2090, t0)

        events_v1 = derive_thermal_events([det], calibrated_config)

        config_v2 = calibrated_config.model_copy(update={"version": "v2.0-calibrated"})
        events_v2 = derive_thermal_events([det], config_v2)

        assert events_v1[0].event_id != events_v2[0].event_id
        assert events_v1[0].formation_configuration_version == "v1.0-test"
        assert events_v2[0].formation_configuration_version == "v2.0-calibrated"
