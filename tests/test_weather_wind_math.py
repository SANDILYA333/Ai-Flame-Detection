"""Tests for meteorological wind conversions, downwind derivation, cardinal mapping, and calm wind states."""

import math
import pytest

from packages.physics.wind import (
    build_wind_vector,
    classify_wind_state,
    compute_downwind_direction,
    compute_wind_vector_components,
    degrees_to_cardinal,
    normalize_degrees,
)
from packages.schemas.weather import WindState


class TestWindConversions:
    """Test angular normalization and downwind direction calculations."""

    @pytest.mark.parametrize(
        "angle,expected",
        [
            (0.0, 0.0),
            (360.0, 0.0),
            (720.0, 0.0),
            (45.0, 45.0),
            (225.0, 225.0),
            (-45.0, 315.0),
            (-180.0, 180.0),
            (359.99, 359.99),
        ],
    )
    def test_normalize_degrees(self, angle: float, expected: float) -> None:
        assert normalize_degrees(angle) == pytest.approx(expected, abs=1e-5)

    def test_normalize_degrees_invalid(self) -> None:
        with pytest.raises(ValueError, match="finite number"):
            normalize_degrees(float("nan"))
        with pytest.raises(ValueError, match="finite number"):
            normalize_degrees(float("inf"))

    @pytest.mark.parametrize(
        "dir_from,expected_dir_to",
        [
            (0.0, 180.0),      # North wind -> blows South
            (45.0, 225.0),     # NE wind -> blows SW
            (90.0, 270.0),     # East wind -> blows West
            (180.0, 0.0),      # South wind -> blows North
            (225.0, 45.0),     # SW wind -> blows NE
            (270.0, 90.0),     # West wind -> blows East
            (315.0, 135.0),    # NW wind -> blows SE
            (359.0, 179.0),    # Almost North
            (360.0, 180.0),    # 360° wraps to 0° -> blows South
        ],
    )
    def test_downwind_direction(self, dir_from: float, expected_dir_to: float) -> None:
        assert compute_downwind_direction(dir_from) == pytest.approx(expected_dir_to, abs=1e-5)


class TestCardinalDirections:
    """Test 16-point compass conversions and boundary conditions."""

    @pytest.mark.parametrize(
        "degrees,expected_cardinal",
        [
            (0.0, "N"),
            (11.24, "N"),
            (11.26, "NNE"),
            (22.5, "NNE"),
            (45.0, "NE"),
            (67.5, "ENE"),
            (90.0, "E"),
            (112.5, "ESE"),
            (135.0, "SE"),
            (157.5, "SSE"),
            (180.0, "S"),
            (202.5, "SSW"),
            (225.0, "SW"),
            (247.5, "WSW"),
            (270.0, "W"),
            (292.5, "WNW"),
            (315.0, "NW"),
            (337.5, "NNW"),
            (350.0, "N"),
            (359.9, "N"),
            (360.0, "N"),
        ],
    )
    def test_16_point_cardinal_bearings(self, degrees: float, expected_cardinal: str) -> None:
        assert degrees_to_cardinal(degrees, points=16) == expected_cardinal

    def test_8_point_cardinal_bearings(self) -> None:
        assert degrees_to_cardinal(0.0, points=8) == "N"
        assert degrees_to_cardinal(45.0, points=8) == "NE"
        assert degrees_to_cardinal(90.0, points=8) == "E"
        assert degrees_to_cardinal(180.0, points=8) == "S"
        assert degrees_to_cardinal(225.0, points=8) == "SW"
        assert degrees_to_cardinal(270.0, points=8) == "W"


class TestWindIntensityAndCalmState:
    """Test calm wind detection and Beaufort state classifications."""

    @pytest.mark.parametrize(
        "speed_ms,expected_state",
        [
            (0.0, WindState.CALM),
            (0.4, WindState.CALM),
            (0.5, WindState.LIGHT),
            (2.5, WindState.LIGHT),
            (5.0, WindState.MODERATE),
            (10.0, WindState.FRESH),
            (15.0, WindState.STRONG),
            (25.0, WindState.GALE),
        ],
    )
    def test_classify_wind_state(self, speed_ms: float, expected_state: WindState) -> None:
        assert classify_wind_state(speed_ms) == expected_state


