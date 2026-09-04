"""Unit tests for Phase 3 Atmospheric Dispersion physics and mathematical formulation."""

import pytest

from packages.geospatial.coordinates import project_coordinate
from packages.physics.dispersion import (
    AtmosphericDispersionEngine,
    compute_ground_concentration,
    compute_sigma_y,
    compute_sigma_z,
    estimate_pasquill_stability,
)
from packages.schemas.common import Coordinate
from packages.schemas.dispersion import PasquillStabilityClass
from packages.schemas.weather import (
    AtmosphereData,
    CanonicalWeatherData,
    DataQuality,
    DataStatus,
    WeatherProviderInfo,
    WindState,
    WindVector,
)


def _make_mock_weather(
    speed_ms: float = 5.0,
    direction_deg: float = 270.0,
    cloud_cover_pct: float | None = 20.0,
    temperature_c: float = 25.0,
    data_quality: DataQuality = DataQuality.LIVE,
) -> CanonicalWeatherData:
    """Helper to build canonical weather fixture."""
    is_calm = speed_ms < 0.5
    downwind_deg = (direction_deg + 180.0) % 360.0
    return CanonicalWeatherData(
        location=Coordinate(latitude=22.38, longitude=69.87),
        observed_at="2026-09-04T10:00:00Z",
        retrieved_at="2026-09-04T10:00:00Z",
        data_status=DataStatus.LIVE,
        data_quality=data_quality,
        atmosphere=AtmosphereData(
            temperature_c=temperature_c,
            relative_humidity_pct=50.0,
            cloud_cover_pct=cloud_cover_pct,
        ),
        wind=WindVector(
            speed_ms=speed_ms,
            direction_from_deg=direction_deg,
            direction_from_label="W",
            direction_to_deg=downwind_deg,
            downwind_direction_label="E",
            gust_ms=speed_ms * 1.3,
            u_ms=speed_ms,
            v_ms=0.0,
            is_calm=is_calm,
            wind_state=WindState.CALM if is_calm else WindState.MODERATE,
        ),
        forecast=[],
        provider=WeatherProviderInfo(name="TestMetProvider"),
    )


class TestPasquillStabilityEstimation:
    """Tests for Pasquill-Gifford stability class deduction."""

    def test_strong_daytime_light_wind_is_unstable_a(self) -> None:
        """Strong daytime sun + light wind (<2 m/s) -> Class A."""
        cls, rationale = estimate_pasquill_stability(
            wind_speed_ms=1.5,
            cloud_cover_pct=10.0,
            is_daytime=True,
        )
        assert cls == PasquillStabilityClass.A
        assert "Strong insolation" in rationale

    def test_moderate_daytime_wind_is_unstable_b(self) -> None:
        """Daytime sun + 2.5 m/s wind -> Class B."""
        cls, rationale = estimate_pasquill_stability(
            wind_speed_ms=2.5,
            cloud_cover_pct=20.0,
            is_daytime=True,
        )
        assert cls == PasquillStabilityClass.B

    def test_strong_wind_daytime_is_neutral_d(self) -> None:
        """Strong wind (>= 6 m/s) -> Neutral Class D."""
        cls, _ = estimate_pasquill_stability(
            wind_speed_ms=7.0,
            cloud_cover_pct=10.0,
            is_daytime=True,
        )
        assert cls == PasquillStabilityClass.D

    def test_clear_night_light_wind_is_stable_f(self) -> None:
        """Nighttime + light wind (< 2.5 m/s) + clear skies -> Class F."""
        cls, rationale = estimate_pasquill_stability(
            wind_speed_ms=1.8,
            cloud_cover_pct=15.0,
            is_daytime=False,
        )
        assert cls == PasquillStabilityClass.F
        assert "Radiative cooling" in rationale

    def test_cloudy_night_moderate_wind_is_stable_e(self) -> None:
        """Nighttime + 4.0 m/s wind + clear/moderate clouds -> Class E."""
        cls, _ = estimate_pasquill_stability(
            wind_speed_ms=4.0,
            cloud_cover_pct=20.0,
            is_daytime=False,
        )
        assert cls == PasquillStabilityClass.E

    def test_overcast_day_or_night_is_neutral_d(self) -> None:
        """Overcast skies (>80%) -> Neutral Class D."""
        cls_day, _ = estimate_pasquill_stability(
            wind_speed_ms=3.0,
            cloud_cover_pct=90.0,
            is_daytime=True,
        )
        assert cls_day == PasquillStabilityClass.D

        cls_night, _ = estimate_pasquill_stability(
            wind_speed_ms=3.0,
            cloud_cover_pct=90.0,
            is_daytime=False,
        )
        assert cls_night == PasquillStabilityClass.D

    def test_missing_cloud_cover_defaults_conservatively(self) -> None:
        """Missing cloud cover still evaluates safely without exception."""
        cls, _ = estimate_pasquill_stability(
            wind_speed_ms=4.0,
            cloud_cover_pct=None,
            is_daytime=True,
        )
        assert cls in [PasquillStabilityClass.C, PasquillStabilityClass.D]


