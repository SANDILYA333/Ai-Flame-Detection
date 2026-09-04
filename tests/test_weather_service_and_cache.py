"""Tests for WeatherService coordination, spatial caching, TTL, event enrichment, and degraded fallback."""

import time
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from packages.config.settings import get_test_settings
from packages.data.weather.base import BaseWeatherProvider
from packages.data.weather.cache import WeatherCache
from packages.data.weather.service import WeatherService, get_weather_service
from packages.errors import InvalidCoordinateError, ServiceUnavailableError
from packages.physics.wind import build_wind_vector
from packages.schemas.common import Coordinate
from packages.schemas.weather import (
    AtmosphereData,
    CanonicalWeatherData,
    DataQuality,
    DataStatus,
    WeatherProviderInfo,
)


def _make_dummy_weather(lat: float, lon: float, temp: float = 30.0) -> CanonicalWeatherData:
    """Helper to generate valid canonical weather record."""
    now = datetime.now(timezone.utc)
    return CanonicalWeatherData(
        location=Coordinate(latitude=lat, longitude=lon),
        observed_at=now,
        retrieved_at=now,
        data_status=DataStatus.LIVE,
        data_quality=DataQuality.LIVE,
        atmosphere=AtmosphereData(
            temperature_c=temp,
            relative_humidity_pct=45.0,
            surface_pressure_hpa=1010.0,
            precipitation_mm=0.0,
            cloud_cover_pct=10.0,
            boundary_layer_height_m=1200.0,
            soil_moisture_m3_m3=0.15,
        ),
        wind=build_wind_vector(speed_ms=6.0, direction_from_deg=180.0, gust_ms=8.0),
        forecast=[],
        provider=WeatherProviderInfo(name="open-meteo"),
    )


class TestWeatherCache:
    """Test spatial bucketing and TTL behavior."""

    def test_cache_hit_and_spatial_quantization(self) -> None:
        cache = WeatherCache(grid_precision=3)
        data = _make_dummy_weather(23.1234, 72.5678)
        cache.set(data, forecast_hours=24, ttl_seconds=60.0)

        # Exact coordinate match
        hit = cache.get(23.1234, 72.5678, forecast_hours=24)
        assert hit is not None
        assert hit.data_status == DataStatus.CACHED
        assert hit.data_quality == DataQuality.CACHED

        # Proximate coordinate quantized to same grid (23.123, 72.568)
        hit_proximate = cache.get(23.12344, 72.56779, forecast_hours=24)
        assert hit_proximate is not None
        assert hit_proximate.data_status == DataStatus.CACHED
        assert hit_proximate.data_quality == DataQuality.CACHED

        # Distant coordinate misses cache
        miss = cache.get(24.5000, 75.0000, forecast_hours=24)
        assert miss is None

    def test_cache_ttl_expiration(self) -> None:
        cache = WeatherCache(grid_precision=3)
        data = _make_dummy_weather(23.123, 72.567)
        # Short TTL of 0.05s
        cache.set(data, forecast_hours=24, ttl_seconds=0.05)

        assert cache.get(23.123, 72.567, forecast_hours=24) is not None
        time.sleep(0.08)
        # Expired for normal get
        assert cache.get(23.123, 72.567, forecast_hours=24) is None
        # Still available for degraded stale fallback with FALLBACK quality
        stale = cache.get_stale(23.123, 72.567, forecast_hours=24)
        assert stale is not None
        assert stale.data_status == DataStatus.CACHED
        assert stale.data_quality == DataQuality.FALLBACK


class TestWeatherService:
    """Test WeatherService workflow, coordinate validation, fallback, and event enrichment."""

    def test_coordinate_validation_errors(self) -> None:
        service = WeatherService()

        with pytest.raises(InvalidCoordinateError):
            service.get_weather(latitude=95.0, longitude=72.0)

        with pytest.raises(InvalidCoordinateError):
            service.get_weather(latitude=23.0, longitude=-190.0)

        with pytest.raises(InvalidCoordinateError):
            service.get_weather(latitude=float("nan"), longitude=72.0)

    def test_service_flow_cache_miss_then_hit(self) -> None:
        mock_provider = MagicMock(spec=BaseWeatherProvider)
        mock_provider.get_weather.return_value = _make_dummy_weather(23.123, 72.567, temp=32.0)

        cache = WeatherCache()
        service = WeatherService(provider=mock_provider, cache=cache)

        # 1st call: Provider called
        res1 = service.get_weather(23.123, 72.567, forecast_hours=24)
        assert res1.data_status == DataStatus.LIVE
        assert res1.data_quality == DataQuality.LIVE
        assert mock_provider.get_weather.call_count == 1

        # 2nd call: Returned from cache without calling provider again
        res2 = service.get_weather(23.123, 72.567, forecast_hours=24)
        assert res2.data_status == DataStatus.CACHED
        assert res2.data_quality == DataQuality.CACHED
        assert mock_provider.get_weather.call_count == 1

    def test_service_degraded_fallback_to_stale_cache(self) -> None:
        mock_provider = MagicMock(spec=BaseWeatherProvider)
        mock_provider.get_weather.return_value = _make_dummy_weather(23.123, 72.567, temp=32.0)

        cache = WeatherCache()
        service = WeatherService(provider=mock_provider, cache=cache)

        # Seed cache
        service.get_weather(23.123, 72.567, forecast_hours=24)

        # Make cache expire
        cache._cache[cache._make_key(23.123, 72.567, 24)].stored_at = time.time() - 1000

        # Now make provider fail
        mock_provider.get_weather.side_effect = ServiceUnavailableError("Open-Meteo down")

        # Service gracefully returns stale data with FALLBACK quality
        fallback = service.get_weather(23.123, 72.567, forecast_hours=24)
        assert fallback.data_status == DataStatus.CACHED
        assert fallback.data_quality == DataQuality.FALLBACK
        assert fallback.atmosphere.temperature_c == 32.0

    def test_enrich_event(self) -> None:
        mock_provider = MagicMock(spec=BaseWeatherProvider)
        mock_provider.get_weather.return_value = _make_dummy_weather(22.38, 69.87, temp=29.5)

        service = WeatherService(provider=mock_provider, cache=WeatherCache())
        enrichment = service.enrich_event(
            event_id="EVT-2026-GUJ-001",
            latitude=22.38,
            longitude=69.87,
        )

        assert enrichment.event_id == "EVT-2026-GUJ-001"
        assert enrichment.weather.location.latitude == 22.38
        assert enrichment.weather.location.longitude == 69.87
        assert enrichment.weather.atmosphere.temperature_c == 29.5

    def test_singleton_factory(self) -> None:
        s1 = get_weather_service()
        s2 = get_weather_service()
        assert s1 is s2
