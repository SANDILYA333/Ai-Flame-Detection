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
