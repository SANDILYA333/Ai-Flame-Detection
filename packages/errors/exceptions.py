"""Categorized application exceptions for SIH26162.

Provides specific domain, configuration, database, validation, external service,
and pipeline exception classes derived from the canonical AppError foundation.
"""

from packages.errors.base import AppError
from packages.errors.codes import ErrorCode

# ==============================================================================
# Configuration Exceptions
# ==============================================================================


class ConfigurationError(AppError):
    """Raised when an operational or system configuration error occurs."""

    default_code: ErrorCode | str = ErrorCode.CONFIGURATION_ERROR
    default_message: str = "A configuration error occurred."
    category: str = "configuration"


class MissingConfigurationError(ConfigurationError):
    """Raised when a required operational setting or secret is missing."""

    default_code: ErrorCode | str = ErrorCode.MISSING_CONFIGURATION
    default_message: str = "A required configuration setting is missing."


class InvalidConfigurationError(ConfigurationError):
    """Raised when a configuration setting contains an invalid value or type."""

    default_code: ErrorCode | str = ErrorCode.INVALID_CONFIGURATION
    default_message: str = "A configuration setting contains an invalid value."


# ==============================================================================
# Validation Exceptions
# ==============================================================================


class ValidationError(AppError):
    """Raised when input data or parameter validation fails."""

    default_code: ErrorCode | str = ErrorCode.VALIDATION_ERROR
    default_message: str = "Input data validation failed."
    category: str = "validation"


class ContractViolationError(ValidationError):
    """Raised when a canonical domain contract or boundary invariant is violated."""

    default_code: ErrorCode | str = ErrorCode.CONTRACT_VIOLATION
    default_message: str = "A canonical domain contract was violated."


# ==============================================================================
# Database / Storage Exceptions
# ==============================================================================


class DatabaseError(AppError):
    """Raised when a database or persistence layer failure occurs."""

    default_code: ErrorCode | str = ErrorCode.DATABASE_ERROR
    default_message: str = "A database operation failed."
    category: str = "database"


class DatabaseConnectionError(DatabaseError):
    """Raised when connectivity to the database service cannot be established."""

    default_code: ErrorCode | str = ErrorCode.DATABASE_CONNECTION_ERROR
    default_message: str = "Could not establish database connection."
    default_retryable: bool = True


class NotFoundError(DatabaseError):
    """Raised when a requested resource or record cannot be found."""

    default_code: ErrorCode | str = ErrorCode.RESOURCE_NOT_FOUND
    default_message: str = "The requested resource was not found."


class ConflictError(DatabaseError):
    """Raised when a unique constraint or resource state conflict occurs."""

    default_code: ErrorCode | str = ErrorCode.RESOURCE_CONFLICT
    default_message: str = "A resource state conflict occurred."


# ==============================================================================
# External Service & Provider Exceptions
# ==============================================================================


class ExternalServiceError(AppError):
    """Raised when an external service, data provider, or API call fails."""

    default_code: ErrorCode | str = ErrorCode.EXTERNAL_SERVICE_ERROR
    default_message: str = "An external service dependency failed."
    category: str = "external"


class ServiceUnavailableError(ExternalServiceError):
    """Raised when an external service is temporarily unavailable or returning 5xx."""

    default_code: ErrorCode | str = ErrorCode.SERVICE_UNAVAILABLE
    default_message: str = "The external service is temporarily unavailable."
    default_retryable: bool = True


class ServiceTimeoutError(ExternalServiceError):
    """Raised when an external network request or API call times out."""

    default_code: ErrorCode | str = ErrorCode.SERVICE_TIMEOUT
    default_message: str = "The external service request timed out."
    default_retryable: bool = True


# ==============================================================================
# Domain Exceptions
# ==============================================================================


class DomainError(AppError):
    """Raised when an application or domain rule is violated."""

    default_code: ErrorCode | str = ErrorCode.DOMAIN_ERROR
    default_message: str = "A domain invariant was violated."
    category: str = "domain"


class InvariantViolationError(DomainError):
    """Raised when an immutable architectural or domain invariant is violated."""

    default_code: ErrorCode | str = ErrorCode.INVARIANT_VIOLATION
    default_message: str = "An architectural invariant was violated."


# ==============================================================================
# Pipeline & Background Processing Exceptions
# ==============================================================================


class PipelineError(AppError):
    """Raised when a processing pipeline or batch execution fails."""

    default_code: ErrorCode | str = ErrorCode.PIPELINE_ERROR
    default_message: str = "A processing pipeline execution failed."
    category: str = "pipeline"


class JobExecutionError(PipelineError):
    """Raised when an asynchronous background job fails during execution."""

    default_code: ErrorCode | str = ErrorCode.JOB_EXECUTION_ERROR
    default_message: str = "A background job execution failed."
