"""Structured exceptions for data quality and ingestion integrity validation."""

from typing import Any

from packages.errors.codes import ErrorCode
from packages.errors.exceptions import ContractViolationError


class QualityIntegrityError(ContractViolationError):
    """Base exception for all data quality and dataset integrity failures."""

    default_code: ErrorCode | str = ErrorCode.CONTRACT_VIOLATION
    default_message: str = "Dataset quality or integrity validation failed."
    category: str = "data_quality"


class BrokenProvenanceError(QualityIntegrityError):
    """Raised when records or datasets lack verifiable source lineage or raw hashes."""

    default_code: ErrorCode | str = ErrorCode.CONTRACT_VIOLATION
    default_message: str = "Record or dataset has broken or missing provenance lineage."


class DatasetRejectedError(QualityIntegrityError):
    """Raised in strict mode when a dataset falls into REJECTED quality tier."""

    default_code: ErrorCode | str = ErrorCode.VALIDATION_ERROR
    default_message: str = (
        "Dataset quality is unacceptable and was rejected during strict audit."
    )

    def __init__(
        self,
        message: str | None = None,
        *,
        critical_violations: list[str] | None = None,
        details: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        det = dict(details or {})
        if critical_violations:
            det["critical_violations"] = critical_violations
        super().__init__(message=message, details=det, **kwargs)
        self.critical_violations = critical_violations or []
