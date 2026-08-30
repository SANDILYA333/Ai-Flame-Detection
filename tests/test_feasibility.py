"""Unit, adversarial, and determinism tests for DATA-001 feasibility."""

import random
from datetime import UTC, datetime, timedelta

import pytest

from packages.config.scientific import ScientificConfig
from packages.context.models import ContextFeature
from packages.errors import MissingConfigurationError
from packages.feasibility import (
    JAMNAGAR_KUTCH,
    PROVISIONAL_CANDIDATE_AREAS,
    CandidateReferencePoint,
    FeasibilityLevel,
    StudyAreaRole,
    analyze_context_feasibility,
    analyze_derivation_feasibility,
    analyze_firms_feasibility,
    analyze_reference_feasibility,
    evaluate_study_area_feasibility,
    generate_markdown_feasibility_report,
    get_candidate_study_area,
    run_comparative_feasibility_harness,
)
from packages.schemas.common import Coordinate
from packages.schemas.detection import Detection
from packages.schemas.enums import ContextType, DayNight


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
        persistence_min_observations=3,
        attribution_radius_meters=1500.0,
        attribution_confidence_threshold=0.7,
        minimum_event_confidence=0.5,
        abstention_confidence_threshold=0.4,
    )


def _make_detection(
    detection_id: str,
    lat: float,
    lon: float,
    acquired_at: datetime | None = None,
    frp_mw: float | None = 20.0,
    satellite: str = "NOAA-20",
    instrument: str = "VIIRS",
    day_night: DayNight = DayNight.NIGHT,
) -> Detection:
    """Helper to create a canonical Detection domain object."""
    t = acquired_at or datetime(2026, 8, 1, 10, 0, 0, tzinfo=UTC)
    return Detection(
        detection_id=detection_id,
        source="firms",
        source_snapshot_id="SNAP-001",
        acquired_at=t,
        geometry=Coordinate(latitude=lat, longitude=lon),
        satellite=satellite,
        instrument=instrument,
        product_type="nrt",
        product_version="v2.0",
        raw_hash=f"hash_{detection_id}",
        frp_mw=frp_mw,
        brightness_ti4_k=340.0,
        brightness_ti5_k=295.0,
        confidence="nominal",
        scan_km=0.375,
        track_km=0.375,
        day_night=day_night,
    )


def _make_context_feature(
    feature_id: str,
    lat: float,
    lon: float,
    context_type: ContextType = ContextType.OIL_GAS,
    facility_name: str = "Test Petrochemical Complex",
) -> ContextFeature:
    """Helper to create a canonical ContextFeature."""
    return ContextFeature(
        feature_id=feature_id,
        provider="osm",
        dataset_name="osm_polygons",
        dataset_version="2026-08-01",
        context_type=context_type,
        geometry=Coordinate(latitude=lat, longitude=lon),
        facility_name=facility_name,
    )


def _make_reference_point(
    point_id: str,
    lat: float,
    lon: float,
    source_name: str = "GGIT_FLARING",
    tier: str = "TIER_A",
    facility_name: str = "Refinery Flare Stack",
) -> CandidateReferencePoint:
    """Helper to create a candidate reference ground-truth point."""
    return CandidateReferencePoint(
        point_id=point_id,
        source_name=source_name,
        tier=tier,
        geometry=Coordinate(latitude=lat, longitude=lon),
        facility_name=facility_name,
    )


class TestCandidateStudyAreas:
    """Validate provisional candidate Indian study area definitions."""

    def test_provisional_candidates_completeness(self) -> None:
        """All provisional candidate regions are properly formed."""
        assert len(PROVISIONAL_CANDIDATE_AREAS) == 4
        for area in PROVISIONAL_CANDIDATE_AREAS:
            assert area.is_provisional is True
            assert area.approx_area_sqkm > 1000.0
            assert area.bounding_box.min_latitude < area.bounding_box.max_latitude
            assert area.bounding_box.min_longitude < area.bounding_box.max_longitude
            assert len(area.scientific_rationale) > 20

    def test_get_candidate_by_id(self) -> None:
        """Retrieve candidate study areas by area_id."""
        area = get_candidate_study_area("jamnagar_kutch")
        assert area.name == JAMNAGAR_KUTCH.name
        assert area.state == "Gujarat"

    def test_get_invalid_candidate_raises_key_error(self) -> None:
        """Querying unknown study area raises KeyError."""
        with pytest.raises(KeyError) as exc_info:
            get_candidate_study_area("non_existent_area")
        assert "not found" in str(exc_info.value)


