"""Structured JSON formatter for application log records."""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from packages.errors.base import AppError
from packages.logging.sanitizer import sanitize_log_data

# Standard logging attributes to exclude when discovering custom extra context.
STANDARD_RECORD_ATTRS = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "context",
        "error",
    }
)


class StructuredJsonFormatter(logging.Formatter):
    """Formats Python logging records into machine-readable JSON strings."""

    def __init__(self, *, include_traceback: bool = True) -> None:
        super().__init__()
        self.include_traceback = include_traceback

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record into a structured JSON string."""
        # 1. Base structured fields
        timestamp = datetime.fromtimestamp(record.created, tz=UTC).isoformat()
        message = record.getMessage()

        payload: dict[str, Any] = {
            "timestamp": timestamp,
            "level": record.levelname,
            "logger": record.name,
            "message": message,
        }

        # 2. Extract and sanitize structured context
        context: dict[str, Any] = {}

        # Context explicitly passed via extra={"context": {...}}
        explicit_context = getattr(record, "context", None)
        if isinstance(explicit_context, dict):
            context.update(explicit_context)

        # Additional arbitrary extra fields attached to record
        for attr, value in record.__dict__.items():
            if attr not in STANDARD_RECORD_ATTRS and not attr.startswith("_"):
                context[attr] = value

        if context:
            payload["context"] = sanitize_log_data(context)

        # 3. Extract and sanitize error / exception information
        error_info: dict[str, Any] = {}

        # Attached AppError or Exception object
        attached_error = getattr(record, "error", None)
        exc_obj = None

        if isinstance(attached_error, Exception):
            exc_obj = attached_error
        elif record.exc_info and isinstance(record.exc_info[1], Exception):
            exc_obj = record.exc_info[1]

        if exc_obj is not None:
            if isinstance(exc_obj, AppError):
                error_info = {
                    "code": str(exc_obj.code),
                    "category": exc_obj.category,
                    "message": exc_obj.message,
                    "retryable": exc_obj.retryable,
                    "details": sanitize_log_data(exc_obj.details),
                    "exception_type": exc_obj.__class__.__name__,
                }
            else:
                error_info = {
                    "code": "INTERNAL_ERROR",
                    "category": "general",
                    "message": str(exc_obj),
                    "retryable": False,
                    "details": {},
                    "exception_type": exc_obj.__class__.__name__,
                }

            # Preserve chained cause information if present
            if exc_obj.__cause__ is not None:
                cause = exc_obj.__cause__
                error_info["cause"] = {
                    "exception_type": cause.__class__.__name__,
                    "message": str(cause),
                }

            # Optional formatted traceback
            if self.include_traceback and record.exc_info:
                error_info["traceback"] = self.formatException(record.exc_info)

            payload["error"] = error_info
        elif record.exc_info and self.include_traceback:
            # Fallback for exc_info when exc_obj wasn't an Exception instance
            payload["error"] = {
                "traceback": self.formatException(record.exc_info),
            }

        return json.dumps(payload, default=str, ensure_ascii=False)
