# Operational Configuration (BE-003)

The platform provides a centralized, strongly-typed operational configuration system defined in `packages/config/` using **Pydantic Settings**.

---

## 1. Architectural Scope

- **Operational Configuration**: Manages runtime environment modes, networking hosts/ports, database connection parameters, pool sizes, and security keys.
- **Scientific Configuration Boundary**: Scientific parameters (event cluster radii, temporal windows, persistence thresholds, attribution criteria) are **strictly isolated** from operational settings and managed separately under `BE-004`.

---

## 2. Configuration Parameters

All operational settings are loaded from environment variables (or `.env` locally) with safe development defaults:

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `ENVIRONMENT` | `AppEnvironment` | `development` | Environment mode (`development`, `test`, `staging`, `production`) |
| `DEBUG` | `bool` | `false` | Enable debug mode |
| `API_HOST` | `str` | `0.0.0.0` | HTTP listen address |
| `API_PORT` | `int` | `8000` | HTTP listen port (1–65535) |
| `LOG_LEVEL` | `LogLevel` | `INFO` | Operational logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) |
| `SECRET_KEY` | `SecretStr` | *(dev key)* | Security key for signing operational tokens |
| `POSTGRES_DB` | `str` | `sih26162` | PostgreSQL database name |
| `POSTGRES_USER` | `str` | `sih_user` | PostgreSQL username |
| `POSTGRES_PASSWORD` | `SecretStr` | `sih_dev_password` | PostgreSQL password (protected) |
| `POSTGRES_HOST` | `str` | `localhost` | PostgreSQL host |
| `POSTGRES_PORT` | `int` | `5432` | PostgreSQL port (1–65535) |
| `DATABASE_URL` | `SecretStr \| None` | `None` | Optional full database URL override |
| `DATABASE_POOL_SIZE` | `int` | `5` | SQLAlchemy pool size |
| `DATABASE_MAX_OVERFLOW` | `int` | `10` | SQLAlchemy max pool overflow |

---

## 3. Secret Protection & URL Helpers

Sensitive fields (`POSTGRES_PASSWORD`, `SECRET_KEY`, `DATABASE_URL`) are wrapped in `pydantic.SecretStr`:
- **Redaction**: Printing or logging a `Settings` object automatically masks secrets (e.g. `**********`).
- **Connection URL**: Use `settings.get_database_url()` to obtain the driver connection string.
- **Safe Display URL**: Use `settings.get_safe_database_url()` to obtain a connection string with passwords masked as `***` for logs and diagnostics.

---

## 4. Usage in Code

### Standard Application Usage
```python
from packages.config import get_settings

settings = get_settings()
print(settings.ENVIRONMENT)
db_url = settings.get_database_url()
```

### Unit & Integration Testing
To avoid global cache contamination, tests can instantiate isolated settings:
```python
from packages.config import get_test_settings

test_settings = get_test_settings(
    ENVIRONMENT="test",
    API_PORT=9090,
    POSTGRES_DB="test_db",
)
```
