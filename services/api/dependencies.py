"""FastAPI application dependencies and dependency injection providers."""

from packages.config.settings import Settings, get_settings


def get_app_settings() -> Settings:
    """Retrieve canonical operational settings instance."""
    return get_settings()
