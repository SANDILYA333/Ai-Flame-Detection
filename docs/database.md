# Local Database Infrastructure & Migrations (DB-001 / DB-002)

This repository uses **PostgreSQL 16 + PostGIS 3.4** as its analytical source-of-record store, managed through **Alembic** schema migrations.

---

## 1. Quickstart

### Start Database Service
To start the database in the background:
```bash
docker compose up -d
```

### Check Status & Health
```bash
# Check container status and healthcheck
docker compose ps

# Detailed health check status
docker inspect --format='{{json .State.Health.Status}}' sih26162-postgres-postgis
```

### Stop Database Service
```bash
docker compose down
```

---

## 2. Configuration & Ports

Environment variables can be configured via `.env` (copy from `.env.example`):

| Variable | Default | Description |
| :--- | :--- | :--- |
| `POSTGRES_DB` | `sih26162` | Database name |
| `POSTGRES_USER` | `sih_user` | Superuser username |
| `POSTGRES_PASSWORD` | `sih_dev_password` | Local development password |
| `POSTGRES_PORT` | `5432` | Host port mapping (`${POSTGRES_PORT:-5432}:5432`) |
| `DATABASE_URL` | *(constructed)* | Optional full SQLAlchemy database URL override |

### Networking Contexts
- **Host machine to container**: `localhost:${POSTGRES_PORT:-5432}` (e.g. `localhost:5433` if host port 5432 is occupied)
- **Container to container (Compose network)**: `postgres-postgis:5432`

---

## 3. PostGIS Verification

Run the automated validation script:
```bash
./scripts/validate_db.sh
```

Or execute integration smoke tests with pytest:
```bash
uv run pytest -m integration
```

Or query PostGIS directly via `psql`:
```bash
docker compose exec postgres-postgis psql -U sih_user -d sih26162 -c "SELECT PostGIS_Full_Version();"
docker compose exec postgres-postgis psql -U sih_user -d sih26162 -c "SELECT ST_AsText(ST_Point(77.2090, 28.6139, 4326));"
```

---

## 4. Database Migrations (Alembic)

All schema changes are version-controlled via Alembic in `alembic/versions/`.

### Canonical Migration Commands

```bash
# Apply all pending migrations to head
uv run alembic upgrade head

# Inspect currently applied revision
uv run alembic current

# Inspect migration history
uv run alembic history --verbose

# Revert the latest migration (or downgrade to base)
uv run alembic downgrade -1
uv run alembic downgrade base

# Create a new migration revision
uv run alembic revision -m "describe_migration"
```

---

## 5. Resetting the Database

> [!WARNING]
> Resetting the database destroys the persistent Docker volume and all local database records.

To perform a complete reset:
```bash
# Stop containers and remove volumes
docker compose down -v

# Start fresh container with clean PostGIS initialization
docker compose up -d

# Apply migrations from scratch
uv run alembic upgrade head
```
