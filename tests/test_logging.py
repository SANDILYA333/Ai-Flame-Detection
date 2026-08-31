"""Unit tests for BE-006 canonical structured logging system."""

import io
import json
import logging
import sys
from datetime import datetime

from pydantic import SecretStr

from packages.errors import DatabaseConnectionError, ErrorCode, NotFoundError
from packages.logging import (
    configure_logging,
    get_logger,
    log_with_context,
    sanitize_log_data,
)


class TestStructuredLogging:
    """Test suite for structured logging, JSON formatting, and secret safety."""

    def test_logger_acquisition_naming(self) -> None:
        """TEST 1: get_logger names loggers under sih26162 namespace."""
        logger_root = get_logger()
        assert logger_root.name == "sih26162"

        logger_mod = get_logger("packages.config")
        assert logger_mod.name == "sih26162.packages.config"

        # Already prefixed names should not be double-prefixed
        logger_prefixed = get_logger("sih26162.custom")
        assert logger_prefixed.name == "sih26162.custom"

    def test_log_levels_emission(self) -> None:
        """TEST 2: Standard log levels emit correct level names in JSON."""
        stream = io.StringIO()
        configure_logging(level=logging.DEBUG, json_format=True, stream=stream)
        logger = get_logger("test_levels")

        levels = [
            (logging.DEBUG, logger.debug, "debug test"),
            (logging.INFO, logger.info, "info test"),
            (logging.WARNING, logger.warning, "warning test"),
            (logging.ERROR, logger.error, "error test"),
            (logging.CRITICAL, logger.critical, "critical test"),
        ]

        for _, log_fn, msg in levels:
            stream.truncate(0)
            stream.seek(0)
            log_fn(msg)
            output = stream.getvalue().strip()
            data = json.loads(output)
            assert data["message"] == msg
            assert data["level"] == log_fn.__name__.upper()

    def test_structured_json_schema(self) -> None:
        """TEST 3: Emitted JSON contains required base fields and ISO timestamp."""
        stream = io.StringIO()
        configure_logging(level=logging.INFO, json_format=True, stream=stream)
        logger = get_logger("test_schema")

        logger.info("Operational event triggered")
        output = stream.getvalue().strip()
        data = json.loads(output)

        assert "timestamp" in data
        assert "level" in data
        assert "logger" in data
        assert "message" in data

        assert data["level"] == "INFO"
        assert data["logger"] == "sih26162.test_schema"
        assert data["message"] == "Operational event triggered"

        # Validate timestamp parses as ISO datetime
        dt = datetime.fromisoformat(data["timestamp"])
        assert dt.tzinfo is not None

    def test_contextual_metadata_attachment(self) -> None:
        """TEST 4: Context metadata is safely attached and emitted in context field."""
        stream = io.StringIO()
        configure_logging(level=logging.INFO, json_format=True, stream=stream)
        logger = get_logger("test_context")

        logger.info(
            "Processed detection batch",
            extra={"context": {"batch_id": "b-987", "record_count": 150}},
        )
        output = stream.getvalue().strip()
        data = json.loads(output)

        assert "context" in data
        assert data["context"]["batch_id"] == "b-987"
        assert data["context"]["record_count"] == 150

    def test_app_error_integration(self) -> None:
        """TEST 5: BE-005 AppError is serialized with code, category, and details."""
        stream = io.StringIO()
        configure_logging(level=logging.ERROR, json_format=True, stream=stream)
        logger = get_logger("test_error")

        err = NotFoundError(
            "Fire event not found in index",
            details={"event_id": "evt-555", "table": "fire_events"},
        )
        log_with_context(logger, logging.ERROR, "Lookup failed", error=err)

        output = stream.getvalue().strip()
        data = json.loads(output)

        assert data["message"] == "Lookup failed"
        assert "error" in data
        assert data["error"]["code"] == "RESOURCE_NOT_FOUND"
        assert data["error"]["category"] == "database"
        assert data["error"]["message"] == "Fire event not found in index"
        assert data["error"]["retryable"] is False
        assert data["error"]["details"] == {
            "event_id": "evt-555",
            "table": "fire_events",
        }
        assert data["error"]["exception_type"] == "NotFoundError"

    def test_exception_chaining_diagnostics(self) -> None:
        """TEST 6: Chained exception causes are recorded in error diagnostics."""
        stream = io.StringIO()
        configure_logging(level=logging.ERROR, json_format=True, stream=stream)
        logger = get_logger("test_chain")

        try:
            try:
                raise ConnectionResetError("TCP connection reset by peer")
            except ConnectionResetError as raw_exc:
                raise DatabaseConnectionError("Database connection lost") from raw_exc
        except DatabaseConnectionError as app_exc:
            log_with_context(logger, logging.ERROR, "DB failure", error=app_exc)

        output = stream.getvalue().strip()
        data = json.loads(output)

        assert "error" in data
        assert data["error"]["code"] == ErrorCode.DATABASE_CONNECTION_ERROR
        assert data["error"]["retryable"] is True
        assert "cause" in data["error"]
        assert data["error"]["cause"]["exception_type"] == "ConnectionResetError"
        assert "TCP connection reset" in data["error"]["cause"]["message"]

    def test_secret_scrubbing_in_context_and_payloads(self) -> None:
        """TEST 7: Sensitive keys and SecretStr instances are masked in log output."""
        stream = io.StringIO()
        configure_logging(level=logging.INFO, json_format=True, stream=stream)
        logger = get_logger("test_secrets")

        fake_secret_key = "fake-api-key-123"
        fake_db_pass = "top-secret-password-xyz"

        payload = {
            "user": "sih_user",
            "api_key": fake_secret_key,
            "nested": {
                "postgres_password": fake_db_pass,
                "secret_token": SecretStr("masked-token-value"),
                "safe_field": "visible_value",
            },
        }

        logger.info("User logged in", extra={"context": payload})
        output = stream.getvalue().strip()
        data = json.loads(output)

        assert fake_secret_key not in output
        assert fake_db_pass not in output
        assert "masked-token-value" not in output

        assert data["context"]["user"] == "sih_user"
        assert data["context"]["api_key"] == "[REDACTED]"
        assert data["context"]["nested"]["postgres_password"] == "[REDACTED]"
        assert data["context"]["nested"]["secret_token"] == "[REDACTED]"
        assert data["context"]["nested"]["safe_field"] == "visible_value"

    def test_sanitizer_standalone(self) -> None:
        """TEST 8: Standalone sanitize_log_data handles primitives and collections."""
        raw = {
            "token": "sensitive1",
            "list": [{"password": "sensitive2"}, "safe"],
            "secret_obj": SecretStr("sensitive3"),
            "safe_num": 42,
        }
        sanitized = sanitize_log_data(raw)
        assert sanitized == {
            "token": "[REDACTED]",
            "list": [{"password": "[REDACTED]"}, "safe"],
            "secret_obj": "[REDACTED]",
            "safe_num": 42,
        }

    def test_idempotent_configuration(self) -> None:
        """TEST 9: Repeated configure_logging calls do not duplicate handlers."""
        stream = io.StringIO()
        configure_logging(level=logging.INFO, json_format=True, stream=stream)
        configure_logging(level=logging.INFO, json_format=True, stream=stream)
        configure_logging(level=logging.INFO, json_format=True, stream=stream)

        logger = get_logger("test_idempotent")
        logger.info("Single line event")

        lines = [line for line in stream.getvalue().splitlines() if line.strip()]
        assert len(lines) == 1

    def test_transport_independence(self) -> None:
        """TEST 10: Logging package has no dependency on web frameworks."""
        import packages.logging
        import packages.logging.config
        import packages.logging.formatters
        import packages.logging.sanitizer

        for mod in [
            packages.logging,
            packages.logging.config,
            packages.logging.formatters,
            packages.logging.sanitizer,
        ]:
            mod_vars = dir(mod)
            assert "HTTPException" not in mod_vars
            assert "Request" not in mod_vars
            assert "Response" not in mod_vars

        import subprocess

        cmd = [
            sys.executable,
            "-c",
            "import packages.logging, sys; "
            "libs = ['fastapi', 'starlette', 'requests', 'httpx', 'aiohttp']; "
            "assert all(lib not in sys.modules for lib in libs)",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 0, f"Imported web framework: {result.stderr}"