class TestFirmsFeasibilityAnalyzer:
    """Validate FIRMS observation volume, temporal, and spatial metric analysis."""

    def test_empty_detections_returns_zero_metrics(self) -> None:
        """Empty detection set produces clean zeroed metrics without crashing."""
        metrics = analyze_firms_feasibility(
            detections=[],
            bounds=JAMNAGAR_KUTCH.bounding_box,
            approx_area_sqkm=JAMNAGAR_KUTCH.approx_area_sqkm,
        )
        assert metrics.total_detections == 0
        assert metrics.unique_observation_dates == 0
        assert metrics.temporal_span_days == 0.0
        assert metrics.frp_mean_mw is None
        assert metrics.spatial_density_per_sqkm == 0.0

    def test_spatial_filtering_within_bounds(self) -> None:
        """Only detections strictly inside candidate bounds are included."""
        # 2 inside Jamnagar (22.4, 70.0), 1 outside (Singrauli 24.1, 82.5)
        d1 = _make_detection("D1", 22.45, 70.05)
        d2 = _make_detection("D2", 22.46, 70.06)
        d_out = _make_detection("D_OUT", 24.10, 82.50)

        metrics = analyze_firms_feasibility(
            detections=[d1, d2, d_out],
            bounds=JAMNAGAR_KUTCH.bounding_box,
            approx_area_sqkm=JAMNAGAR_KUTCH.approx_area_sqkm,
        )
        assert metrics.total_detections == 2
        assert "NOAA-20_VIIRS" in metrics.sensor_breakdown
        assert metrics.sensor_breakdown["NOAA-20_VIIRS"] == 2

    def test_temporal_span_and_frp_statistics(self) -> None:
        """Computes temporal span, unique dates, and FRP statistics correctly."""
        t0 = datetime(2026, 8, 1, 10, 0, 0, tzinfo=UTC)
        t1 = datetime(2026, 8, 11, 10, 0, 0, tzinfo=UTC)

        d1 = _make_detection("D1", 22.45, 70.05, acquired_at=t0, frp_mw=10.0)
        d2 = _make_detection("D2", 22.45, 70.05, acquired_at=t1, frp_mw=30.0)
        d3 = _make_detection("D3", 22.45, 70.05, acquired_at=t1, frp_mw=None)

        metrics = analyze_firms_feasibility(
            detections=[d1, d2, d3],
            bounds=JAMNAGAR_KUTCH.bounding_box,
            approx_area_sqkm=10000.0,
        )
        assert metrics.total_detections == 3
        assert metrics.unique_observation_dates == 2
        assert metrics.temporal_span_days == 10.0
        assert metrics.frp_mean_mw == 20.0
        assert metrics.frp_max_mw == 30.0
        assert metrics.missing_frp_count == 1


class TestDerivationAndContextFeasibility:
    """Validate Phase 3 derivation and contextual infrastructure feasibility."""

    def test_derivation_feasibility_with_persistent_source(
        self, calibrated_config: ScientificConfig
    ) -> None:
        """Multiple detections on different dates form persistent source candidates."""
        detections: list[Detection] = []
        base_t = datetime(2026, 7, 1, 10, 0, 0, tzinfo=UTC)
        # 5 detections over 32 days at same location (exceeding 30-day threshold)
        for day in range(5):
            t = base_t + timedelta(days=day * 8)
            detections.append(_make_detection(f"D-{day}", 22.45, 70.05, acquired_at=t))

        metrics = analyze_derivation_feasibility(
            detections=detections,
            config=calibrated_config,
            approx_area_sqkm=10000.0,
        )
        assert metrics.candidate_events_count == 5
        assert metrics.candidate_sources_count == 1
        assert "persistent" in metrics.persistence_state_breakdown

    def test_context_feasibility_analysis(
        self, calibrated_config: ScientificConfig
    ) -> None:
        """Measures contextual infrastructure features and event coverage ratio."""
        t0 = datetime(2026, 8, 1, 10, 0, 0, tzinfo=UTC)
        d1 = _make_detection("D1", 22.450, 70.050, acquired_at=t0)
        d2 = _make_detection("D2", 22.800, 70.500, acquired_at=t0)

        # Context feature near D1 (200m away), none near D2
        feat = _make_context_feature("F1", 22.451, 70.051, ContextType.OIL_GAS)

        from packages.events.service import derive_thermal_events

        events = derive_thermal_events([d1, d2], calibrated_config)
        assert len(events) == 2

        ctx_metrics = analyze_context_feasibility(
            events=events,
            context_features=[feat],
            bounds=JAMNAGAR_KUTCH.bounding_box,
            config=calibrated_config,
        )

        assert ctx_metrics.total_context_features == 1
        assert ctx_metrics.events_with_context_count == 1
        assert ctx_metrics.context_coverage_ratio == 0.5

    def test_reference_feasibility_analysis(
        self, calibrated_config: ScientificConfig
    ) -> None:
        """Measures candidate ground-truth reference points and event overlap."""
        t0 = datetime(2026, 8, 1, 10, 0, 0, tzinfo=UTC)
        d1 = _make_detection("D1", 22.450, 70.050, acquired_at=t0)

        ref_pt = _make_reference_point("REF-1", 22.451, 70.051, tier="TIER_A")

        from packages.events.service import derive_thermal_events

        events = derive_thermal_events([d1], calibrated_config)

        ref_metrics = analyze_reference_feasibility(
            events=events,
            reference_points=[ref_pt],
            bounds=JAMNAGAR_KUTCH.bounding_box,
            config=calibrated_config,
        )

        assert ref_metrics.candidate_reference_points == 1
        assert ref_metrics.events_with_reference_count == 1
        assert ref_metrics.reference_coverage_ratio == 1.0
        assert ref_metrics.reference_by_tier["TIER_A"] == 1


