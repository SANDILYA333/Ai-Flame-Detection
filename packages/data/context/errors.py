"""Structured exceptions for external contextual dataset ingestion."""

from typing import Any

from packages.errors.codes import ErrorCode
from packages.errors.exceptions import ContractViolationError


class ContextDataError(ContractViolationError):
    """Base exception for all external context dataset ingestion failures."""

    default_code: ErrorCode | str = ErrorCode.CONTRACT_VIOLATION
    default_message: str = "Context dataset ingestion failed."
    category: str = "context_data"


class ContextParsingError(ContextDataError):
    """Raised when context input format (GeoJSON/CSV/JSON) is malformed."""

    default_code: ErrorCode | str = ErrorCode.CONTRACT_VIOLATION
    default_message: str = "Failed to parse context dataset input format."


class ContextValidationError(ContextDataError):
    """Raised when an individual context feature fails validation."""

    default_code: ErrorCode | str = ErrorCode.VALIDATION_ERROR
    default_message: str = "Context feature validation failed."

    def __init__(
        self,
        message: str | None = None,
        *,
        item_index: int | None = None,
        field_name: str | None = None,
        details: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        det = dict(details or {})
        if item_index is not None:
            det["item_index"] = item_index
        if field_name is not None:
            det["field_name"] = field_name
        super().__init__(message=message, details=det, **kwargs)
        self.item_index = item_index
        self.field_name = field_name
