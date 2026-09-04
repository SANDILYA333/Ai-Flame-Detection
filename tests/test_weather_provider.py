"""Tests for Open-Meteo weather provider response parsing, query building, validation, and error handling."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from packages.config.settings import get_test_settings
from packages.data.weather.open_meteo import OpenMeteoWeatherProvider
from packages.errors import (
    ExternalServiceError,
    ServiceTimeoutError,
    ServiceUnavailableError,
)
from packages.schemas.weather import DataQuality, DataStatus, WindState


@pytest.fixture
def mock_open_meteo_payload() -> dict:
    """Canonical mocked Open-Meteo API response."""
    return {
        "latitude": 23.125,
        "longitude": 72.5625,
        "generationtime_ms": 0.12,
        "utc_offset_seconds": 0,
        "timezone": "UTC",
        "elevation": 55.0,
        "current_units": {
            "wind_speed_10m": "ms",
        },
        "current": {
            "time": "2026-09-04T04:30",
            "interval": 900,
            "temperature_2m": 32.4,
            "relative_humidity_2m": 41.0,
            "surface_pressure": 1008.4,
            "precipitation": 0.0,
            "cloud_cover": 12.0,
            "wind_speed_10m": 8.4,
            "wind_direction_10m": 225.0,
            "wind_gusts_10m": 11.2,
            "boundary_layer_height": 1240.0,
            "soil_moisture_0_to_1cm": 0.152,
        },
        "hourly": {
            "time": [
                "2026-09-04T04:30",
                "2026-09-04T10:30",  # +6h
                "2026-09-04T16:30",  # +12h
                "2026-09-05T04:30",  # +24h
            ],
            "temperature_2m": [32.4, 35.0, 31.0, 27.5],
            "relative_humidity_2m": [41.0, 30.0, 48.0, 65.0],
            "surface_pressure": [1008.4, 1006.2, 1007.8, 1010.1],
            "precipitation": [0.0, 0.0, 0.5, 0.0],
            "cloud_cover": [12.0, 5.0, 40.0, 10.0],
            "wind_speed_10m": [8.4, 9.2, 6.1, 4.0],
            "wind_direction_10m": [225.0, 240.0, 210.0, 180.0],
            "wind_gusts_10m": [11.2, 12.5, 8.0, 5.5],
            "boundary_layer_height": [1240.0, 1500.0, 900.0, 400.0],
            "soil_moisture_0_to_1cm": [0.152, 0.148, 0.145, 0.142],
        },
    }


class TestOpenMeteoWeatherProvider:
    """Test suite for OpenMeteoWeatherProvider."""

    def test_provider_initialization(self) -> None:
        settings = get_test_settings(OPEN_METEO_BASE_URL="https://custom.api.open-meteo.com")
        provider = OpenMeteoWeatherProvider(settings)
        assert provider.provider_name == "open-meteo"
        assert provider.base_url == "https://custom.api.open-meteo.com"

    def test_build_request_params(self) -> None:
        provider = OpenMeteoWeatherProvider()
        params = provider._build_request_params(23.123456, 72.654321, forecast_hours=24)
        assert params["latitude"] == 23.1235
        assert params["longitude"] == 72.6543
        assert "temperature_2m" in params["current"]
        assert "wind_speed_10m" in params["current"]
        assert params["wind_speed_unit"] == "ms"
        assert params["timezone"] == "UTC"

    def test_parse_weather_response(self, mock_open_meteo_payload: dict) -> None:
        provider = OpenMeteoWeatherProvider()
        data = provider.parse_weather_response(
            payload=mock_open_meteo_payload,
            latitude=23.1234,
            longitude=72.5678,
            forecast_hours=24,
        )

        # Basic properties
        assert data.location.latitude == 23.1234
        assert data.location.longitude == 72.5678
        assert data.data_status == DataStatus.LIVE
        assert data.data_quality == DataQuality.LIVE
        assert data.provider.name == "open-meteo"

        # Wind properties
        assert data.wind.speed_ms == 8.4
        assert data.wind.direction_from_deg == 225.0
        assert data.wind.direction_from_label == "SW"
        assert data.wind.direction_to_deg == 45.0
        assert data.wind.downwind_direction_label == "NE"
        assert data.wind.gust_ms == 11.2
        assert data.wind.is_calm is False
        assert data.wind.wind_state == WindState.FRESH
        assert data.wind.u_ms > 0
        assert data.wind.v_ms > 0

        # Atmospheric properties
        assert data.atmosphere.temperature_c == 32.4
        assert data.atmosphere.relative_humidity_pct == 41.0
        assert data.atmosphere.surface_pressure_hpa == 1008.4
        assert data.atmosphere.precipitation_mm == 0.0
        assert data.atmosphere.cloud_cover_pct == 12.0
        assert data.atmosphere.boundary_layer_height_m == 1240.0
        assert data.atmosphere.soil_moisture_m3_m3 == 0.152

        # Forecast horizons
        assert len(data.forecast) == 3
        horizons = [pt.horizon_hours for pt in data.forecast]
        assert horizons == [6, 12, 24]

        # Check 6h forecast
        pt6 = data.forecast[0]
        assert pt6.horizon_hours == 6
        assert pt6.atmosphere.temperature_c == 35.0
        assert pt6.wind.direction_from_deg == 240.0
        assert pt6.wind.direction_from_label == "WSW"
        assert pt6.wind.direction_to_deg == 60.0
        assert pt6.wind.downwind_direction_label == "ENE"

    def test_parse_kmh_unit_conversion(self, mock_open_meteo_payload: dict) -> None:
        provider = OpenMeteoWeatherProvider()
        mock_open_meteo_payload["current_units"]["wind_speed_10m"] = "km/h"
        mock_open_meteo_payload["current"]["wind_speed_10m"] = 36.0  # 36 km/h = 10.0 m/s
        data = provider.parse_weather_response(
            payload=mock_open_meteo_payload,
            latitude=23.0,
            longitude=72.0,
        )
        assert data.wind.speed_ms == 10.0

    def test_parse_weather_response_missing_current_raises(self) -> None:
        provider = OpenMeteoWeatherProvider()
        with pytest.raises(ExternalServiceError, match="missing required 'current'"):
            provider.parse_weather_response(
                payload={"latitude": 23.0},
                latitude=23.0,
                longitude=72.0,
            )

    @patch("packages.data.weather.open_meteo.httpx.Client")
    def test_execute_http_request_success(self, mock_client_cls: MagicMock, mock_open_meteo_payload: dict) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_open_meteo_payload

        mock_client_instance = MagicMock()
        mock_client_instance.get.return_value = mock_response
        mock_client_cls.return_value.__enter__.return_value = mock_client_instance

        provider = OpenMeteoWeatherProvider()
        res = provider.get_weather(latitude=23.1234, longitude=72.5678)
        assert res.wind.speed_ms == 8.4
        assert res.atmosphere.temperature_c == 32.4

    @patch("packages.data.weather.open_meteo.httpx.Client")
    def test_execute_http_request_503_raises_service_unavailable(self, mock_client_cls: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.text = "Service Temporarily Unavailable"

        mock_client_instance = MagicMock()
        mock_client_instance.get.return_value = mock_response
        mock_client_cls.return_value.__enter__.return_value = mock_client_instance

        settings = get_test_settings(OPEN_METEO_MAX_RETRIES=0)
        provider = OpenMeteoWeatherProvider(settings)

        with pytest.raises(ServiceUnavailableError, match="HTTP 503"):
            provider.get_weather(latitude=23.1234, longitude=72.5678)
