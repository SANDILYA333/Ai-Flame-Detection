# Structured Logging System (BE-006)

The platform provides a centralized, strongly-typed structured logging system defined in `packages/logging/` built upon Python's standard library `logging`.

---

## 1. Architectural Principles

- **Standard Library Foundation**: Built purely on Python's built-in `logging` infrastructure with a custom `StructuredJsonFormatter`.
- **Machine-Readable Structure**: Emits structured JSON events with standardized timestamps, levels, logger names, contextual metadata, and error details.
- **Automatic Secret Sanitization**: Automatically intercepts and redacts sensitive keys (`password`, `token`, `secret`, `api_key`, `auth`) and `SecretStr` objects to prevent credential leaks.
- **BE-005 Error Integration**: Automatically formats `AppError` exceptions, extracting machine-readable error codes, categories, safe messages, structured details, and chained underlying causes.
- **Transport Independence**: Contains zero HTTP or web framework coupling.

---

## 2. Emitted JSON Record Schema

```json
{
  "timestamp": "2026-08-29T12:00:00.000000+00:00",
  "level": "INFO",
  "logger": "sih26162.packages.config",
  "message": "Configuration loaded successfully",
  "context": {
    "environment": "development",
    "api_port": 8000
  },
  "error": {
    "code": "DATABASE_CONNECTION_ERROR",
    "category": "database",
    "message": "Could not establish connection",
    "retryable": true,
    "details": {
      "host": "localhost",
      "port": 5432
    },
    "exception_type": "DatabaseConnectionError",
    "cause": {
      "exception_type": "ConnectionRefusedError",
      "message": "Connection refused"
    },
    "traceback": "..."
  }
}
```

---

## 3. Usage Patterns

### 1. Acquiring a Logger
```python
from packages.logging import get_logger

logger = get_logger(__name__)
logger.info("Application service initialized.")
```

### 2. Emitting Structured Context
```python
logger.info(
    "Processed satellite detection batch",
    extra={"context": {"source": "firms_viirs", "batch_size": 250}},
)
```

### 3. Logging Application Errors (`AppError`)
```python
import logging
from packages.errors import NotFoundError
from packages.logging import log_with_context, get_logger

logger = get_logger(__name__)

try:
    find_source("src-999")
except NotFoundError as err:
    log_with_context(
        logger,
        logging.ERROR,
        "Source lookup failed",
        error=err,
    )
```

### 4. Global Logging Configuration
```python
from packages.logging import configure_logging

# Automatically uses packages.config.get_settings().LOG_LEVEL
configure_logging(json_format=True)
```
