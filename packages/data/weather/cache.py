"""Spatially-bucketed, thread-safe in-memory cache for meteorological data."""

import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import NamedTuple

from packages.config.settings import Settings, get_settings
from packages.schemas.weather import (
    CanonicalWeatherData,
    DataQuality,
    DataStatus,
)


class SpatialCacheKey(NamedTuple):
    """Spatially quantized cache key."""

    lat_grid: float
    lon_grid: float
    forecast_hours: int


@dataclass
class _CacheEntry:
    data: CanonicalWeatherData
    stored_at: float
    ttl_seconds: float


class WeatherCache:
    """Thread-safe spatial cache with TTL expiration and stale retrieval fallback."""

    def __init__(
        self,
        settings: Settings | None = None,
        grid_precision: int = 3,
    ) -> None:
        self.settings = settings or get_settings()
        self.ttl_seconds = float(self.settings.WEATHER_CACHE_TTL_SECONDS)
        self.max_entries = int(self.settings.WEATHER_CACHE_MAX_ENTRIES)
        self.grid_precision = grid_precision
        self._cache: dict[SpatialCacheKey, _CacheEntry] = {}
        self._lock = threading.Lock()

    def _make_key(
        self, latitude: float, longitude: float, forecast_hours: int
    ) -> SpatialCacheKey:
        """Quantize coordinates to spatial grid to group proximate events."""
        return SpatialCacheKey(
            lat_grid=round(latitude, self.grid_precision),
            lon_grid=round(longitude, self.grid_precision),
            forecast_hours=forecast_hours,
        )

    def get(
        self,
        latitude: float,
        longitude: float,
        forecast_hours: int = 24,
    ) -> CanonicalWeatherData | None:
        """Retrieve valid (non-expired) cached weather data if present."""
        key = self._make_key(latitude, longitude, forecast_hours)
        now = time.time()

        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None

            if now - entry.stored_at <= entry.ttl_seconds:
                # Return updated copy with CACHED status and current retrieved_at
                cached_copy = entry.data.model_copy(
                    update={
                        "data_status": DataStatus.CACHED,
                        "data_quality": DataQuality.CACHED,
                        "retrieved_at": datetime.now(timezone.utc),
                    }
                )
                return cached_copy

        return None

    def get_stale(
        self,
        latitude: float,
        longitude: float,
        forecast_hours: int = 24,
    ) -> CanonicalWeatherData | None:
        """Retrieve stale cached data when live provider is unavailable (fallback mode)."""
        key = self._make_key(latitude, longitude, forecast_hours)

        with self._lock:
            entry = self._cache.get(key)
            if entry is not None:
                return entry.data.model_copy(
                    update={
                        "data_status": DataStatus.CACHED,
                        "data_quality": DataQuality.FALLBACK,
                        "retrieved_at": datetime.now(timezone.utc),
                    }
                )

        return None

    def set(
        self,
        data: CanonicalWeatherData,
        forecast_hours: int = 24,
        ttl_seconds: float | None = None,
    ) -> None:
        """Store weather data into cache."""
        key = self._make_key(
            data.location.latitude,
            data.location.longitude,
            forecast_hours,
        )
        ttl = self.ttl_seconds if ttl_seconds is None else ttl_seconds

        with self._lock:
            # If at max capacity, evict oldest entry
            if len(self._cache) >= self.max_entries and key not in self._cache:
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].stored_at)
                del self._cache[oldest_key]

            self._cache[key] = _CacheEntry(
                data=data,
                stored_at=time.time(),
                ttl_seconds=ttl,
            )

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        """Return current number of cached items."""
        with self._lock:
            return len(self._cache)
