"""Unit tests for BE-005 application error taxonomy and exception contracts."""

import sys

from packages.errors import (
    AppError,
    ConfigurationError,
    ConflictError,
    ContractViolationError,
    DatabaseConnectionError,
    DatabaseError,
    DomainError,
    ErrorCode,
    ExternalServiceError,
    InvalidConfigurationError,
    InvariantViolationError,
    JobExecutionError,
    MissingConfigurationError,
    NotFoundError,
    PipelineError,
    ServiceTimeoutError,
    ServiceUnavailableError,
    ValidationError,
)


class TestApplicationErrorFramework:
    """Test suite validating canonical error taxonomy, hierarchy, and serialization."""

    def test_base_app_error_construction(self) -> None:
        """TEST 1: Base AppError constructs with defaults and custom parameters."""
        err_default = AppError()
        assert err_default.code == ErrorCode.INTERNAL_ERROR
        assert err_default.message == "An unexpected application error occurred."
        assert err_default.category == "general"
        assert err_default.retryable is False
        assert err_default.details == {}

        err_custom = AppError(
            "Custom failure message",
            code=ErrorCode.VALIDATION_ERROR,
            details={"field": "coordinate", "value": -95.0},
            retryable=True,
        )
        assert err_custom.message == "Custom failure message"
        assert err_custom.code == ErrorCode.VALIDATION_ERROR
        assert err_custom.retryable is True
        assert err_custom.details == {"field": "coordinate", "value": -95.0}

    def test_app_error_str_and_repr(self) -> None:
        """TEST 2: str() and repr() representations are clear and informative."""
        err = AppError("File not found", code=ErrorCode.RESOURCE_NOT_FOUND)
        assert str(err) == "[RESOURCE_NOT_FOUND] File not found"
        assert "AppError" in repr(err)
        assert "code='RESOURCE_NOT_FOUND'" in repr(err)
        assert "message='File not found'" in repr(err)

    def test_error_hierarchy_instantiation(self) -> None:
        """TEST 3: Categorized exception classes instantiate with proper defaults."""
        cases: list[tuple[type[AppError], ErrorCode | str, str, bool]] = [
            (
                ConfigurationError,
                ErrorCode.CONFIGURATION_ERROR,
                "configuration",
                False,
            ),
            (
                MissingConfigurationError,
                ErrorCode.MISSING_CONFIGURATION,
                "configuration",
                False,
            ),
            (
                InvalidConfigurationError,
                ErrorCode.INVALID_CONFIGURATION,
                "configuration",
                False,
            ),
            (ValidationError, ErrorCode.VALIDATION_ERROR, "validation", False),
            (
                ContractViolationError,
                ErrorCode.CONTRACT_VIOLATION,
                "validation",
                False,
            ),
            (DatabaseError, ErrorCode.DATABASE_ERROR, "database", False),
            (
                DatabaseConnectionError,
                ErrorCode.DATABASE_CONNECTION_ERROR,
                "database",
                True,
            ),
            (NotFoundError, ErrorCode.RESOURCE_NOT_FOUND, "database", False),
            (ConflictError, ErrorCode.RESOURCE_CONFLICT, "database", False),
            (
                ExternalServiceError,
                ErrorCode.EXTERNAL_SERVICE_ERROR,
                "external",
                False,
            ),
            (
                ServiceUnavailableError,
                ErrorCode.SERVICE_UNAVAILABLE,
                "external",
                True,
            ),
            (
                ServiceTimeoutError,
                ErrorCode.SERVICE_TIMEOUT,
                "external",
                True,
            ),
            (DomainError, ErrorCode.DOMAIN_ERROR, "domain", False),
            (
                InvariantViolationError,
                ErrorCode.INVARIANT_VIOLATION,
                "domain",
                False,
            ),
            (PipelineError, ErrorCode.PIPELINE_ERROR, "pipeline", False),
            (
                JobExecutionError,
                ErrorCode.JOB_EXECUTION_ERROR,
                "pipeline",
                False,
            ),
        ]

        for exc_cls, expected_code, expected_cat, expected_retry in cases:
            exc = exc_cls()
            assert exc.code == expected_code, f"{exc_cls.__name__} code mismatch"
            assert exc.category == expected_cat, f"{exc_cls.__name__} category mismatch"
            assert exc.retryable is expected_retry, (
                f"{exc_cls.__name__} retryable mismatch"
            )

    def test_error_catchability_via_base(self) -> None:
        """TEST 4: All categorized exceptions can be caught via AppError."""
        subclasses = [
            ConfigurationError("Config missing"),
            ValidationError("Bad input"),
            DatabaseError("DB error"),
            ExternalServiceError("API down"),
            DomainError("Domain violation"),
            PipelineError("Pipeline failed"),
        ]

        for exc in subclasses:
            try:
                raise exc
            except AppError as caught:
                assert caught is exc
                assert issubclass(type(caught), Exception)

    def test_exception_chaining_preserves_cause(self) -> None:
        """TEST 5: Standard Python exception chaining preserves original cause."""
        original_exc = ConnectionRefusedError("Connection refused on 5432")
        try:
            try:
                raise original_exc
            except ConnectionRefusedError as e:
                raise DatabaseConnectionError(
                    "Database is unreachable at localhost:5432"
                ) from e
        except DatabaseConnectionError as app_exc:
            assert app_exc.__cause__ is original_exc
            assert "Connection refused" in str(app_exc.__cause__)

    def test_to_dict_serialization(self) -> None:
        """TEST 6: to_dict() produces safe, serializable structured dictionary."""
        err = NotFoundError(
            "Detection record not found",
            details={"detection_id": "det-12345", "source": "firms_modis"},
        )
        serialized = err.to_dict()

        assert serialized == {
            "code": "RESOURCE_NOT_FOUND",
            "message": "Detection record not found",
            "category": "database",
            "retryable": False,
            "details": {
                "detection_id": "det-12345",
                "source": "firms_modis",
            },
        }
        # Ensure tracebacks are not in dictionary
        assert "traceback" not in serialized

    def test_retryability_overrides(self) -> None:
        """TEST 7: Explicit retryable parameter overrides category default."""
        err_non_retryable = DatabaseConnectionError(
            "Permanently invalid auth", retryable=False
        )
        assert err_non_retryable.retryable is False

        err_retryable_override = ValidationError(
            "Transient validation lock", retryable=True
        )
        assert err_retryable_override.retryable is True

    def test_secret_safety_in_error_payloads(self) -> None:
        """TEST 8: Error representations do not automatically leak secrets."""
        safe_message = "Authentication failed for user sih_user"
        err = DatabaseConnectionError(
            safe_message,
            details={"user": "sih_user", "host": "localhost", "port": 5432},
        )
        # Verify message and serialized output contain safe details only
        assert "sih_dev_password" not in str(err)
        assert "sih_dev_password" not in repr(err)
        assert "sih_dev_password" not in str(err.to_dict())

    def test_transport_independence(self) -> None:
        """TEST 9: Error package has zero HTTP or web framework dependencies."""
        import packages.errors
        import packages.errors.base
        import packages.errors.codes
        import packages.errors.exceptions

        for mod in [
            packages.errors,
            packages.errors.base,
            packages.errors.codes,
            packages.errors.exceptions,
        ]:
            mod_vars = dir(mod)
            assert "HTTPException" not in mod_vars
            assert "Response" not in mod_vars
            assert "Request" not in mod_vars

        # Confirm no web frameworks were imported into sys.modules by packages.errors
        for web_lib in ["fastapi", "starlette", "requests", "httpx", "aiohttp"]:
            assert web_lib not in sys.modules

    def test_native_exceptions_not_altered(self) -> None:
        """TEST 10: Standard Python exceptions are not subclasses of AppError."""
        native_exceptions = [
            KeyError,
            ValueError,
            TypeError,
            KeyboardInterrupt,
            SystemExit,
            MemoryError,
        ]
        for exc_cls in native_exceptions:
            assert not issubclass(exc_cls, AppError)
