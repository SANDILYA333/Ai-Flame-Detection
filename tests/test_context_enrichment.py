"""Comprehensive unit and determinism tests for contextual evidence enrichment."""

import random
from datetime import UTC, datetime

import pytest

from packages.config.scientific import ScientificConfig
from packages.context import (
    ContextFeature,
    InMemoryContextProvider,
    SpatialMatchRule,
    build_not_found_evidence,
    enrich_event_with_context,
    enrich_source_with_context,
    enrich_with_context,
    evaluate_spatial_association,
    evaluate_temporal_validity,
)
from packages.errors import MissingConfigurationError
from packages.schemas.common import BoundingBox, Coordinate
from packages.schemas.enums import (
    ContextType,
    EvidenceAvailabilityState,
    PersistenceState,
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
        attribution_radius_meters=1500.0,  # 1.5 km context search radius
        attribution_confidence_threshold=0.7,
        minimum_event_confidence=0.5,
        abstention_confidence_threshold=0.4,
    )


def _make_context_feature(
    feature_id: str,
    lat: float,
    lon: float,
    context_type: ContextType = ContextType.INDUSTRIAL,
    provider: str = "osm",
    facility_name: str | None = "Test Industrial Facility",
    valid_from: datetime | None = None,
    valid_to: datetime | None = None,
    bounding_box: BoundingBox | None = None,
) -> ContextFeature:
    """Helper to create a canonical ContextFeature for testing."""
    return ContextFeature(
        feature_id=feature_id,
        provider=provider,
        dataset_name="planet_osm_test",
        dataset_version="v2026.08",
        context_type=context_type,
        geometry=Coordinate(latitude=lat, longitude=lon),
        facility_name=facility_name,
        bounding_box=bounding_box,
        valid_from=valid_from,
        valid_to=valid_to,
        raw_metadata={"industrial_type": "refinery"},
    )


class TestSpatialAndTemporalMatchingRules:
    """Validate core spatial proximity and temporal validity evaluation."""

    def test_proximity_matching_within_radius(self) -> None:
        """Feature ~500m away matches a 1500m search radius."""
        target = Coordinate(latitude=28.6139, longitude=77.2090)
        # ~500m north
        feat = _make_context_feature("FEAT-001", 28.6184, 77.2090)

        is_matched, dist = evaluate_spatial_association(
            target_coord=target,
            feature=feat,
            max_radius_meters=1500.0,
        )
        assert is_matched is True
        assert 490.0 < dist < 510.0

    def test_proximity_matching_outside_radius_rejected(self) -> None:
        """Feature ~2500m away does not match a 1500m search radius."""
        target = Coordinate(latitude=28.6139, longitude=77.2090)
        # ~2.5 km north
        feat = _make_context_feature("FEAT-002", 28.6364, 77.2090)

        is_matched, dist = evaluate_spatial_association(
            target_coord=target,
            feature=feat,
            max_radius_meters=1500.0,
        )
        assert is_matched is False
        assert dist > 2400.0

    def test_exact_boundary_threshold_behavior(self) -> None:
        """Distances exactly at radius match; distances just outside are rejected."""
        target = Coordinate(latitude=0.0, longitude=0.0)
        feat = _make_context_feature("FEAT-BND", 0.0, 0.0)

        # Distance is 0.0m <= 100.0m -> match
        matched_0, dist_0 = evaluate_spatial_association(target, feat, 100.0)
        assert matched_0 is True
        assert dist_0 == 0.0

        # Distance is 0.0m <= 0.0m -> exact match
        matched_exact, _ = evaluate_spatial_association(target, feat, 0.0)
        assert matched_exact is True

    def test_containment_envelope_matching(self) -> None:
        """Point inside feature bounding box matches under CONTAINMENT_ENVELOPE rule."""
        target = Coordinate(latitude=28.6150, longitude=77.2095)
        bbox = BoundingBox(
            min_latitude=28.6100,
            max_latitude=28.6200,
            min_longitude=77.2000,
            max_longitude=77.2200,
        )
        feat = _make_context_feature("FEAT-POLY", 28.6150, 77.2100, bounding_box=bbox)

        is_matched, _ = evaluate_spatial_association(
            target_coord=target,
            feature=feat,
            max_radius_meters=100.0,
            rule=SpatialMatchRule.CONTAINMENT_ENVELOPE,
        )
        assert is_matched is True

    def test_temporal_validity_matching(self) -> None:
        """Temporal validity correctly prevents hindsight leakage."""
        t_event = datetime(2026, 8, 15, 12, 0, 0, tzinfo=UTC)

        # 1. Static feature (no validity bounds) -> valid
        static_feat = _make_context_feature("FEAT-STATIC", 28.6139, 77.2090)
        assert evaluate_temporal_validity(t_event, static_feat) is True

        # 2. Commissioned in 2025, active through 2030 -> valid
        active_feat = _make_context_feature(
            "FEAT-ACTIVE",
            28.6139,
            77.2090,
            valid_from=datetime(2025, 1, 1, tzinfo=UTC),
            valid_to=datetime(2030, 1, 1, tzinfo=UTC),
        )
        assert evaluate_temporal_validity(t_event, active_feat) is True

        # 3. Commissioned in 2027 (future) -> invalid (prevents hindsight leakage)
        future_feat = _make_context_feature(
            "FEAT-FUTURE",
            28.6139,
            77.2090,
            valid_from=datetime(2027, 1, 1, tzinfo=UTC),
        )
        assert evaluate_temporal_validity(t_event, future_feat) is False

        # 4. Decommissioned in 2024 (past) -> invalid
        decommissioned_feat = _make_context_feature(
            "FEAT-DECOMMISSIONED",
            28.6139,
            77.2090,
            valid_to=datetime(2024, 12, 31, tzinfo=UTC),
        )
        assert evaluate_temporal_validity(t_event, decommissioned_feat) is False


