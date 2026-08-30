"""Unit tests for packages/geospatial calculations and distance metrics."""

import math
from datetime import UTC, datetime

import pytest

from packages.errors import InvalidCoordinateError
from packages.geospatial import (
    WGS84_MEAN_EARTH_RADIUS_METERS,
    calculate_bounding_box,
    calculate_spatial_centroid,
    format_wkt_point,
    haversine_distance_meters,
    is_spatiotemporally_proximate,
    parse_wkt_point,
    validate_wgs84_coordinates,
)


class TestCoordinateValidation:
    """Validate WGS-84 coordinate validation and bounds enforcement."""

    def test_valid_coordinates(self) -> None:
        """Valid latitude and longitude in range pass without modification."""
        lat, lon = validate_wgs84_coordinates(28.6139, 77.2090)
        assert lat == 28.6139
        assert lon == 77.2090

        # Boundary checks
        assert validate_wgs84_coordinates(90.0, 180.0) == (90.0, 180.0)
        assert validate_wgs84_coordinates(-90.0, -180.0) == (-90.0, -180.0)
        assert validate_wgs84_coordinates(0.0, 0.0) == (0.0, 0.0)

    def test_invalid_latitude_bounds(self) -> None:
        """Latitude outside [-90.0, 90.0] raises InvalidCoordinateError."""
        with pytest.raises(InvalidCoordinateError) as exc_info:
            validate_wgs84_coordinates(90.0001, 77.0)
        assert "Latitude must be between -90.0 and 90.0" in str(exc_info.value)

        with pytest.raises(InvalidCoordinateError):
            validate_wgs84_coordinates(-90.1, 77.0)

    def test_invalid_longitude_bounds(self) -> None:
        """Longitude outside [-180.0, 180.0] raises InvalidCoordinateError."""
        with pytest.raises(InvalidCoordinateError) as exc_info:
            validate_wgs84_coordinates(28.0, 180.0001)
        assert "Longitude must be between -180.0 and 180.0" in str(exc_info.value)

        with pytest.raises(InvalidCoordinateError):
            validate_wgs84_coordinates(28.0, -180.01)

    def test_non_finite_coordinates(self) -> None:
        """NaN and infinite coordinates raise InvalidCoordinateError."""
        with pytest.raises(InvalidCoordinateError):
            validate_wgs84_coordinates(float("nan"), 77.0)

        with pytest.raises(InvalidCoordinateError):
            validate_wgs84_coordinates(28.0, float("inf"))

        with pytest.raises(InvalidCoordinateError):
            validate_wgs84_coordinates(float("-inf"), 0.0)


class TestWktFormattingAndParsing:
    """Validate WKT POINT(longitude latitude) compliance with OGC standard."""

    def test_format_wkt_point(self) -> None:
        """Format produces POINT(lon lat) with longitude first."""
        wkt = format_wkt_point(latitude=28.6139, longitude=77.2090)
        assert wkt == "POINT(77.209 28.6139)"

    def test_parse_wkt_point(self) -> None:
        """Parsing extracts (latitude, longitude) correctly."""
        lat, lon = parse_wkt_point("POINT(77.209 28.6139)")
        assert math.isclose(lat, 28.6139, rel_tol=1e-5)
        assert math.isclose(lon, 77.209, rel_tol=1e-5)

    def test_parse_wkt_point_with_spaces_and_negatives(self) -> None:
        """Parser handles variable whitespace and negative numbers."""
        lat, lon = parse_wkt_point("  POINT ( -73.9851   40.7488 )  ")
        assert math.isclose(lat, 40.7488, rel_tol=1e-5)
        assert math.isclose(lon, -73.9851, rel_tol=1e-5)

    def test_parse_malformed_wkt(self) -> None:
        """Malformed WKT strings raise InvalidCoordinateError."""
        with pytest.raises(InvalidCoordinateError):
            parse_wkt_point("POLYGON((0 0, 0 1, 1 1, 0 0))")

        with pytest.raises(InvalidCoordinateError):
            parse_wkt_point("POINT(abc def)")

        with pytest.raises(InvalidCoordinateError):
            parse_wkt_point("POINT()")


class TestGeodesicDistance:
    """Validate Haversine distance calculations against physical benchmarks."""

    def test_distance_identical_points(self) -> None:
        """Distance between identical coordinates is exactly 0.0 meters."""
        dist = haversine_distance_meters(28.6139, 77.2090, 28.6139, 77.2090)
        assert dist == 0.0

    def test_delhi_to_mumbai_benchmark(self) -> None:
        """Delhi to Mumbai great-circle distance is approximately 1,148 km."""
        delhi_lat, delhi_lon = 28.6139, 77.2090
        mumbai_lat, mumbai_lon = 19.0760, 72.8777

        distance_meters = haversine_distance_meters(
            delhi_lat, delhi_lon, mumbai_lat, mumbai_lon
        )
        distance_km = distance_meters / 1000.0

        # Physical distance is ~1148 km (+/- 1% tolerance for sphere vs ellipsoid)
        assert 1135.0 < distance_km < 1160.0

    def test_antipodal_points_distance(self) -> None:
        """Distance between antipodal points equals half Earth circumference."""
        dist = haversine_distance_meters(0.0, 0.0, 0.0, 180.0)
        half_circumference = math.pi * WGS84_MEAN_EARTH_RADIUS_METERS
        assert math.isclose(dist, half_circumference, rel_tol=1e-4)

    def test_degree_convergence_distortion_proof(self) -> None:
        """Demonstrate why Euclidean degree distance is invalid.

        At the equator, 1 degree longitude is ~111.19 km.
        At 60 degrees north, 1 degree longitude is ~55.60 km (cos(60) = 0.5).
        """
        dist_equator = haversine_distance_meters(0.0, 0.0, 0.0, 1.0)
        dist_60_north = haversine_distance_meters(60.0, 0.0, 60.0, 1.0)

        assert 110_000.0 < dist_equator < 112_000.0
        assert 55_000.0 < dist_60_north < 56_000.0
        # High latitude 1 degree is roughly half the physical distance
        assert math.isclose(dist_60_north / dist_equator, 0.5, rel_tol=1e-2)