class TestBriggsDispersionCoefficients:
    """Tests for Briggs rural dispersion curves sigma_y and sigma_z."""

    def test_sigma_grows_monotonically_with_distance(self) -> None:
        """Dispersion coefficients must expand with downwind distance."""
        distances = [100.0, 500.0, 1000.0, 5000.0, 10000.0]
        stabilities = [
            PasquillStabilityClass.A,
            PasquillStabilityClass.C,
            PasquillStabilityClass.D,
            PasquillStabilityClass.F,
        ]

        for stab in stabilities:
            prev_sy = 0.0
            prev_sz = 0.0
            for d in distances:
                sy = compute_sigma_y(d, stab)
                sz = compute_sigma_z(d, stab)
                assert sy > prev_sy, f"sigma_y did not grow for {stab} at {d}m"
                assert sz >= prev_sz, f"sigma_z did not grow for {stab} at {d}m"
                assert sy >= 1.0
                assert sz >= 1.0
                prev_sy = sy
                prev_sz = sz

    def test_unstable_has_larger_spread_than_stable(self) -> None:
        """Class A (unstable) dispersion coefficients must exceed Class F (stable)."""
        dist = 2000.0
        sy_a = compute_sigma_y(dist, PasquillStabilityClass.A)
        sy_f = compute_sigma_y(dist, PasquillStabilityClass.F)
        sz_a = compute_sigma_z(dist, PasquillStabilityClass.A)
        sz_f = compute_sigma_z(dist, PasquillStabilityClass.F)

        assert sy_a > sy_f
        assert sz_a > sz_f


class TestGaussianGroundConcentration:
    """Tests for ground-level Gaussian plume concentration math."""

    def test_ground_level_release_peaks_at_source_and_decays(self) -> None:
        """Ground release (H=0) concentration decays monotonically along centerline."""
        q = 10.0
        u = 5.0
        stab = PasquillStabilityClass.D
        h = 0.0

        c_100 = compute_ground_concentration(q, u, 100.0, 0.0, h, stab)
        c_500 = compute_ground_concentration(q, u, 500.0, 0.0, h, stab)
        c_2000 = compute_ground_concentration(q, u, 2000.0, 0.0, h, stab)
        c_10000 = compute_ground_concentration(q, u, 10000.0, 0.0, h, stab)

        assert c_100 > c_500 > c_2000 > c_10000
        assert c_10000 > 0.0

    def test_crosswind_gaussian_decay(self) -> None:
        """Off-centerline concentration decays symmetrically with crosswind distance y."""
        q = 10.0
        u = 4.0
        x = 1000.0
        h = 10.0
        stab = PasquillStabilityClass.C

        c_center = compute_ground_concentration(q, u, x, 0.0, h, stab)
        c_y50_pos = compute_ground_concentration(q, u, x, 50.0, h, stab)
        c_y50_neg = compute_ground_concentration(q, u, x, -50.0, h, stab)
        c_y200 = compute_ground_concentration(q, u, x, 200.0, h, stab)

        assert c_center > c_y50_pos
        assert pytest.approx(c_y50_pos, rel=1e-5) == c_y50_neg
        assert c_y50_pos > c_y200

    def test_calm_effective_velocity_clamp(self) -> None:
        """Wind speed < 0.5 m/s is clamped to 0.5 m/s preventing zero division."""
        c_calm = compute_ground_concentration(10.0, 0.0, 500.0, 0.0, 0.0, PasquillStabilityClass.D)
        c_floor = compute_ground_concentration(10.0, 0.5, 500.0, 0.0, 0.0, PasquillStabilityClass.D)
        assert pytest.approx(c_calm, rel=1e-5) == c_floor


