"""Unit and integration tests for Atmospheric Dispersion service and API endpoints (Phase 3)."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from packages.config.settings import AppEnvironment, LogLevel, get_test_settings
from packages.data.weather.dispersion_service import AtmosphericDispersionService, get_dispersion_service
from packages.physics.wind import build_wind_vector
from packages.schemas.common import Coordinate
from packages.schemas.dispersion import AtmosphericDispersionResult, PasquillStabilityClass
from packages.schemas.weather import (
    AtmosphereData,
    CanonicalWeatherData,
    DataQuality,
    DataStatus,
    WeatherProviderInfo,
    WindState,
)
from services.api.app import create_app
from services.api.dependencies import get_app_settings
from services.api.schemas.dispersion import (
    DispersionCalculationRequest,
    DispersionCalculationResponse,
)


def _make_mock_weather(
    lat: float = 22.38,
    lon: float = 69.87,
    speed_ms: float = 6.0,
    direction_deg: float = 270.0,
    quality: DataQuality = DataQuality.LIVE,
) -> CanonicalWeatherData:
    now = datetime.now(timezone.utc)
    return CanonicalWeatherData(
        location=Coordinate(latitude=lat, longitude=lon),
        observed_at=now,
        retrieved_at=now,
        data_status=DataStatus.LIVE,
        data_quality=quality,
        atmosphere=AtmosphereData(
            temperature_c=28.0,
            relative_humidity_pct=45.0,
            cloud_cover_pct=20.0,
            surface_pressure_hpa=1012.0,
        ),
        wind=build_wind_vector(speed_ms=speed_ms, direction_from_deg=direction_deg, gust_ms=8.0),
        forecast=[],
        provider=WeatherProviderInfo(name="open-meteo", model="best_match"),
    )


@pytest.fixture
def test_app() -> FastAPI:
    """Create test FastAPI application instance with test configuration."""
    settings = get_test_settings(
        ENVIRONMENT=AppEnvironment.TEST,
        DEBUG=True,
        LOG_LEVEL=LogLevel.DEBUG,
    )
    app = create_app(settings=settings)
    app.dependency_overrides[get_app_settings] = lambda: settings
    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Create a TestClient for testing HTTP requests."""
    return TestClient(test_app)


class TestAtmosphericDispersionService:
    """Unit tests for AtmosphericDispersionService business logic."""

    @patch("packages.data.weather.service.WeatherService.get_weather")
    def test_calculate_dispersion_with_live_weather(self, mock_get_weather: MagicMock) -> None:
        mock_get_weather.return_value = _make_mock_weather(speed_ms=7.0, direction_deg=225.0)
        settings = get_test_settings()
        service = AtmosphericDispersionService(settings=settings)

        res = service.calculate_dispersion(
            latitude=22.38,
            longitude=69.87,
            frp_mw=45.0,
            is_daytime=True,
        )

        assert isinstance(res, AtmosphericDispersionResult)
        assert res.source_location.latitude == 22.38
        assert res.source_location.longitude == 69.87
        assert res.wind.speed_ms == 7.0
        assert res.dispersion.is_engineering_approximation is True
        assert res.dispersion.plume_angle_deg == 45.0  # From SW (225) -> downwind NE (45)
        assert len(res.trajectory) > 5
        assert res.data_quality == DataQuality.LIVE

    @patch("packages.data.weather.service.WeatherService.get_weather")
    def test_calculate_dispersion_with_parameter_overrides(self, mock_get_weather: MagicMock) -> None:
        mock_get_weather.return_value = _make_mock_weather(speed_ms=2.0, direction_deg=90.0)
        settings = get_test_settings()
        service = AtmosphericDispersionService(settings=settings)

        res = service.calculate_dispersion(
            latitude=22.38,
            longitude=69.87,
            custom_wind_speed_ms=12.0,
            custom_wind_direction_deg=180.0,
            release_height_m=50.0,
            max_distance_km=15.0,
        )

        assert res.wind.speed_ms == 12.0
        assert res.wind.direction_from_deg == 180.0
        assert res.dispersion.plume_angle_deg == 0.0  # From South (180) -> downwind North (0)
        assert res.dispersion.effective_release_height_m >= 50.0
        assert res.dispersion.max_hazard_distance_km == 15.0
        assert res.trajectory[-1].downwind_distance_km == 15.0

    @patch("packages.data.weather.service.WeatherService.get_weather")
    def test_evaluate_event_dispersion(self, mock_get_weather: MagicMock) -> None:
        mock_get_weather.return_value = _make_mock_weather()
        settings = get_test_settings()
        service = AtmosphericDispersionService(settings=settings)

        res = service.evaluate_event_dispersion(
            event_id="EVT-2026-GUJ-001",
            latitude=22.38,
            longitude=69.87,
            frp_mw=80.0,
        )

        assert res.event_id == "EVT-2026-GUJ-001"
        assert res.dispersion.source_strength_proxy == pytest.approx(80.0 ** 0.5, rel=1e-3)

    @patch("packages.data.weather.service.WeatherService.get_weather")
    def test_weather_fallback_propagation(self, mock_get_weather: MagicMock) -> None:
        mock_get_weather.return_value = _make_mock_weather(quality=DataQuality.FALLBACK)
        settings = get_test_settings()
        service = AtmosphericDispersionService(settings=settings)

        res = service.calculate_dispersion(latitude=22.38, longitude=69.87)
        assert res.data_quality == DataQuality.FALLBACK