class TestSpatiotemporalProximity:
    """Validate joint spatiotemporal threshold evaluation."""

    def test_proximate_both_space_and_time(self) -> None:
        """Within spatial radius and temporal window returns True."""
        t1 = datetime(2026, 8, 29, 10, 0, 0, tzinfo=UTC)
        t2 = datetime(2026, 8, 29, 11, 30, 0, tzinfo=UTC)  # 1.5 hours diff

        # Points ~500 meters apart
        lat1, lon1 = 28.6139, 77.2090
        lat2, lon2 = 28.6184, 77.2090

        assert is_spatiotemporally_proximate(
            lat1,
            lon1,
            t1,
            lat2,
            lon2,
            t2,
            max_distance_meters=1000.0,
            max_time_difference_hours=2.0,
        )

    def test_outside_temporal_window_returns_false(self) -> None:
        """Nearby in space but outside time window returns False."""
        t1 = datetime(2026, 8, 29, 10, 0, 0, tzinfo=UTC)
        t2 = datetime(2026, 8, 29, 15, 0, 0, tzinfo=UTC)  # 5 hours diff

        lat1, lon1 = 28.6139, 77.2090
        lat2, lon2 = 28.6140, 77.2090

        assert not is_spatiotemporally_proximate(
            lat1,
            lon1,
            t1,
            lat2,
            lon2,
            t2,
            max_distance_meters=1000.0,
            max_time_difference_hours=2.0,
        )

    def test_outside_spatial_radius_returns_false(self) -> None:
        """Same time but outside spatial radius returns False."""
        t1 = datetime(2026, 8, 29, 10, 0, 0, tzinfo=UTC)
        t2 = datetime(2026, 8, 29, 10, 5, 0, tzinfo=UTC)

        # ~1148 km apart (Delhi to Mumbai)
        assert not is_spatiotemporally_proximate(
            28.6139,
            77.2090,
            t1,
            19.0760,
            72.8777,
            t2,
            max_distance_meters=5000.0,
            max_time_difference_hours=1.0,
        )

    def test_negative_thresholds_raise_value_error(self) -> None:
        """Negative distance or time thresholds raise ValueError."""
        t = datetime(2026, 8, 29, 10, 0, 0, tzinfo=UTC)
        with pytest.raises(ValueError):
            is_spatiotemporally_proximate(
                28.0,
                77.0,
                t,
                28.0,
                77.0,
                t,
                max_distance_meters=-10.0,
                max_time_difference_hours=1.0,
            )

        with pytest.raises(ValueError):
            is_spatiotemporally_proximate(
                28.0,
                77.0,
                t,
                28.0,
                77.0,
                t,
                max_distance_meters=100.0,
                max_time_difference_hours=-1.0,
            )


class TestSpatialCentroidAndBoundingBox:
    """Validate spatial envelope and centroid calculations."""

    def test_single_point_centroid_and_bbox(self) -> None:
        """Single point produces identical centroid and zero-area bbox."""
        points = [(28.6139, 77.2090)]
        centroid_lat, centroid_lon = calculate_spatial_centroid(points)
        assert math.isclose(centroid_lat, 28.6139)
        assert math.isclose(centroid_lon, 77.2090)

        bbox = calculate_bounding_box(points)
        assert bbox.min_latitude == 28.6139
        assert bbox.max_latitude == 28.6139
        assert bbox.min_longitude == 77.2090
        assert bbox.max_longitude == 77.2090

    def test_multi_point_cluster(self) -> None:
        """Multiple points compute mean centroid and enclosing bounding box."""
        points = [
            (28.0, 77.0),
            (28.0, 78.0),
            (29.0, 77.0),
            (29.0, 78.0),
        ]
        centroid_lat, centroid_lon = calculate_spatial_centroid(points)
        assert math.isclose(centroid_lat, 28.5, rel_tol=1e-3)
        assert math.isclose(centroid_lon, 77.5, rel_tol=1e-3)

        bbox = calculate_bounding_box(points)
        assert bbox.min_latitude == 28.0
        assert bbox.max_latitude == 29.0
        assert bbox.min_longitude == 77.0
        assert bbox.max_longitude == 78.0

    def test_empty_points_raises_value_error(self) -> None:
        """Empty sequence raises ValueError."""
        with pytest.raises(ValueError):
            calculate_spatial_centroid([])

        with pytest.raises(ValueError):
            calculate_bounding_box([])
