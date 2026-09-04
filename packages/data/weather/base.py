"""Abstract base interface for meteorological data providers."""

from abc import ABC, abstractmethod

from packages.schemas.weather import CanonicalWeatherData


class BaseWeatherProvider(ABC):
    """Abstract interface for ingesting meteorological and wind observations."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the weather data provider service."""
        ...

    @abstractmethod
    def get_weather(
        self,
        latitude: float,
        longitude: float,
        forecast_hours: int = 24,
    ) -> CanonicalWeatherData:
        """Fetch current weather conditions and short-term forecast for coordinates.

        Args:
            latitude: Latitude in decimal degrees [-90.0, 90.0].
            longitude: Longitude in decimal degrees [-180.0, 180.0].
            forecast_hours: Forecast horizon in hours (e.g. 6, 12, 24).

        Returns:
            CanonicalWeatherData: Normalized weather and wind data model.

        Raises:
            ServiceTimeoutError: If external request times out.
            ServiceUnavailableError: If external service fails or returns 5xx.
            ExternalServiceError: If response is malformed or invalid.
        """
        ...
