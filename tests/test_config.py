"""Unit tests for BE-003 operational configuration contracts."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from packages.config.settings import (
    AppEnvironment,
    LogLevel,
    Settings,
    get_settings,
    get_test_settings,
)


class TestOperationalConfiguration:
    """Test suite validating typed operational settings and secret protection."""

    def test_default_settings_instantiation(self) -> None:
        """TEST 1: Valid default configuration loads with correct types."""
        settings = get_test_settings()
        assert settings.ENVIRONMENT == AppEnvironment.DEVELOPMENT
        assert settings.DEBUG is False
        assert settings.API_HOST == "0.0.0.0"
        assert settings.API_PORT == 8000
        assert settings.LOG_LEVEL == LogLevel.INFO
        assert settings.POSTGRES_DB == "sih26162"
        assert settings.POSTGRES_USER == "sih_user"
        assert settings.POSTGRES_HOST == "localhost"
        assert settings.POSTGRES_PORT == 5432
        assert settings.DATABASE_POOL_SIZE == 5
        assert settings.DATABASE_MAX_OVERFLOW == 10

    def test_settings_immutability(self) -> None:
        """TEST 2: Settings instance is frozen and cannot be mutated at runtime."""
        settings = get_test_settings()
        with pytest.raises(ValidationError):
            # Attempting to assign to a frozen model raises ValidationError
            settings.API_PORT = 9000  # type: ignore[misc]

    def test_invalid_port_validation(self) -> None:
        """TEST 3: Port out of range raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            get_test_settings(API_PORT=70000)
        assert "API_PORT" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            get_test_settings(POSTGRES_PORT=0)
        assert "POSTGRES_PORT" in str(exc_info.value)

    def test_invalid_enum_validation(self) -> None:
        """TEST 4: Invalid enum value raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            get_test_settings(ENVIRONMENT="nonexistent_env")
        assert "ENVIRONMENT" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            get_test_settings(LOG_LEVEL="TRACE")
        assert "LOG_LEVEL" in str(exc_info.value)

    def test_environment_variable_override(self) -> None:
        """TEST 5: Environment variables override defaults correctly."""
        env_vars = {
            "ENVIRONMENT": "production",
            "DEBUG": "true",
            "API_PORT": "9090",
            "LOG_LEVEL": "WARNING",
            "POSTGRES_HOST": "db.internal.cloud",
            "POSTGRES_PORT": "5433",
            "POSTGRES_DB": "prod_db",
            "POSTGRES_USER": "prod_user",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            # Instantiate Settings directly so env vars are read
            settings = Settings(_env_file=None)
            assert settings.ENVIRONMENT == AppEnvironment.PRODUCTION
            assert settings.DEBUG is True
            assert settings.API_PORT == 9090
            assert settings.LOG_LEVEL == LogLevel.WARNING
            assert settings.POSTGRES_HOST == "db.internal.cloud"
            assert settings.POSTGRES_PORT == 5433
            assert settings.POSTGRES_DB == "prod_db"
            assert settings.POSTGRES_USER == "prod_user"

    def test_database_url_generation(self) -> None:
        """TEST 6: Database URL is correctly assembled with driver and credentials."""
        settings = get_test_settings(
            POSTGRES_USER="test_usr",
            POSTGRES_PASSWORD="test_secret_password",
            POSTGRES_HOST="10.0.0.5",
            POSTGRES_PORT=5432,
            POSTGRES_DB="test_db",
        )
        url = settings.get_database_url()
        expected = (
            "postgresql+psycopg://test_usr:test_secret_password@10.0.0.5:5432/test_db"
        )
        assert url == expected

    def test_database_url_explicit_override(self) -> None:
        """TEST 7: Explicit DATABASE_URL takes precedence and normalizes driver."""
        custom_url = "postgresql://custom_usr:custom_pass@cluster.db:5432/custom_db"
        settings = get_test_settings(DATABASE_URL=custom_url)
        url = settings.get_database_url()
        assert (
            url
            == "postgresql+psycopg://custom_usr:custom_pass@cluster.db:5432/custom_db"
        )

    def test_secret_redaction(self) -> None:
        """TEST 8: Secret values are masked in repr, str, and serialization."""
        secret_pass = "top_secret_db_pass_123"
        secret_key = "super_secret_app_key_456"
        settings = get_test_settings(
            POSTGRES_PASSWORD=secret_pass,
            SECRET_KEY=secret_key,
        )

        # repr and str masking
        assert secret_pass not in repr(settings)
        assert secret_key not in repr(settings)
        assert secret_pass not in str(settings)
        assert secret_key not in str(settings)

        # Direct access via get_secret_value succeeds
        assert settings.POSTGRES_PASSWORD.get_secret_value() == secret_pass
        assert settings.SECRET_KEY.get_secret_value() == secret_key

    def test_safe_database_url_masks_password(self) -> None:
        """TEST 9: get_safe_database_url() redacts passwords for display."""
        settings = get_test_settings(
            POSTGRES_USER="my_user",
            POSTGRES_PASSWORD="my_sensitive_password",
            POSTGRES_HOST="db.local",
            POSTGRES_PORT=5432,
            POSTGRES_DB="my_db",
        )
        safe_url = settings.get_safe_database_url()
        assert "my_sensitive_password" not in safe_url
        assert safe_url == "postgresql+psycopg://my_user:***@db.local:5432/my_db"

        # Also test with explicit DATABASE_URL
        settings_override = get_test_settings(
            DATABASE_URL="postgresql://user:secret_phrase@host:5432/db"
        )
        safe_override_url = settings_override.get_safe_database_url()
        assert "secret_phrase" not in safe_override_url
        assert safe_override_url == "postgresql+psycopg://user:***@host:5432/db"

    def test_no_scientific_parameters_in_operational_settings(self) -> None:
        """TEST 10: Verify operational settings contain ZERO scientific parameters."""
        scientific_forbidden_substrings = [
            "radius",
            "window",
            "threshold",
            "persistence_day",
            "attribution_dist",
            "confidence_cutoff",
            "cluster",
            "taxonomy",
            "benchmark",
        ]
        field_names = list(Settings.model_fields.keys())
        for field in field_names:
            for forbidden in scientific_forbidden_substrings:
                assert forbidden not in field.lower(), (
                    f"Forbidden scientific parameter '{field}' found in "
                    "operational settings"
                )

    def test_singleton_accessor_and_test_factory(self) -> None:
        """TEST 11: get_settings() is cached; get_test_settings() is isolated."""
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

        test_s1 = get_test_settings(API_PORT=9001)
        test_s2 = get_test_settings(API_PORT=9002)
        assert test_s1 is not test_s2
        assert test_s1.API_PORT == 9001
        assert test_s2.API_PORT == 9002
