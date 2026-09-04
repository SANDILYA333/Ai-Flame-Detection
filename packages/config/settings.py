"""Operational configuration contracts and settings loader.

Provides strongly-typed, validated, environment-driven operational configuration
for the SIH26162 platform using Pydantic Settings.

Operational settings cover runtime environments, ports, database connection parameters,
and operational secrets. Scientific parameters belong strictly to BE-004.
"""

from enum import StrEnum
from functools import lru_cache
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvironment(StrEnum):
    """Runtime deployment environments."""

    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(StrEnum):
    """Operational logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """Canonical operational configuration for SIH26162.

    All settings are loaded from environment variables and optionally overridden
    via a local .env file. Secrets are protected using SecretStr to prevent
    accidental exposure in logs, repr, or error traces.
    """

    model_config = SettingsConfigDict(
        frozen=True,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Runtime Environment
    ENVIRONMENT: AppEnvironment = Field(
        default=AppEnvironment.DEVELOPMENT,
        description="Application execution environment mode",
    )
    DEBUG: bool = Field(
        default=False,
        description="Enable debug mode",
    )
    API_HOST: str = Field(
        default="0.0.0.0",
        description="Host interface for API server",
    )
    API_PORT: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="Port for API server",
    )
    LOG_LEVEL: LogLevel = Field(
        default=LogLevel.INFO,
        description="Operational log level",
    )
    SECRET_KEY: SecretStr = Field(
        default=SecretStr("sih26162-dev-secret-key-change-in-prod"),
        description="Secret key for signing and operational tokens",
    )

    # CORS Configuration
    CORS_ORIGINS: list[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ],
        description="Allowed CORS origin URLs",
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(
        default=True,
        description="Whether to support credentials for cross-origin requests",
    )
    CORS_ALLOW_METHODS: list[str] = Field(
        default=["*"],
        description="Allowed HTTP methods for CORS requests",
    )
    CORS_ALLOW_HEADERS: list[str] = Field(
        default=["*"],
        description="Allowed HTTP headers for CORS requests",
    )

    # Database Configuration (PostgreSQL + PostGIS)
    POSTGRES_DB: str = Field(
        default="sih26162",
        min_length=1,
        description="Database name",
    )
    POSTGRES_USER: str = Field(
        default="sih_user",
        min_length=1,
        description="Database username",
    )
    POSTGRES_PASSWORD: SecretStr = Field(
        default=SecretStr("sih_dev_password"),
        description="Database password (secret)",
    )
    POSTGRES_HOST: str = Field(
        default="localhost",
        min_length=1,
        description="Database host address",
    )
    POSTGRES_PORT: int = Field(
        default=5432,
        ge=1,
        le=65535,
        description="Database port",
    )
    DATABASE_URL: SecretStr | None = Field(
        default=None,
        description="Explicit SQLAlchemy connection URL override",
    )
    DATABASE_POOL_SIZE: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Database connection pool size",
    )
    DATABASE_MAX_OVERFLOW: int = Field(
        default=10,
        ge=0,
        le=100,
        description="Database connection pool max overflow",
    )

    # NASA FIRMS API Configuration
    FIRMS_BASE_URL: str = Field(
        default="https://firms.modaps.eosdis.nasa.gov/api",
        description="Base URL endpoint for NASA FIRMS API",
    )
    FIRMS_MAP_KEY: SecretStr | None = Field(
        default=None,
        description="NASA FIRMS MAP_KEY authentication token (secret)",
    )
    FIRMS_TIMEOUT_SECONDS: float = Field(
        default=30.0,
        gt=0.0,
        le=300.0,
        description="HTTP request timeout in seconds for NASA FIRMS API",
    )
    FIRMS_MAX_RETRIES: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum transient failure retry attempts for FIRMS requests",
    )
    FIRMS_RETRY_BACKOFF_FACTOR: float = Field(
        default=0.5,
        ge=0.0,
        le=10.0,
        description="Exponential backoff base factor in seconds",
    )
    FIRMS_USER_AGENT: str = Field(
        default="SIH26162-Flare-Intelligence/1.0",
        description="Safe HTTP User-Agent identifier for NASA FIRMS requests",
    )

    # OpenStreetMap (OSM) Overpass API Configuration
    OSM_OVERPASS_URL: str = Field(
        default="https://overpass-api.de/api/interpreter",
        description="Overpass API interpreter endpoint for OSM geospatial queries",
    )
    OSM_USER_AGENT: str = Field(
        default="PyroSat-AI-Forest-Intelligence/1.0 (https://github.com/SANDILYA333/Ai-Flame-Detection)",
        description="HTTP User-Agent header for OpenStreetMap Overpass API requests",
    )
    OSM_TIMEOUT_SECONDS: float = Field(
        default=60.0,
        gt=0.0,
        le=300.0,
        description="HTTP request timeout in seconds for Overpass API requests",
    )
    OSM_MAX_RETRIES: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts for transient Overpass API failures",
    )
    OSM_RETRY_BACKOFF_FACTOR: float = Field(
        default=1.0,
        ge=0.0,
        le=10.0,
        description="Exponential backoff base factor in seconds for OSM requests",
    )

    # Open-Meteo Weather API Configuration (Phase 1 Wind Intelligence)
    OPEN_METEO_BASE_URL: str = Field(
        default="https://api.open-meteo.com",
        description="Base URL endpoint for Open-Meteo meteorological API",
    )
    OPEN_METEO_TIMEOUT_SECONDS: float = Field(
        default=10.0,
        gt=0.0,
        le=120.0,
        description="HTTP request timeout in seconds for Open-Meteo API",
    )
    OPEN_METEO_MAX_RETRIES: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Maximum retry attempts for transient Open-Meteo API failures",
    )
    OPEN_METEO_RETRY_BACKOFF_FACTOR: float = Field(
        default=0.5,
        ge=0.0,
        le=10.0,
        description="Exponential backoff base factor in seconds for Open-Meteo requests",
    )
    WEATHER_CACHE_TTL_SECONDS: int = Field(
        default=900,
        ge=0,
        le=86400,
        description="In-memory weather cache TTL in seconds (default 15 minutes)",
    )
    WEATHER_CACHE_MAX_ENTRIES: int = Field(
        default=2048,
        ge=16,
        le=100000,
        description="Maximum number of spatially bucketed weather cache entries",
    )

    # Forest Threat & Proximity Intelligence Configuration (Phase 3 & 4)
    FOREST_SEARCH_DISTANCE_KM: float = Field(
        default=10.0,
        gt=0.0,
        le=500.0,
        description="Default geographic search distance in km",
    )
    FOREST_THREAT_DISTANCE_KM: float = Field(
        default=10.0,
        gt=0.0,
        le=100.0,
        description="Distance threshold in km for proximity threat",
    )
    FOREST_AWARENESS_DISTANCE_KM: float = Field(
        default=10.0,
        gt=0.0,
        le=100.0,
        description="Distance in km for FOREST AWARENESS state",
    )
    FOREST_WARNING_DISTANCE_KM: float = Field(
        default=5.0,
        gt=0.0,
        le=50.0,
        description="Distance in km for FOREST WARNING state",
    )
    FOREST_CRITICAL_DISTANCE_KM: float = Field(
        default=2.0,
        ge=0.0,
        le=50.0,
        description="Distance in km for CRITICAL threat level",
    )
    FOREST_HIGH_DISTANCE_KM: float = Field(
        default=2.5,
        ge=0.0,
        le=50.0,
        description="Distance in km for HIGH threat level",
    )
    FOREST_MODERATE_DISTANCE_KM: float = Field(
        default=5.0,
        ge=0.0,
        le=100.0,
        description="Distance in km for MODERATE threat level",
    )

    @property
    def FOREST_SEARCH_RADIUS_KM(self) -> float:
        """Alias for FOREST_SEARCH_DISTANCE_KM."""
        return self.FOREST_SEARCH_DISTANCE_KM

    @property
    def FOREST_THREAT_RADIUS_KM(self) -> float:
        """Alias for FOREST_THREAT_DISTANCE_KM."""
        return self.FOREST_THREAT_DISTANCE_KM

    @property
    def FOREST_AWARENESS_RADIUS_KM(self) -> float:
        """Alias for FOREST_AWARENESS_DISTANCE_KM."""
        return self.FOREST_AWARENESS_DISTANCE_KM

    @property
    def FOREST_WARNING_RADIUS_KM(self) -> float:
        """Alias for FOREST_WARNING_DISTANCE_KM."""
        return self.FOREST_WARNING_DISTANCE_KM

    @property
    def FOREST_CRITICAL_RADIUS_KM(self) -> float:
        """Alias for FOREST_CRITICAL_DISTANCE_KM."""
        return self.FOREST_CRITICAL_DISTANCE_KM

    @property
    def FOREST_HIGH_RADIUS_KM(self) -> float:
        """Alias for FOREST_HIGH_DISTANCE_KM."""
        return self.FOREST_HIGH_DISTANCE_KM

    @property
    def FOREST_MODERATE_RADIUS_KM(self) -> float:
        """Alias for FOREST_MODERATE_DISTANCE_KM."""
        return self.FOREST_MODERATE_DISTANCE_KM

    # Redis Job Queue Configuration (WORK-002 / Section 21)
    REDIS_URL: SecretStr | None = Field(
        default=None,
        description="Explicit Redis connection URL (e.g. redis://localhost:6379/0)",
    )
    REDIS_HOST: str = Field(
        default="localhost",
        min_length=1,
        description="Redis server host",
    )
    REDIS_PORT: int = Field(
        default=6379,
        ge=1,
        le=65535,
        description="Redis server port",
    )
    REDIS_DB: int = Field(
        default=0,
        ge=0,
        le=15,
        description="Redis database index",
    )
    REDIS_PASSWORD: SecretStr | None = Field(
        default=None,
        description="Redis authentication password (secret)",
    )
    REDIS_TIMEOUT_SECONDS: float = Field(
        default=5.0,
        gt=0.0,
        le=60.0,
        description="Redis connection/operation timeout in seconds",
    )
    REDIS_QUEUE_KEY_PREFIX: str = Field(
        default="sih26162:queue",
        min_length=1,
        description="Prefix key namespace for Redis job queues",
    )

    # Emergency Notification & Dispatch Configuration
    NOTIFICATION_MODE: str = Field(
        default="simulation",
        description="Notification execution mode: 'simulation' or 'live'",
    )
    SMS_PROVIDER: str = Field(
        default="fast2sms",
        description="Active SMS messaging provider identifier",
    )
    WHATSAPP_PROVIDER: str = Field(
        default="richautomate",
        description="Active WhatsApp messaging provider identifier",
    )
    FAST2SMS_API_KEY: SecretStr | None = Field(
        default=None,
        description="Fast2SMS gateway API authorization key (secret)",
    )
    FAST2SMS_ENABLED: bool = Field(
        default=True,
        description="Whether Fast2SMS integration is enabled",
    )
    FAST2SMS_BASE_URL: str = Field(
        default="https://www.fast2sms.com/dev/bulkV2",
        description="Fast2SMS bulk API endpoint",
    )
    RICHAUTOMATE_API_KEY: SecretStr | None = Field(
        default=None,
        description="RichAutomate WhatsApp gateway API key (secret)",
    )
    RICHAUTOMATE_BASE_URL: str = Field(
        default="https://richautomate.in/api/v1",
        description="RichAutomate WhatsApp gateway base endpoint",
    )
    RICHAUTOMATE_ENABLED: bool = Field(
        default=True,
        description="Whether RichAutomate integration is enabled",
    )
    NOTIFICATION_TIMEOUT_SECONDS: float = Field(
        default=10.0,
        ge=1.0,
        le=60.0,
        description="Timeout in seconds for external notification provider requests",
    )
    NOTIFICATION_MAX_RETRIES: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Maximum retry attempts for transient provider failures",
    )
    NOTIFICATION_RETRY_BACKOFF_SECONDS: float = Field(
        default=0.1,
        ge=0.01,
        le=5.0,
        description="Base exponential backoff interval in seconds",
    )
    EMERGENCY_RESPONSE_ENABLED: bool = Field(
        default=True,
        description="Global feature flag for emergency response & regulation",
    )
    EMERGENCY_AUTO_ESCALATION_ENABLED: bool = Field(
        default=True,
        description="Whether automatic emergency escalation is permitted",
    )
    EMERGENCY_REVIEW_MIN_CONFIDENCE: float = Field(
        default=0.94,
        ge=0.0,
        le=1.0,
        description="Calibrated confidence boundary requiring operator review",
    )
    EMERGENCY_AUTO_ESCALATION_MIN_CONFIDENCE: float = Field(
        default=0.98,
        ge=0.0,
        le=1.0,
        description="Calibrated confidence boundary permitting automatic escalation",
    )

    # Google Gemini AI Configuration (AGNI Phase 2 Command Interpretation)
    GEMINI_API_KEY: SecretStr | None = Field(
        default=None,
        description="Google Gemini API key for AGNI natural language voice command interpretation",
    )
    GEMINI_MODEL: str = Field(
        default="gemini-2.5-flash",
        description="Google Gemini model identifier for AGNI interpretation",
    )
    GEMINI_TIMEOUT_SECONDS: float = Field(
        default=15.0,
        gt=0.0,
        le=60.0,
        description="HTTP request timeout in seconds for Gemini API requests",
    )

    def get_redis_url(self) -> str:
        """Construct full Redis connection URL."""
        if self.REDIS_URL is not None:
            return self.REDIS_URL.get_secret_value()
        if self.REDIS_PASSWORD is not None:
            pwd = self.REDIS_PASSWORD.get_secret_value()
            return f"redis://:{pwd}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    def get_database_url(self, driver: str = "postgresql+psycopg") -> str:
        """Construct full plaintext database connection URL for driver connections.

        Args:
            driver: The SQLAlchemy database dialect/driver prefix.

        Returns:
            The complete connection URL string with password resolved.
        """
        if self.DATABASE_URL is not None:
            url_str = self.DATABASE_URL.get_secret_value()
            if url_str.startswith("postgresql://"):
                return url_str.replace("postgresql://", f"{driver}://", 1)
            if url_str.startswith("postgres://"):
                return url_str.replace("postgres://", f"{driver}://", 1)
            return url_str

        password = self.POSTGRES_PASSWORD.get_secret_value()
        return (
            f"{driver}://{self.POSTGRES_USER}:{password}@"
            f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    def get_safe_database_url(self, driver: str = "postgresql+psycopg") -> str:
        """Construct database connection URL with credentials redacted for logging.

        Args:
            driver: The SQLAlchemy database dialect/driver prefix.

        Returns:
            The connection URL string with the password masked as '***'.
        """
        if self.DATABASE_URL is not None:
            raw_url = self.DATABASE_URL.get_secret_value()
            try:
                parsed = urlsplit(raw_url)
                if parsed.password:
                    safe_netloc = parsed.netloc.replace(f":{parsed.password}@", ":***@")
                    parsed = parsed._replace(netloc=safe_netloc)
                safe_url = urlunsplit(parsed)
                if safe_url.startswith("postgresql://"):
                    return safe_url.replace("postgresql://", f"{driver}://", 1)
                if safe_url.startswith("postgres://"):
                    return safe_url.replace("postgres://", f"{driver}://", 1)
                return safe_url
            except Exception:
                return f"{driver}://***:***@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

        return (
            f"{driver}://{self.POSTGRES_USER}:***@"
            f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get the cached singleton operational configuration instance."""
    return Settings()


def get_test_settings(**overrides: Any) -> Settings:
    """Create an isolated, non-cached Settings instance for deterministic testing.

    Args:
        **overrides: Field values to override for the test configuration.

    Returns:
        A new, validated Settings instance.
    """
    return Settings(_env_file=None, **overrides)
