# Local Database Infrastructure & Migrations (DB-001 / DB-002 / DB-003 / DB-004)

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

### Migration History
1. `0001_baseline`: Enables PostGIS extension at baseline infrastructure level.
2. `0002_scientific_contracts`: Creates the `scientific_contracts` table to persist versioned scientific parameters and calibration contracts without fabricated defaults.
3. `0003_source_registry`: Creates the `source_registry` table establishing persistent identities, semantic roles, access metadata, and lifecycle status for data sources.

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

## 5. Schema Reference: `scientific_contracts` (DB-003)

The `scientific_contracts` table stores versioned scientific algorithm configurations corresponding to the BE-004 `ScientificConfig` model:

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PRIMARY KEY`, `DEFAULT gen_random_uuid()` | Unique contract row identifier |
| `version` | `VARCHAR(64)` | `NOT NULL`, `UNIQUE` | Semantic version of the scientific contract |
| `name` | `VARCHAR(128)` | `NOT NULL`, `DEFAULT 'default'` | Profile name |
| `description` | `TEXT` | `NOT NULL`, `DEFAULT ''` | Calibration notes / basis |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL`, `DEFAULT now()` | UTC creation timestamp |
| `fingerprint` | `VARCHAR(64)` | `NOT NULL`, `INDEX` | Deterministic SHA-256 fingerprint |
| `spatial_cluster_radius_meters` | `DOUBLE PRECISION` | `NULLABLE`, `CHECK (> 0)` | Clustering radius ($m$) |
| `temporal_window_hours` | `DOUBLE PRECISION` | `NULLABLE`, `CHECK (> 0)` | Clustering time window ($h$) |
| `persistence_threshold_days` | `DOUBLE PRECISION` | `NULLABLE`, `CHECK (> 0)` | Persistence duration ($d$) |
| `persistence_min_observations` | `INTEGER` | `NULLABLE`, `CHECK (>= 1)` | Min observation count |
| `attribution_radius_meters` | `DOUBLE PRECISION` | `NULLABLE`, `CHECK (> 0)` | Attribution search radius ($m$) |
| `attribution_confidence_threshold` | `DOUBLE PRECISION` | `NULLABLE`, `CHECK ([0, 1])`| Attribution confidence cutoff |
| `minimum_event_confidence` | `DOUBLE PRECISION` | `NULLABLE`, `CHECK ([0, 1])`| Confirmed event confidence |
| `abstention_confidence_threshold` | `DOUBLE PRECISION` | `NULLABLE`, `CHECK ([0, 1])`| Classification abstention cutoff |
| `raw_config` | `JSONB` | `NULLABLE` | Full canonical JSON payload |
| `is_active` | `BOOLEAN` | `NOT NULL`, `DEFAULT false`, `INDEX` | Active profile indicator |

---

## 6. Schema Reference: `source_registry` (DB-004)

The `source_registry` table stores canonical source definitions and semantic roles, establishing the provenance boundary between source identity and downstream acquisition snapshots / records:

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PRIMARY KEY`, `DEFAULT gen_random_uuid()` | Unique internal surrogate identifier |
| `name` | `VARCHAR(128)` | `NOT NULL`, `UNIQUE`, `CHECK (non-empty)` | Canonical unique source identifier/name |
| `provider` | `VARCHAR(128)` | `NOT NULL`, `CHECK (non-empty)`, `INDEX` | Provider organization/system |
| `source_type` | `VARCHAR(64)` | `NOT NULL`, `CHECK (non-empty)`, `INDEX` | Broad classification (e.g. `satellite`, `vector`, `api`) |
| `role` | `VARCHAR(64)` | `NOT NULL`, `CHECK (role IN (...))`, `INDEX` | Canonical semantic role from `SourceRole` enum |
| `observation_family` | `VARCHAR(64)` | `NULLABLE` | Sensor / observation family (e.g. `thermal`, `optical`) |
| `coverage_notes` | `TEXT` | `NULLABLE` | Textual description of spatial/temporal coverage |
| `access_method` | `VARCHAR(128)` | `NULLABLE` | Access protocol (e.g. `REST API`, `WMS`, `FTP`) |
| `auth_required` | `BOOLEAN` | `NOT NULL`, `DEFAULT false` | Authentication requirement flag (no credentials stored) |
| `license_notes` | `TEXT` | `NULLABLE` | Terms of use / license attribution notes |
| `rate_limit_notes` | `TEXT` | `NULLABLE` | Rate limiting / quota guidance |
| `fallback_source_id`| `UUID` | `NULLABLE`, `FK (id) ON DELETE SET NULL`, `CHECK (!= id)`, `INDEX` | Optional fallback source identity |
| `status` | `VARCHAR(32)` | `NOT NULL`, `DEFAULT 'active'`, `CHECK (non-empty)`, `INDEX` | Lifecycle status (`active`, `deprecated`, etc.) |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL`, `DEFAULT now()` | UTC registration creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL`, `DEFAULT now()`, `CHECK (updated_at >= created_at)` | UTC last update timestamp |

### Provenance Boundaries:
- **`source_registry` (DB-004)**: Answers *"What data source is this?"* (identity and access contract).
- **`source_snapshots` (DB-005)**: Answers *"What exact version/state of that source did we acquire?"* (hashes, retrieval timestamps, HTTP states).
- **`source_records` (DB-006)**: Answers *"What raw observation records came from that acquisition?"* (per-record hashes, raw URIs).

---

## 7. Resetting the Database

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

