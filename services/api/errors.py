"""Exception handlers for mapping AppError hierarchy to HTTP responses."""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from packages.errors import (
    AppError,
    ConflictError,
    DatabaseConnectionError,
    NotFoundError,
    ServiceTimeoutError,
    ServiceUnavailableError,
    ValidationError,
)
from packages.logging import get_logger, log_with_context

logger = get_logger("services.api.errors")
HTTP_422 = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)


def _status_code_for_error(exc: AppError) -> int:
    """Map typed application exception to appropriate HTTP status code."""
    if isinstance(exc, ValidationError):
        return HTTP_422
    if isinstance(exc, NotFoundError):
        return status.HTTP_404_NOT_FOUND
    if isinstance(exc, ConflictError):
        return status.HTTP_409_CONFLICT
    if isinstance(exc, ServiceTimeoutError):
        return status.HTTP_504_GATEWAY_TIMEOUT
    if isinstance(exc, (DatabaseConnectionError, ServiceUnavailableError)):
        return status.HTTP_503_SERVICE_UNAVAILABLE
    return status.HTTP_500_INTERNAL_SERVER_ERROR


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Handle domain/application AppError instances cleanly."""
    status_code = _status_code_for_error(exc)
    error_payload = exc.to_dict()

    log_with_context(
        logger,
        logging.WARNING if status_code < 500 else logging.ERROR,
        f"AppError during request {request.method} {request.url.path}: {exc.message}",
        context={
            "path": request.url.path,
            "method": request.method,
            "status_code": status_code,
            "error_code": str(exc.code),
            "category": exc.category,
        },
        error=exc,
    )

    return JSONResponse(
        status_code=status_code,
        content=error_payload,
    )


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle FastAPI / Pydantic RequestValidationError."""
    errors = exc.errors()
    log_with_context(
        logger,
        logging.INFO,
        f"Request validation failed for {request.method} {request.url.path}",
        context={
            "path": request.url.path,
            "method": request.method,
            "error_count": len(errors),
        },
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed.",
            "category": "validation",
            "retryable": False,
            "details": {"errors": errors},
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Safely catch unhandled exceptions without leaking internals or credentials."""
    log_with_context(
        logger,
        logging.ERROR,
        f"Unhandled exception during {request.method} {request.url.path}",
        context={
            "path": request.url.path,
            "method": request.method,
        },
        error=exc,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": "INTERNAL_ERROR",
            "message": "An internal server error occurred.",
            "category": "general",
            "retryable": False,
            "details": {},
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all canonical exception handlers on the FastAPI application."""
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)
