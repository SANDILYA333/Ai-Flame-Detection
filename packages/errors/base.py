"""Base application error contract for SIH26162."""

from collections.abc import Mapping
from typing import Any

from packages.errors.codes import ErrorCode


class AppError(Exception):
    """Canonical base exception for all application-level errors.

    Provides stable machine-readable error codes, safe human-readable messages,
    optional structured context, and retryability classification.
    Transport-independent and suitable for propagation to API, worker, or pipeline
    layers.
    """

    default_code: ErrorCode | str = ErrorCode.INTERNAL_ERROR
    default_message: str = "An unexpected application error occurred."
    category: str = "general"
    default_retryable: bool = False

    def __init__(
        self,
        message: str | None = None,
        *,
        code: ErrorCode | str | None = None,
        details: Mapping[str, Any] | None = None,
        retryable: bool | None = None,
    ) -> None:
        self.message = message if message is not None else self.default_message
        self.code = code if code is not None else self.default_code
        self.details = dict(details) if details is not None else {}
        self.retryable = retryable if retryable is not None else self.default_retryable
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Return safe, structured dictionary representation suitable for serialization.

        Does not serialize tracebacks, credentials, or internal memory addresses.
        """
        return {
            "code": str(self.code),
            "message": self.message,
            "category": self.category,
            "retryable": self.retryable,
            "details": self.details,
        }

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"

    def __repr__(self) -> str:
        code_str = (
            self.code.value if isinstance(self.code, ErrorCode) else str(self.code)
        )
        return (
            f"{self.__class__.__name__}("
            f"code={code_str!r}, "
            f"message={self.message!r}, "
            f"retryable={self.retryable!r}, "
            f"details={self.details!r})"
        )