class TestFeasibilityEvaluatorAndHarness:
    """Validate comprehensive assessment, comparative ranking, and report generation."""

    def test_evaluate_study_area_feasibility(
        self, calibrated_config: ScientificConfig
    ) -> None:
        """Complete evaluation of candidate study area."""
        # Create robust detection history in Jamnagar
        base_t = datetime(2026, 7, 1, 10, 0, 0, tzinfo=UTC)
        detections = [
            _make_detection(
                f"D-{i}",
                22.45,
                70.05,
                acquired_at=base_t + timedelta(days=i * 2),
            )
            for i in range(12)
        ]
        context_features = [
            _make_context_feature("F1", 22.451, 70.051, ContextType.OIL_GAS),
            _make_context_feature("F2", 22.500, 70.100, ContextType.POWER),
        ]
        reference_points = [_make_reference_point("R1", 22.451, 70.051, tier="TIER_A")]

        assessment = evaluate_study_area_feasibility(
            study_area=JAMNAGAR_KUTCH,
            detections=detections,
            context_features=context_features,
            reference_points=reference_points,
            config=calibrated_config,
        )

        assert assessment.study_area.area_id == "jamnagar_kutch"
        assert assessment.data_adequacy_score > 0.60
        assert assessment.overall_feasibility in (
            FeasibilityLevel.HIGH_FEASIBILITY,
            FeasibilityLevel.MODERATE_FEASIBILITY,
        )
        assert assessment.recommended_role == StudyAreaRole.PRIMARY_BENCHMARK_CANDIDATE
        assert len(assessment.key_strengths) > 0

    def test_run_comparative_feasibility_harness(
        self, calibrated_config: ScientificConfig
    ) -> None:
        """Runs comparative harness across multiple provisional candidate regions."""
        base_t = datetime(2026, 7, 1, 10, 0, 0, tzinfo=UTC)
        # Heavy detections in Jamnagar, sparse in Singrauli, none in Punjab
        detections = [
            _make_detection(
                f"D-JAM-{i}",
                22.45,
                70.05,
                acquired_at=base_t + timedelta(days=i),
            )
            for i in range(20)
        ] + [_make_detection("D-SING-1", 24.10, 82.50, acquired_at=base_t)]

        context_features = [
            _make_context_feature("F-JAM-1", 22.451, 70.051, ContextType.OIL_GAS)
        ]
        reference_points = [
            _make_reference_point("R-JAM-1", 22.451, 70.051, tier="TIER_A")
        ]

        report = run_comparative_feasibility_harness(
            study_areas=PROVISIONAL_CANDIDATE_AREAS,
            detections=detections,
            context_features=context_features,
            reference_points=reference_points,
            config=calibrated_config,
        )

        assert len(report.candidate_assessments) == 4
        # Jamnagar has highest data adequacy
        assert report.comparative_ranking[0] == "jamnagar_kutch"

        # Generate human-readable Markdown report
        md = generate_markdown_feasibility_report(report)
        assert "# DATA-001 — Study-Area Feasibility Assessment Report" in md
        assert "## 1. Measured Findings" in md
        assert "## 2. Comparative Candidate Ranking" in md
        assert "## 4. Inferred Insights" in md
        assert "## 5. Evidence-Based Recommendations" in md
        assert "## 6. Open Questions for Subsequent Gates" in md

    def test_uncalibrated_config_raises_error(self) -> None:
        """Incomplete scientific config raises MissingConfigurationError."""
        uncalibrated = ScientificConfig(version="uncalibrated-v1")

        with pytest.raises(MissingConfigurationError) as exc_info:
            evaluate_study_area_feasibility(
                study_area=JAMNAGAR_KUTCH,
                detections=[],
                context_features=[],
                reference_points=[],
                config=uncalibrated,
            )
        assert "is incomplete" in str(exc_info.value)

    def test_permutation_invariance_20_trials(
        self, calibrated_config: ScientificConfig
    ) -> None:
        """20 random orderings produce identical scores and rankings."""
        base_t = datetime(2026, 7, 1, 10, 0, 0, tzinfo=UTC)
        detections = [
            _make_detection(
                f"D-JAM-{i}",
                22.45,
                70.05,
                acquired_at=base_t + timedelta(days=i),
            )
            for i in range(10)
        ]

        baseline = run_comparative_feasibility_harness(
            study_areas=PROVISIONAL_CANDIDATE_AREAS,
            detections=detections,
            context_features=[],
            reference_points=[],
            config=calibrated_config,
        )
        baseline_ranking = list(baseline.comparative_ranking)

        rng = random.Random(42)
        for _trial in range(20):
            shuffled_areas = list(PROVISIONAL_CANDIDATE_AREAS)
            rng.shuffle(shuffled_areas)

            trial_report = run_comparative_feasibility_harness(
                study_areas=shuffled_areas,
                detections=detections,
                context_features=[],
                reference_points=[],
                config=calibrated_config,
            )

            assert trial_report.comparative_ranking == baseline_ranking