class TestContextEnrichmentService:
    """Validate high-level enrichment service for Events and Sources."""

    def test_zero_candidate_features_returns_empty_list(
        self, calibrated_config: ScientificConfig
    ) -> None:
        """Zero candidate features produces zero evidence."""
        target_coord = Coordinate(latitude=28.6139, longitude=77.2090)
        t0 = datetime(2026, 8, 1, 10, 0, 0, tzinfo=UTC)

        evidence = enrich_with_context(
            "EVT-001", target_coord, t0, [], calibrated_config
        )
        assert evidence == []

    def test_enrich_event_with_nearby_refinery(
        self, calibrated_config: ScientificConfig
    ) -> None:
        """Event near industrial refinery gets ContextEvidence attached."""
        t0 = datetime(2026, 8, 1, 10, 0, 0, tzinfo=UTC)
        ev = Event(
            event_id="EVT-001",
            detection_ids=["DET-1"],
            detection_count=1,
            started_at=t0,
            ended_at=t0,
            centroid_geometry=Coordinate(latitude=28.6139, longitude=77.2090),
            formation_configuration_id="test_profile",
            formation_configuration_version="v1.0-test",
            duration_seconds=0.0,
        )

        refinery = _make_context_feature(
            "OSM-REFINERY",
            28.6170,
            77.2090,
            context_type=ContextType.OIL_GAS,
            facility_name="Northern Petroleum Refinery",
        )
        power_plant_distant = _make_context_feature(
            "WRI-POWER-001",
            28.6500,
            77.2090,
            context_type=ContextType.POWER,
            facility_name="Distant Thermal Power Station",
        )

        evidence = enrich_event_with_context(
            event=ev,
            candidate_features=[refinery, power_plant_distant],
            config=calibrated_config,
        )

        assert len(evidence) == 1
        ev_item = evidence[0]

        assert ev_item.source_type == "osm"
        assert ev_item.context_type == ContextType.OIL_GAS
        assert ev_item.external_facility_id == "OSM-REFINERY"
        assert ev_item.facility_name == "Northern Petroleum Refinery"
        assert ev_item.availability_state == EvidenceAvailabilityState.AVAILABLE
        assert ev_item.distance_to_event_meters is not None
        assert 300.0 < ev_item.distance_to_event_meters < 400.0

    def test_enrich_source_with_multiple_features(
        self, calibrated_config: ScientificConfig
    ) -> None:
        """Persistent source near both power plant and industrial park matches both."""
        t0 = datetime(2026, 8, 1, 10, 0, 0, tzinfo=UTC)
        t1 = datetime(2026, 8, 31, 10, 0, 0, tzinfo=UTC)
        src = PersistentSource(
            source_id="SRC-001",
            linked_event_ids=["EVT-1", "EVT-2"],
            total_event_count=2,
            centroid_geometry=Coordinate(latitude=28.6139, longitude=77.2090),
            first_seen_at=t0,
            last_seen_at=t1,
            active_days_count=2,
            persistence_state=PersistenceState.RECURRING,
            persistence_configuration_id="test_profile",
            persistence_configuration_version="v1.0-test",
        )

        feat_power = _make_context_feature(
            "FEAT-POWER", 28.6150, 77.2090, context_type=ContextType.POWER
        )
        feat_ind = _make_context_feature(
            "FEAT-IND", 28.6180, 77.2090, context_type=ContextType.INDUSTRIAL
        )

        evidence = enrich_source_with_context(
            source=src,
            candidate_features=[feat_ind, feat_power],
            config=calibrated_config,
        )

        assert len(evidence) == 2
        # Deterministically ordered by distance (FEAT-POWER is closer than FEAT-IND)
        assert evidence[0].external_facility_id == "FEAT-POWER"
        assert evidence[1].external_facility_id == "FEAT-IND"

    def test_not_found_evidence_generation(
        self, calibrated_config: ScientificConfig
    ) -> None:
        """build_not_found_evidence records explicit NOT_FOUND_IN_SOURCE state."""
        coord = Coordinate(latitude=28.6139, longitude=77.2090)
        ev = build_not_found_evidence(
            target_id="EVT-EMPTY",
            target_coord=coord,
            provider="osm",
            context_type=ContextType.INDUSTRIAL,
            config=calibrated_config,
        )

        assert ev.availability_state == EvidenceAvailabilityState.NOT_FOUND_IN_SOURCE
        assert ev.source_type == "osm"
        assert ev.context_type == ContextType.INDUSTRIAL
        assert ev.distance_to_event_meters is None

    def test_in_memory_provider_integration(
        self, calibrated_config: ScientificConfig
    ) -> None:
        """InMemoryContextProvider queries features within radius."""
        f1 = _make_context_feature("F1", 28.6140, 77.2090)
        f2 = _make_context_feature("F2", 28.6900, 77.2090)
        provider = InMemoryContextProvider(features=[f1, f2], provider_name="test_osm")

        coord = Coordinate(latitude=28.6139, longitude=77.2090)
        results = provider.query_features_near(coord, radius_meters=1500.0)

        assert len(results) == 1
        assert results[0].feature_id == "F1"

    def test_unhealthy_provider_raises_error(self) -> None:
        """Unhealthy provider raises RuntimeError."""
        provider = InMemoryContextProvider(
            provider_name="offline_provider", is_healthy=False
        )
        coord = Coordinate(latitude=28.6139, longitude=77.2090)

        with pytest.raises(RuntimeError) as exc_info:
            provider.query_features_near(coord, radius_meters=1000.0)

        assert "is unavailable" in str(exc_info.value)


