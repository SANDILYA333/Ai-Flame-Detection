"""Logging configuration and logger acquisition."""

import logging
import sys
from collections.abc import Mapping
from typing import Any

from packages.config.settings import LogLevel
from packages.logging.formatters import StructuredJsonFormatter

LOGGER_PREFIX = "sih26162"


def get_logger(name: str | None = None) -> logging.Logger:
    """Acquire a canonical application logger.

    Args:
        name: Module or component name (typically __name__).

    Returns:
        A namespaced logging.Logger instance.
    """
    if not name:
        return logging.getLogger(LOGGER_PREFIX)

    if name.startswith(f"{LOGGER_PREFIX}."):
        return logging.getLogger(name)

    return logging.getLogger(f"{LOGGER_PREFIX}.{name}")


def _resolve_log_level(level: str | LogLevel | int | None) -> int:
    """Resolve level argument into a standard logging integer level."""
    if level is None:
        try:
            from packages.config import get_settings

            settings_level = get_settings().LOG_LEVEL
            return int(getattr(logging, settings_level.value, logging.INFO))
        except Exception:
            return logging.INFO

    if isinstance(level, int):
        return level

    if isinstance(level, LogLevel):
        return int(getattr(logging, level.value, logging.INFO))

    level_name = level.upper()
    return int(getattr(logging, level_name, logging.INFO))


def configure_logging(
    level: str | LogLevel | int | None = None,
    *,
    json_format: bool = True,
    stream: Any | None = None,
) -> None:
    """Configure the application logging infrastructure idempotently.

    Args:
        level: Minimum log level to emit. Defaults to packages.config.LOG_LEVEL.
        json_format: If True, uses JSON formatter. If False, standard text.
        stream: Target output stream (defaults to sys.stderr).
    """
    resolved_level = _resolve_log_level(level)
    target_stream = stream if stream is not None else sys.stderr

    root_logger = logging.getLogger()
    root_logger.setLevel(resolved_level)

    # Remove existing handlers to guarantee idempotency and avoid duplicate log lines
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        handler.close()

    handler = logging.StreamHandler(target_stream)
    handler.setLevel(resolved_level)

    if json_format:
        formatter: logging.Formatter = StructuredJsonFormatter()
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)


def log_with_context(
    logger: logging.Logger,
    level: int,
    msg: str,
    *,
    context: Mapping[str, Any] | None = None,
    error: Exception | None = None,
    exc_info: Any = None,
) -> None:
    """Helper to emit structured log records with explicit context and error objects.

    Args:
        logger: Target logger instance.
        level: Logging severity level (e.g. logging.INFO).
        msg: Human-readable log message.
        context: Safe structured contextual dictionary.
        error: Optional AppError or Exception object.
        exc_info: Optional boolean or sys.exc_info() tuple.
    """
    extra: dict[str, Any] = {}
    if context:
        extra["context"] = dict(context)
    if error:
        extra["error"] = error
        if exc_info is None:
            exc_info = error

    logger.log(level, msg, extra=extra, exc_info=exc_info)
