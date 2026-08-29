# Application Error Taxonomy & Exceptions (BE-005)

The platform provides a centralized, strongly-typed application error hierarchy defined in `packages/errors/`.

---

## 1. Architectural Principles

- **Transport Independence**: Errors represent application and domain failures and are completely decoupled from HTTP, REST, or FastAPI. Future API layers map `AppError` to HTTP responses.
- **Cause-Preserving Chaining**: When wrapping lower-level exceptions (e.g. database or network errors), the original cause is preserved using Python's standard `raise ... from exc` pattern.
- **Safe by Default**: Error messages and structured context must never contain raw passwords, API keys, or unredacted secrets.
- **Retryability Classification**: Exceptions include a `retryable: bool` metadata flag indicating whether the failure is transient or deterministic (without embedding retry logic into the error package).

---

## 2. Error Code Registry (`ErrorCode`)

| Category | ErrorCode | Description |
| :--- | :--- | :--- |
| **System** | `INTERNAL_ERROR` | Unexpected general application error |
| **Configuration** | `CONFIGURATION_ERROR` | General configuration failure |
| | `MISSING_CONFIGURATION` | Required setting or secret is missing |
| | `INVALID_CONFIGURATION` | Configuration value is malformed or out of range |
| **Validation** | `VALIDATION_ERROR` | Input data validation failure |
| | `INVALID_INPUT` | Parameter or payload constraint violated |
| | `CONTRACT_VIOLATION` | Canonical domain schema contract broken |
| **Database** | `DATABASE_ERROR` | General database operation failure |
| | `DATABASE_CONNECTION_ERROR` | Database connectivity failure *(retryable)* |
| | `RESOURCE_NOT_FOUND` | Query returned no matching record |
| | `RESOURCE_CONFLICT` | Unique constraint or state conflict |
| **External Service**| `EXTERNAL_SERVICE_ERROR` | External data provider/API failure |
| | `SERVICE_UNAVAILABLE` | External service down or returning 5xx *(retryable)* |
| | `SERVICE_TIMEOUT` | External network request timed out *(retryable)* |
| **Domain** | `DOMAIN_ERROR` | Business rule or domain logic failure |
| | `INVARIANT_VIOLATION` | Immutable architectural invariant violated |
| **Pipeline** | `PIPELINE_ERROR` | Batch or pipeline stage failure |
| | `JOB_EXECUTION_ERROR` | Asynchronous background worker failure |

---

## 3. Exception Hierarchy

```
AppError (Exception)
├── ConfigurationError
│   ├── MissingConfigurationError
│   └── InvalidConfigurationError
├── ValidationError
│   └── ContractViolationError
├── DatabaseError
│   ├── DatabaseConnectionError (retryable=True)
│   ├── NotFoundError
│   └── ConflictError
├── ExternalServiceError
│   ├── ServiceUnavailableError (retryable=True)
│   └── ServiceTimeoutError (retryable=True)
├── DomainError
│   └── InvariantViolationError
└── PipelineError
    └── JobExecutionError
```

---

## 4. Usage Patterns

### Raising an Application Error
```python
from packages.errors import NotFoundError


def get_event(event_id: str):
    record = query_db(event_id)
    if not record:
        raise NotFoundError(
            f"Thermal event '{event_id}' not found.",
            details={"event_id": event_id},
        )
    return record
```

### Exception Chaining
```python
from packages.errors import DatabaseConnectionError

try:
    connect_to_postgres()
except ConnectionRefusedError as exc:
    raise DatabaseConnectionError(
        "Could not reach database at localhost:5432.",
        details={"host": "localhost", "port": 5432},
    ) from exc
```

### Safe Serialization (`to_dict()`)
```python
err = NotFoundError("Event not found", details={"event_id": "evt-123"})
payload = err.to_dict()
# Output:
# {
#     "code": "RESOURCE_NOT_FOUND",
#     "message": "Event not found",
#     "category": "database",
#     "retryable": False,
#     "details": {"event_id": "evt-123"}
# }
```