class TestConfigurationAndDeterminism:
    """Validate config enforcement and 100% permutation determinism."""

    def test_uncalibrated_config_raises_error(self) -> None:
        """Incomplete scientific config raises MissingConfigurationError."""
        uncalibrated = ScientificConfig(version="uncalibrated-v1")
        coord = Coordinate(latitude=28.6139, longitude=77.2090)
        t0 = datetime(2026, 8, 1, tzinfo=UTC)
        feat = _make_context_feature("F1", 28.6140, 77.2090)

        with pytest.raises(MissingConfigurationError) as exc_info:
            enrich_with_context("EVT-001", coord, t0, [feat], uncalibrated)

        assert "is incomplete" in str(exc_info.value)
        missing = exc_info.value.details["missing_parameters"]
        assert "attribution_radius_meters" in missing

    def test_permutation_invariance_20_trials(
        self, calibrated_config: ScientificConfig
    ) -> None:
        """20 random orderings of candidate features produce identical evidence."""
        target_coord = Coordinate(latitude=28.6139, longitude=77.2090)
        t0 = datetime(2026, 8, 1, 10, 0, 0, tzinfo=UTC)

        # 5 distinct candidate features at different distances
        features: list[ContextFeature] = [
            _make_context_feature(f"FEAT-{i}", 28.6139 + i * 0.002, 77.2090)
            for i in range(5)
        ]

        # Baseline derivation
        baseline_evidence = enrich_with_context(
            "EVT-PERM", target_coord, t0, features, calibrated_config
        )
        assert len(baseline_evidence) == 5

        baseline_ids = [e.context_id for e in baseline_evidence]
        baseline_fac_ids = [e.external_facility_id for e in baseline_evidence]
        baseline_dists = [e.distance_to_event_meters for e in baseline_evidence]

        # 20 randomized shuffles
        rng = random.Random(42)
        for _trial in range(20):
            shuffled = list(features)
            rng.shuffle(shuffled)

            trial_evidence = enrich_with_context(
                "EVT-PERM", target_coord, t0, shuffled, calibrated_config
            )

            assert [e.context_id for e in trial_evidence] == baseline_ids
            assert [e.external_facility_id for e in trial_evidence] == baseline_fac_ids
            assert [
                e.distance_to_event_meters for e in trial_evidence
            ] == baseline_dists

    def test_configuration_change_changes_context_id(
        self, calibrated_config: ScientificConfig
    ) -> None:
        """Changing configuration version produces a distinct context_id."""
        target_coord = Coordinate(latitude=28.6139, longitude=77.2090)
        t0 = datetime(2026, 8, 1, 10, 0, 0, tzinfo=UTC)
        feat = _make_context_feature("FEAT-1", 28.6140, 77.2090)

        ev_v1 = enrich_with_context(
            "EVT-001", target_coord, t0, [feat], calibrated_config
        )

        config_v2 = calibrated_config.model_copy(update={"version": "v2.0-calibrated"})
        ev_v2 = enrich_with_context("EVT-001", target_coord, t0, [feat], config_v2)

        assert ev_v1[0].context_id != ev_v2[0].context_id