class TestWindVectorComponents:
    """Test orthogonal u (zonal) and v (meridional) component calculations."""

    def test_cardinal_north_wind(self) -> None:
        # Wind blowing FROM North (0°) moves South (v < 0, u = 0)
        u, v = compute_wind_vector_components(10.0, 0.0)
        assert u == 0.0
        assert v == -10.0

    def test_cardinal_east_wind(self) -> None:
        # Wind blowing FROM East (90°) moves West (u < 0, v = 0)
        u, v = compute_wind_vector_components(10.0, 90.0)
        assert u == -10.0
        assert v == 0.0

    def test_cardinal_south_wind(self) -> None:
        # Wind blowing FROM South (180°) moves North (v > 0, u = 0)
        u, v = compute_wind_vector_components(10.0, 180.0)
        assert u == 0.0
        assert v == 10.0

    def test_cardinal_west_wind(self) -> None:
        # Wind blowing FROM West (270°) moves East (u > 0, v = 0)
        u, v = compute_wind_vector_components(10.0, 270.0)
        assert u == 10.0
        assert v == 0.0

    def test_intercardinal_southwest_wind(self) -> None:
        # Wind blowing FROM SW (225°) moves NE (u > 0, v > 0)
        speed = 10.0
        u, v = compute_wind_vector_components(speed, 225.0)
        expected = round(speed * (math.sqrt(2) / 2), 4)
        assert u == pytest.approx(expected, abs=1e-4)
        assert v == pytest.approx(expected, abs=1e-4)

    def test_intercardinal_northwest_wind(self) -> None:
        # Wind blowing FROM NW (315°) moves SE (u > 0, v < 0)
        speed = 10.0
        u, v = compute_wind_vector_components(speed, 315.0)
        expected = round(speed * (math.sqrt(2) / 2), 4)
        assert u == pytest.approx(expected, abs=1e-4)
        assert v == pytest.approx(-expected, abs=1e-4)

    def test_zero_wind_speed(self) -> None:
        u, v = compute_wind_vector_components(0.0, 120.0)
        assert u == 0.0
        assert v == 0.0

    def test_invalid_speed(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            compute_wind_vector_components(-5.0, 90.0)
        with pytest.raises(ValueError, match="finite"):
            compute_wind_vector_components(float("nan"), 90.0)


class TestBuildWindVector:
    """Test domain object builder with schema validation and Phase 2 fields."""

    def test_build_wind_vector_success(self) -> None:
        vec = build_wind_vector(speed_ms=8.4, direction_from_deg=225.0, gust_ms=11.2)
        assert vec.speed_ms == 8.4
        assert vec.direction_from_deg == 225.0
        assert vec.direction_from_label == "SW"
        assert vec.direction_to_deg == 45.0
        assert vec.downwind_direction_label == "NE"
        assert vec.gust_ms == 11.2
        assert vec.is_calm is False
        assert vec.wind_state == WindState.FRESH
        assert vec.u_ms > 0
        assert vec.v_ms > 0

    def test_build_wind_vector_calm(self) -> None:
        vec = build_wind_vector(speed_ms=0.2, direction_from_deg=90.0)
        assert vec.is_calm is True
        assert vec.wind_state == WindState.CALM
        assert vec.direction_from_label == "E"
        assert vec.downwind_direction_label == "W"

    def test_build_wind_vector_without_gust(self) -> None:
        vec = build_wind_vector(speed_ms=5.0, direction_from_deg=0.0)
        assert vec.gust_ms is None
        assert vec.direction_from_label == "N"
        assert vec.direction_to_deg == 180.0
        assert vec.downwind_direction_label == "S"
        assert vec.is_calm is False
        assert vec.wind_state == WindState.MODERATE
        assert vec.u_ms == 0.0
        assert vec.v_ms == -5.0
