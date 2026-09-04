"""Open-Meteo meteorological provider implementation with bounded retries and physical validation."""

import json
import logging
import math
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from packages.config.settings import Settings, get_settings
from packages.data.weather.base import BaseWeatherProvider
from packages.errors import (
    ExternalServiceError,
    ServiceTimeoutError,
    ServiceUnavailableError,
)
from packages.logging import get_logger, log_with_context
from packages.physics.wind import build_wind_vector
from packages.schemas.common import Coordinate
from packages.schemas.weather import (
    AtmosphereData,
    CanonicalWeatherData,
    DataQuality,
    DataStatus,
    WeatherForecastPoint,
    WeatherProviderInfo,
)

logger = get_logger("packages.data.weather.open_meteo")


class OpenMeteoWeatherProvider(BaseWeatherProvider):
    """Production provider for fetching weather data from Open-Meteo API."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.base_url = self.settings.OPEN_METEO_BASE_URL.rstrip("/")
        self.timeout = float(self.settings.OPEN_METEO_TIMEOUT_SECONDS)
        self.max_retries = int(self.settings.OPEN_METEO_MAX_RETRIES)
        self.backoff_factor = float(self.settings.OPEN_METEO_RETRY_BACKOFF_FACTOR)

    @property
    def provider_name(self) -> str:
        return "open-meteo"

    def _parse_iso_datetime(self, time_str: str) -> datetime:
        """Parse ISO datetime string and ensure UTC timezone awareness."""
        dt = datetime.fromisoformat(time_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt

    def _build_request_params(
        self, latitude: float, longitude: float, forecast_hours: int
    ) -> dict[str, Any]:
        """Build query parameters for Open-Meteo forecast endpoint."""
        forecast_days = max(1, min(7, (forecast_hours + 23) // 24 + 1))

        current_vars = [
            "temperature_2m",
            "relative_humidity_2m",
            "surface_pressure",
            "precipitation",
            "cloud_cover",
            "wind_speed_10m",
            "wind_direction_10m",
            "wind_gusts_10m",
            "boundary_layer_height",
            "soil_moisture_0_to_1cm",
        ]
        hourly_vars = [
            "temperature_2m",
            "relative_humidity_2m",
            "surface_pressure",
            "precipitation",
            "cloud_cover",
            "wind_speed_10m",
            "wind_direction_10m",
            "wind_gusts_10m",
            "boundary_layer_height",
            "soil_moisture_0_to_1cm",
        ]

        return {
            "latitude": round(latitude, 4),
            "longitude": round(longitude, 4),
            "current": ",".join(current_vars),
            "hourly": ",".join(hourly_vars),
            "wind_speed_unit": "ms",
            "timeformat": "iso8601",
            "timezone": "UTC",
            "forecast_days": forecast_days,
        }

    def _execute_http_request(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute HTTP request against Open-Meteo with bounded retries."""
        url = f"{self.base_url}/v1/forecast"
        headers = {
            "Accept": "application/json",
            "User-Agent": "SIH26162-Flare-Intelligence/1.0",
        }

        last_error: Exception | None = None
        start_time = time.time()

        for attempt in range(self.max_retries + 1):
            try:
                log_with_context(
                    logger,
                    logging.DEBUG,
                    f"Requesting Open-Meteo weather data (attempt {attempt + 1}/{self.max_retries + 1})",
                    context={
                        "latitude": params.get("latitude"),
                        "longitude": params.get("longitude"),
                        "endpoint": url,
                    },
                )
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.get(url, params=params, headers=headers)
                    latency_ms = round((time.time() - start_time) * 1000, 2)

                    if response.status_code == 200:
                        try:
                            payload = response.json()
                            log_with_context(
                                logger,
                                logging.INFO,
                                "Open-Meteo weather request successful",
                                context={
                                    "latitude": params.get("latitude"),
                                    "longitude": params.get("longitude"),
                                    "latency_ms": latency_ms,
                                    "attempt": attempt + 1,
                                },
                            )
                            return payload
                        except json.JSONDecodeError as jde:
                            raise ExternalServiceError(
                                f"Failed to parse Open-Meteo JSON response: {jde}",
                                details={"response_text": response.text[:300]},
                            ) from jde

                    if response.status_code in (429, 502, 503, 504):
                        last_error = ServiceUnavailableError(
                            f"Open-Meteo HTTP {response.status_code}: {response.text[:200]}",
                            details={"status_code": response.status_code},
                        )
                    elif response.status_code >= 400:
                        raise ExternalServiceError(
                            f"Open-Meteo API error HTTP {response.status_code}: {response.text[:300]}",
                            details={"status_code": response.status_code},
                        )
            except httpx.TimeoutException as te:
                last_error = ServiceTimeoutError(
                    f"Open-Meteo request timed out after {self.timeout}s",
                    details={"timeout": self.timeout, "error": str(te)},
                )
            except httpx.NetworkError as ne:
                last_error = ServiceUnavailableError(
                    f"Open-Meteo network connection error: {ne}",
                    details={"error": str(ne)},
                )

            if attempt < self.max_retries:
                sleep_sec = self.backoff_factor * (2**attempt)
                log_with_context(
                    logger,
                    logging.WARNING,
                    f"Open-Meteo attempt {attempt + 1} failed. Retrying in {sleep_sec:.2f}s",
                    context={"error": str(last_error)},
                )
                time.sleep(sleep_sec)

        if isinstance(last_error, (ServiceTimeoutError, ServiceUnavailableError, ExternalServiceError)):
            raise last_error

        raise ExternalServiceError(
            f"Open-Meteo request failed after {self.max_retries + 1} attempts: {last_error}",
            details={"last_error": str(last_error)},
        )

    def _validate_temperature(self, value: Any) -> float:
        """Validate and clamp air temperature in Celsius."""
        if value is None:
            return 20.0
        try:
            val = float(value)
            if not math.isfinite(val) or val < -80.0 or val > 65.0:
                raise ValueError(f"Temperature out of plausible range: {val}°C")
            return val
        except (TypeError, ValueError) as err:
            raise ExternalServiceError(f"Invalid temperature in provider response: {value}") from err

    def _validate_humidity(self, value: Any) -> float:
        """Validate and clamp relative humidity percentage."""
        if value is None:
            return 50.0
        try:
            val = float(value)
            if not math.isfinite(val):
                return 50.0
            return max(0.0, min(100.0, val))
        except (TypeError, ValueError):
            return 50.0

    def _validate_pressure(self, value: Any) -> float | None:
        """Validate atmospheric surface pressure in hPa."""
        if value is None:
            return None
        try:
            val = float(value)
            if not math.isfinite(val) or val < 300.0 or val > 1150.0:
                return None
            return round(val, 2)
        except (TypeError, ValueError):
            return None

    def _validate_wind_speed(self, value: Any, unit: str = "ms") -> float:
        """Validate wind speed and convert to canonical m/s if necessary."""
        if value is None:
            return 0.0
        try:
            val = float(value)
            if not math.isfinite(val) or val < 0.0:
                return 0.0
            if unit.lower() in ("km/h", "kmh"):
                val = val / 3.6
            return round(val, 2)
        except (TypeError, ValueError):
            return 0.0

    def parse_weather_response(
        self,
        payload: dict[str, Any],
        latitude: float,
        longitude: float,
        forecast_hours: int = 24,
    ) -> CanonicalWeatherData:
        """Normalize raw Open-Meteo response into CanonicalWeatherData domain model."""
        now_utc = datetime.now(timezone.utc)
        current = payload.get("current", {})
        current_units = payload.get("current_units", {})

        if not current:
            raise ExternalServiceError(
                "Open-Meteo response missing required 'current' weather block",
                details={"keys": list(payload.keys())},
            )

        # 1. Observation Timestamp
        time_raw = current.get("time")
        if time_raw:
            observed_at = self._parse_iso_datetime(time_raw)
        else:
            observed_at = now_utc

        # 2. Wind Vector
        speed_unit = str(current_units.get("wind_speed_10m", "ms"))
        speed = self._validate_wind_speed(current.get("wind_speed_10m", 0.0), unit=speed_unit)
        direction_raw = current.get("wind_direction_10m", 0.0)
        direction = float(direction_raw) if direction_raw is not None and math.isfinite(float(direction_raw)) else 0.0
        gust = current.get("wind_gusts_10m")
        gust_ms = self._validate_wind_speed(gust, unit=speed_unit) if gust is not None else None

        wind = build_wind_vector(speed_ms=speed, direction_from_deg=direction, gust_ms=gust_ms)

        # 3. Atmosphere
        temp = self._validate_temperature(current.get("temperature_2m", 20.0))
        humidity = self._validate_humidity(current.get("relative_humidity_2m", 50.0))
        pressure = self._validate_pressure(current.get("surface_pressure"))
        precip_raw = current.get("precipitation", 0.0)
        precip = float(precip_raw) if precip_raw is not None and math.isfinite(float(precip_raw)) else 0.0
        cloud_raw = current.get("cloud_cover")
        cloud = float(cloud_raw) if cloud_raw is not None and math.isfinite(float(cloud_raw)) else None
        pbl_raw = current.get("boundary_layer_height")
        pbl = float(pbl_raw) if pbl_raw is not None and math.isfinite(float(pbl_raw)) else None
        soil_raw = current.get("soil_moisture_0_to_1cm")
        soil = float(soil_raw) if soil_raw is not None and math.isfinite(float(soil_raw)) else None

        atmosphere = AtmosphereData(
            temperature_c=round(temp, 2),
            relative_humidity_pct=round(humidity, 1),
            surface_pressure_hpa=pressure,
            precipitation_mm=max(0.0, round(precip, 2)),
            cloud_cover_pct=max(0.0, min(100.0, round(cloud, 1))) if cloud is not None else None,
            boundary_layer_height_m=round(pbl, 1) if pbl is not None else None,
            soil_moisture_m3_m3=round(soil, 4) if soil is not None else None,
        )

        # 4. Forecast Horizons (e.g. 6h, 12h, 24h or up to forecast_hours)
        forecast_points: list[WeatherForecastPoint] = []
        hourly = payload.get("hourly", {})
        hourly_times = hourly.get("time", [])

        if hourly_times:
            target_hours = {6, 12, 24}
            if forecast_hours not in target_hours and forecast_hours > 0:
                target_hours.add(forecast_hours)

            for i, time_str in enumerate(hourly_times):
                f_dt = self._parse_iso_datetime(time_str)
                lead_sec = (f_dt - observed_at).total_seconds()
                lead_hr = int(round(lead_sec / 3600.0))

                if lead_hr in target_hours and lead_hr > 0:
                    f_temp = hourly.get("temperature_2m", [])[i] if i < len(hourly.get("temperature_2m", [])) else temp
                    f_rh = hourly.get("relative_humidity_2m", [])[i] if i < len(hourly.get("relative_humidity_2m", [])) else humidity
                    f_pres = hourly.get("surface_pressure", [])[i] if i < len(hourly.get("surface_pressure", [])) else pressure
                    f_precip = hourly.get("precipitation", [])[i] if i < len(hourly.get("precipitation", [])) else precip
                    f_cloud = hourly.get("cloud_cover", [])[i] if i < len(hourly.get("cloud_cover", [])) else cloud
                    f_pbl = hourly.get("boundary_layer_height", [])[i] if i < len(hourly.get("boundary_layer_height", [])) else pbl
                    f_soil = hourly.get("soil_moisture_0_to_1cm", [])[i] if i < len(hourly.get("soil_moisture_0_to_1cm", [])) else soil

                    f_speed = hourly.get("wind_speed_10m", [])[i] if i < len(hourly.get("wind_speed_10m", [])) else speed
                    f_dir = hourly.get("wind_direction_10m", [])[i] if i < len(hourly.get("wind_direction_10m", [])) else direction
                    f_gust = hourly.get("wind_gusts_10m", [])[i] if i < len(hourly.get("wind_gusts_10m", [])) else gust

                    f_wind = build_wind_vector(
                        speed_ms=float(f_speed) if f_speed is not None and math.isfinite(float(f_speed)) else 0.0,
                        direction_from_deg=float(f_dir) if f_dir is not None and math.isfinite(float(f_dir)) else 0.0,
                        gust_ms=float(f_gust) if f_gust is not None and math.isfinite(float(f_gust)) else None,
                    )
                    f_atmo = AtmosphereData(
                        temperature_c=round(float(f_temp), 2) if f_temp is not None else 20.0,
                        relative_humidity_pct=max(0.0, min(100.0, round(float(f_rh), 1))) if f_rh is not None else 50.0,
                        surface_pressure_hpa=self._validate_pressure(f_pres),
                        precipitation_mm=max(0.0, round(float(f_precip), 2)) if f_precip is not None else 0.0,
                        cloud_cover_pct=max(0.0, min(100.0, round(float(f_cloud), 1))) if f_cloud is not None else None,
                        boundary_layer_height_m=round(float(f_pbl), 1) if f_pbl is not None else None,
                        soil_moisture_m3_m3=round(float(f_soil), 4) if f_soil is not None else None,
                    )

                    forecast_points.append(
                        WeatherForecastPoint(
                            forecast_time=f_dt,
                            horizon_hours=lead_hr,
                            atmosphere=f_atmo,
                            wind=f_wind,
                        )
                    )

            forecast_points.sort(key=lambda pt: pt.horizon_hours)

        return CanonicalWeatherData(
            location=Coordinate(latitude=latitude, longitude=longitude),
            observed_at=observed_at,
            retrieved_at=now_utc,
            data_status=DataStatus.LIVE,
            data_quality=DataQuality.LIVE,
            atmosphere=atmosphere,
            wind=wind,
            forecast=forecast_points,
            provider=WeatherProviderInfo(name="open-meteo", model="best_match"),
        )

    def get_weather(
        self,
        latitude: float,
        longitude: float,
        forecast_hours: int = 24,
    ) -> CanonicalWeatherData:
        """Fetch real-time weather and forecast data from Open-Meteo."""
        params = self._build_request_params(latitude, longitude, forecast_hours)
        payload = self._execute_http_request(params)
        return self.parse_weather_response(
            payload=payload,
            latitude=latitude,
            longitude=longitude,
            forecast_hours=forecast_hours,
        )
