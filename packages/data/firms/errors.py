"""Specialized structured exceptions for NASA FIRMS API retrieval boundary."""

from typing import Any

from packages.errors.codes import ErrorCode
from packages.errors.exceptions import (
    ContractViolationError,
    ExternalServiceError,
    ServiceTimeoutError,
    ServiceUnavailableError,
)


class FirmsApiError(ExternalServiceError):
    """Base exception for all NASA FIRMS external retrieval failures."""

    default_code: ErrorCode | str = ErrorCode.EXTERNAL_SERVICE_ERROR
    default_message: str = "NASA FIRMS API communication failed."
    category: str = "external_firms"


class FirmsAuthenticationError(FirmsApiError):
    """Raised when FIRMS authentication fails (HTTP 401/403 or invalid key)."""

    default_code: ErrorCode | str = ErrorCode.EXTERNAL_SERVICE_ERROR
    default_message: str = (
        "NASA FIRMS authentication failed. Invalid MAP_KEY or unauthorized access."
    )
    default_retryable: bool = False


class FirmsRateLimitError(FirmsApiError):
    """Raised when NASA FIRMS rate limit or quota threshold is exceeded (HTTP 429)."""

    default_code: ErrorCode | str = ErrorCode.EXTERNAL_SERVICE_ERROR
    default_message: str = "NASA FIRMS rate limit exceeded."
    default_retryable: bool = True

    def __init__(
        self,
        message: str | None = None,
        *,
        retry_after_seconds: float | None = None,
        details: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        det = dict(details or {})
        if retry_after_seconds is not None:
            det["retry_after_seconds"] = retry_after_seconds
        super().__init__(message=message, details=det, **kwargs)
        self.retry_after_seconds = retry_after_seconds


class FirmsTimeoutError(ServiceTimeoutError, FirmsApiError):
    """Raised when an external request to NASA FIRMS times out."""

    default_code: ErrorCode | str = ErrorCode.SERVICE_TIMEOUT
    default_message: str = "NASA FIRMS API request timed out."
    default_retryable: bool = True


class FirmsUnavailableError(ServiceUnavailableError, FirmsApiError):
    """Raised when NASA FIRMS provider returns a transient server error (HTTP 5xx)."""

    default_code: ErrorCode | str = ErrorCode.SERVICE_UNAVAILABLE
    default_message: str = "NASA FIRMS API service is temporarily unavailable."
    default_retryable: bool = True


class FirmsMalformedPayloadError(ContractViolationError, FirmsApiError):
    """Raised when provider returns an invalid or malformed content payload."""

    default_code: ErrorCode | str = ErrorCode.CONTRACT_VIOLATION
    default_message: str = (
        "NASA FIRMS returned a malformed or unexpected response payload."
    )
    default_retryable: bool = False