class TestAtmosphericDispersionEngineScenarios:
    """Integration test suite covering canonical physical scenarios A through D."""

    def test_scenario_a_strong_wind_narrow_corridor(self) -> None:
        """Scenario A: High wind (10 m/s) produces narrow hazard corridor oriented downwind."""
        weather = _make_mock_weather(speed_ms=10.0, direction_deg=270.0)  # Wind FROM West -> downwind to East (90 deg)
        result = AtmosphericDispersionEngine.evaluate_dispersion(
            weather=weather,
            latitude=22.38,
            longitude=69.87,
            frp_mw=30.0,
            is_daytime=True,
        )

        assert result.dispersion.plume_angle_deg == pytest.approx(90.0)
        assert not result.dispersion.calm_stagnation_flag
        assert result.dispersion.stability_class in [PasquillStabilityClass.C, PasquillStabilityClass.D]
        assert len(result.trajectory) > 5
        assert result.model_confidence == "HIGH"

        # Trajectory points should move eastward (increasing longitude)
        first_pt = result.trajectory[0].centerline_point
        last_pt = result.trajectory[-1].centerline_point
        assert last_pt.longitude > first_pt.longitude
        assert pytest.approx(last_pt.latitude, rel=1e-3) == first_pt.latitude

    def test_scenario_b_moderate_wind(self) -> None:
        """Scenario B: Moderate wind (4 m/s) produces stable downwind progression."""
        weather = _make_mock_weather(speed_ms=4.0, direction_deg=180.0)  # Wind FROM South -> downwind to North (0 deg)
        result = AtmosphericDispersionEngine.evaluate_dispersion(
            weather=weather,
            latitude=22.38,
            longitude=69.87,
            frp_mw=15.0,
            is_daytime=True,
        )

        assert result.dispersion.plume_angle_deg == pytest.approx(0.0)
        first_pt = result.trajectory[0].centerline_point
        last_pt = result.trajectory[-1].centerline_point
        assert last_pt.latitude > first_pt.latitude  # Traveling North

    def test_scenario_c_calm_wind_stagnation(self) -> None:
        """Scenario C: Calm wind (<0.5 m/s) triggers stagnation broadening and degraded confidence."""
        weather = _make_mock_weather(speed_ms=0.2, direction_deg=0.0)
        result = AtmosphericDispersionEngine.evaluate_dispersion(
            weather=weather,
            latitude=22.38,
            longitude=69.87,
            frp_mw=20.0,
            is_daytime=True,
        )

        assert result.dispersion.calm_stagnation_flag is True
        assert result.model_confidence == "DEGRADED_CALM"
        assert result.dispersion.max_hazard_width_km > 0.5

    def test_scenario_d_high_frp_buoyant_plume(self) -> None:
        """Scenario D: High FRP (150 MW) yields elevated effective release height and high source strength."""
        weather = _make_mock_weather(speed_ms=6.0, direction_deg=90.0)
        result = AtmosphericDispersionEngine.evaluate_dispersion(
            weather=weather,
            latitude=22.38,
            longitude=69.87,
            frp_mw=150.0,
            is_daytime=True,
        )

        assert result.dispersion.effective_release_height_m > 30.0
        assert result.dispersion.source_strength_proxy == pytest.approx(150.0 ** 0.5, rel=1e-3)

    def test_geodesic_lateral_boundary_symmetry(self) -> None:
        """Left and right hazard boundary coordinates must be spatially distinct and symmetric."""
        weather = _make_mock_weather(speed_ms=5.0, direction_deg=270.0)
        result = AtmosphericDispersionEngine.evaluate_dispersion(
            weather=weather,
            latitude=22.38,
            longitude=69.87,
            frp_mw=50.0,
        )

        for pt in result.trajectory[1:]:
            assert pt.left_boundary_point != pt.centerline_point
            assert pt.right_boundary_point != pt.centerline_point
            assert pt.left_boundary_point != pt.right_boundary_point
            assert pt.lateral_width_km > 0.0
            assert 0.0 <= pt.relative_concentration <= 1.0
