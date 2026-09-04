"""Unit and integration tests for FastAPI /weather, /weather/current, and /weather/events endpoints."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from packages.config.settings import AppEnvironment, LogLevel, get_test_settings
from packages.physics.wind import build_wind_vector
from packages.schemas.common import Coordinate, UtcDatetime
from packages.schemas.weather import (
    AtmosphereData,
    CanonicalWeatherData,
    DataQuality,
    DataStatus,
    EventWeatherEnrichment,
    WeatherForecastPoint,
    WeatherProviderInfo,
    WindState,
)
from services.api.app import create_app
from services.api.dependencies import get_app_settings
from services.api.schemas.weather import EventWeatherResponse, WeatherResponse


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


class TestWeatherApi:
    """Test suite for GET /weather, /weather/current, and /weather/events/{event_id} routes."""

    @patch("packages.data.weather.service.WeatherService.get_weather")
    def test_get_weather_success(self, mock_get_weather: MagicMock, client: TestClient) -> None:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        mock_data = CanonicalWeatherData(
            location=Coordinate(latitude=23.1234, longitude=72.5678),
            observed_at=now,
            retrieved_at=now,
            data_status=DataStatus.LIVE,
            data_quality=DataQuality.LIVE,
            atmosphere=AtmosphereData(
                temperature_c=32.4,
                relative_humidity_pct=41.0,
                surface_pressure_hpa=1008.4,
                precipitation_mm=0.0,
                cloud_cover_pct=12.0,
                boundary_layer_height_m=1240.0,
                soil_moisture_m3_m3=0.15,
            ),
            wind=build_wind_vector(speed_ms=8.4, direction_from_deg=225.0, gust_ms=11.2),
            forecast=[
                WeatherForecastPoint(
                    forecast_time=now,
                    horizon_hours=6,
                    atmosphere=AtmosphereData(
                        temperature_c=35.0,
                        relative_humidity_pct=30.0,
                    ),
                    wind=build_wind_vector(speed_ms=9.2, direction_from_deg=240.0),
                )
            ],
            provider=WeatherProviderInfo(name="open-meteo", model="best_match"),
        )
        mock_get_weather.return_value = mock_data

        response = client.get("/weather?lat=23.1234&lon=72.5678&forecast_hours=6")
        assert response.status_code == 200

        payload = response.json()
        validated = WeatherResponse.model_validate(payload)
        assert validated.location.latitude == 23.1234
        assert validated.location.longitude == 72.5678
        assert validated.data_quality == DataQuality.LIVE
        assert validated.wind.speed_ms == 8.4
        assert validated.wind.direction_from_deg == 225.0
        assert validated.wind.direction_from_label == "SW"
        assert validated.wind.direction_to_deg == 45.0
        assert validated.wind.downwind_direction_label == "NE"
        assert validated.wind.is_calm is False
        assert validated.wind.wind_state == WindState.FRESH
        assert validated.wind.u_ms > 0
        assert validated.wind.v_ms > 0
        assert validated.atmosphere.temperature_c == 32.4
        assert len(validated.forecast) == 1
        assert validated.forecast[0].horizon_hours == 6

    @patch("packages.data.weather.service.WeatherService.get_weather")
    def test_get_current_weather_alias(self, mock_get_weather: MagicMock, client: TestClient) -> None:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        mock_get_weather.return_value = CanonicalWeatherData(
            location=Coordinate(latitude=22.38, longitude=69.87),
            observed_at=now,
            retrieved_at=now,
            data_status=DataStatus.LIVE,
            data_quality=DataQuality.LIVE,
            atmosphere=AtmosphereData(temperature_c=30.0, relative_humidity_pct=60.0),
            wind=build_wind_vector(speed_ms=4.2, direction_from_deg=225.0, gust_ms=6.1),
            forecast=[],
            provider=WeatherProviderInfo(name="open-meteo"),
        )

        response = client.get("/weather/current?lat=22.38&lon=69.87")
        assert response.status_code == 200
        data = response.json()
        assert data["location"]["latitude"] == 22.38
        assert data["wind"]["direction_from_label"] == "SW"
        assert data["wind"]["downwind_direction_label"] == "NE"

    @patch("packages.data.weather.service.WeatherService.enrich_event")
    def test_get_event_weather(self, mock_enrich_event: MagicMock, client: TestClient) -> None:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        mock_enrich_event.return_value = EventWeatherEnrichment(
            event_id="EVT-2026-GUJ-001",
            weather=CanonicalWeatherData(
                location=Coordinate(latitude=22.38, longitude=69.87),
                observed_at=now,
                retrieved_at=now,
                data_status=DataStatus.LIVE,
                data_quality=DataQuality.LIVE,
                atmosphere=AtmosphereData(temperature_c=30.0, relative_humidity_pct=60.0),
                wind=build_wind_vector(speed_ms=4.2, direction_from_deg=225.0),
                forecast=[],
                provider=WeatherProviderInfo(name="open-meteo"),
            ),
            enriched_at=now,
        )

        response = client.get("/weather/events/EVT-2026-GUJ-001?latitude=22.38&longitude=69.87")
        assert response.status_code == 200
        payload = response.json()
        validated = EventWeatherResponse.model_validate(payload)
        assert validated.event_id == "EVT-2026-GUJ-001"
        assert validated.weather.location.latitude == 22.38
        assert validated.weather.wind.direction_from_label == "SW"

    def test_get_weather_missing_coordinates(self, client: TestClient) -> None:
        response = client.get("/weather")
        assert response.status_code == 422
        data = response.json()
        assert "VALIDATION_ERROR" in str(data)

    def test_get_weather_invalid_latitude_out_of_range(self, client: TestClient) -> None:
        response = client.get("/weather?lat=95.0&lon=72.0")
        assert response.status_code == 422

    def test_get_weather_invalid_longitude_out_of_range(self, client: TestClient) -> None:
        response = client.get("/weather?lat=23.0&lon=-195.0")
        assert response.status_code == 422

    @patch("packages.data.weather.service.WeatherService.get_weather")
    def test_get_weather_aliases_latitude_longitude(
        self, mock_get_weather: MagicMock, client: TestClient
    ) -> None:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        mock_get_weather.return_value = CanonicalWeatherData(
            location=Coordinate(latitude=28.6139, longitude=77.2090),
            observed_at=now,
            retrieved_at=now,
            data_status=DataStatus.LIVE,
            data_quality=DataQuality.LIVE,
            atmosphere=AtmosphereData(temperature_c=25.0, relative_humidity_pct=50.0),
            wind=build_wind_vector(speed_ms=4.0, direction_from_deg=90.0),
            forecast=[],
            provider=WeatherProviderInfo(name="open-meteo"),
        )

        response = client.get("/weather?latitude=28.6139&longitude=77.2090")
        assert response.status_code == 200
        mock_get_weather.assert_called_once()
