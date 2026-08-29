"""Canonical structured logging package for SIH26162.

Provides the canonical logger acquisition factory, structured JSON formatting,
secret sanitization, and idempotent logging configuration.
"""

from packages.logging.config import configure_logging, get_logger, log_with_context
from packages.logging.formatters import StructuredJsonFormatter
from packages.logging.sanitizer import sanitize_log_data

__all__ = [
    "StructuredJsonFormatter",
    "configure_logging",
    "get_logger",
    "log_with_context",
    "sanitize_log_data",
]