class TestDispersionApiEndpoints:
    """Integration test suite for FastAPI /dispersion and /events/{event_id}/dispersion routes."""

    @patch("packages.data.weather.service.WeatherService.get_weather")
    def test_post_dispersion_success(self, mock_get_weather: MagicMock, client: TestClient) -> None:
        mock_get_weather.return_value = _make_mock_weather(speed_ms=8.0, direction_deg=270.0)

        payload = {
            "latitude": 22.38,
            "longitude": 69.87,
            "frp_mw": 50.0,
            "release_height_m": 15.0,
            "max_distance_km": 10.0,
            "is_daytime": True,
        }

        response = client.post("/dispersion", json=payload)
        assert response.status_code == 200

        data = response.json()
        validated = DispersionCalculationResponse.model_validate(data)
        assert validated.source_location.latitude == 22.38
        assert validated.dispersion.is_engineering_approximation is True
        assert validated.dispersion.plume_angle_deg == 90.0
        assert validated.dispersion.effective_release_height_m >= 15.0
        assert len(validated.trajectory) > 5

    @patch("packages.data.weather.service.WeatherService.get_weather")
    def test_get_dispersion_query_params(self, mock_get_weather: MagicMock, client: TestClient) -> None:
        mock_get_weather.return_value = _make_mock_weather(speed_ms=5.0, direction_deg=180.0)

        response = client.get("/dispersion?lat=22.38&lon=69.87&frp_mw=30.0&max_distance_km=8.0")
        assert response.status_code == 200

        data = response.json()
        assert data["source_location"]["latitude"] == 22.38
        assert data["dispersion"]["plume_angle_deg"] == 0.0

    @patch("packages.data.weather.service.WeatherService.get_weather")
    def test_get_dispersion_events_endpoint(self, mock_get_weather: MagicMock, client: TestClient) -> None:
        mock_get_weather.return_value = _make_mock_weather()

        response = client.get(
            "/dispersion/events/EVT-TEST-001?latitude=22.38&longitude=69.87&frp_mw=40.0"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["event_id"] == "EVT-TEST-001"

    @patch("packages.data.weather.service.WeatherService.get_weather")
    def test_get_event_dispersion_coupled_route(
        self, mock_get_weather: MagicMock, client: TestClient
    ) -> None:
        mock_get_weather.return_value = _make_mock_weather()

        # Query first available event from /events to test coupling
        events_resp = client.get("/events?limit=1")
        if events_resp.status_code == 200 and events_resp.json()["events"]:
            ev_id = events_resp.json()["events"][0]["event_id"]
            resp = client.get(f"/events/{ev_id}/dispersion")
            assert resp.status_code == 200
            data = resp.json()
            assert data["event_id"] == ev_id
            assert "dispersion" in data
            assert "trajectory" in data

    def test_get_dispersion_missing_coordinates(self, client: TestClient) -> None:
        response = client.get("/dispersion")
        assert response.status_code == 422
        data = response.json()
        assert "VALIDATION_ERROR" in str(data)

    def test_post_dispersion_invalid_latitude_range(self, client: TestClient) -> None:
        response = client.post(
            "/dispersion",
            json={"latitude": 105.0, "longitude": 69.87},
        )
        assert response.status_code == 422

    def test_post_dispersion_invalid_max_distance(self, client: TestClient) -> None:
        response = client.post(
            "/dispersion",
            json={"latitude": 22.38, "longitude": 69.87, "max_distance_km": 100.0},
        )
        assert response.status_code == 422
