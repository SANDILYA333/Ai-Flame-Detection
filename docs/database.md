# Local Database Infrastructure & Migrations (DB-001 / DB-002 / DB-003 / DB-004 / DB-005 / DB-006 / DB-007 / DB-008)

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
4. `0004_source_snapshots`: Creates the `source_snapshots` table establishing exact acquired versions, retrieval timestamps, request fingerprints, integrity hashes, and availability states for registered data sources.
5. `0005_source_records`: Creates the `source_records` table establishing raw observation records, record hashes, PostGIS geometry (`EPSG:4326`), provider metadata JSONB, and composite uniqueness invariants (`source_snapshot_id`, `record_hash`).

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

---

## 7. Schema Reference: `source_snapshots` (DB-005)

The `source_snapshots` table records exact acquired source states, versions, retrieval timestamps, request fingerprints, integrity hashes, and availability states:

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PRIMARY KEY`, `DEFAULT gen_random_uuid()` | Immutable surrogate snapshot primary key |
| `source_id` | `UUID` | `NOT NULL`, `FK (source_registry.id) ON DELETE RESTRICT`, `INDEX` | Foreign key referencing registered data source |
| `external_version` | `VARCHAR(128)` | `NULLABLE` | Source-provided version/edition/date string |
| `retrieved_at` | `TIMESTAMPTZ` | `NOT NULL`, `DEFAULT now()`, `INDEX` | UTC timestamp when snapshot was acquired |
| `acquired_from` | `TEXT` | `NULLABLE` | Retrieval URI / endpoint / bucket reference (no credentials) |
| `request_fingerprint` | `VARCHAR(64)` | `NULLABLE`, `CHECK (length = 64)`, `INDEX` | SHA-256 digest of request parameters/query |
| `content_hash` | `VARCHAR(64)` | `NULLABLE`, `CHECK (length = 64)`, `INDEX` | Cryptographic SHA-256 digest of raw acquired artifact |
| `availability_status` | `VARCHAR(32)` | `NOT NULL`, `CHECK (IN (...))`, `INDEX` | State (`AVAILABLE`, `EMPTY_RESULT`, `FAILED`, etc.) |
| `error_code` | `VARCHAR(64)` | `NULLABLE` | Machine-readable error code if acquisition failed |
| `metadata_json` | `JSONB` | `NULLABLE` | Acquisition headers/metadata (ETag, size, content-type) |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL`, `DEFAULT now()` | UTC database insertion timestamp |

---

## 8. Schema Reference: `source_records` (DB-006)

The `source_records` table records individual raw observations/records belonging to a specific source snapshot:

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PRIMARY KEY`, `DEFAULT gen_random_uuid()` | Immutable surrogate record primary key |
| `source_snapshot_id`| `UUID` | `NOT NULL`, `FK (source_snapshots.id) ON DELETE RESTRICT`, `INDEX` | Parent snapshot foreign key |
| `external_record_id`| `VARCHAR(128)` | `NULLABLE`, `INDEX` | External provider record identifier (e.g. FIRMS row index) |
| `raw_artifact_uri` | `TEXT` | `NULLABLE` | Storage URI/path to raw external blob/file if applicable |
| `record_hash` | `VARCHAR(64)` | `NOT NULL`, `CHECK (length = 64)`, `INDEX` | Cryptographic SHA-256 digest of this raw record |
| `record_time` | `TIMESTAMPTZ` | `NULLABLE`, `INDEX` | Source-reported observation timestamp in UTC |
| `geometry` | `GEOMETRY(Geometry, 4326)` | `NULLABLE`, `GIST INDEX` | PostGIS spatial geometry in EPSG:4326 |
| `raw_metadata_json` | `JSONB` | `NULLABLE` | Structured provider-specific raw fields (no credentials) |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL`, `DEFAULT now()` | UTC database persistence timestamp |

### Key Invariants:
- `UNIQUE (source_snapshot_id, record_hash)`: Enforces uniqueness within a single snapshot while allowing identical records across multiple polling snapshots.
- Spatial Index: GiST index on `geometry` for efficient bounding box and radius queries.

---

## 9. Schema Reference: `detections` (DB-007)

The `detections` table records normalized canonical remote-sensing thermal observations derived from raw source records:

| Column | Type | Unit | Constraints | Description |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `UUID` | — | `PRIMARY KEY`, `DEFAULT gen_random_uuid()` | Immutable surrogate detection primary key |
| `source_record_id` | `UUID` | — | `NOT NULL`, `FK (source_records.id) ON DELETE RESTRICT`, `INDEX` | Source record provenance foreign key |
| `source_snapshot_id`| `UUID` | — | `NOT NULL`, `FK (source_snapshots.id) ON DELETE RESTRICT`, `INDEX` | Snapshot provenance foreign key |
| `source` | `VARCHAR(128)` | — | `NOT NULL`, `INDEX` | Observation source adapter identifier (e.g. `'firms'`) |
| `satellite` | `VARCHAR(64)` | — | `NOT NULL`, `INDEX` (composite) | Observing satellite platform (e.g. `'NOAA-20'`, `'Terra'`) |
| `instrument` | `VARCHAR(64)` | — | `NOT NULL`, `INDEX` (composite) | Observing sensor instrument (e.g. `'VIIRS'`, `'MODIS'`) |
| `product_type` | `VARCHAR(64)` | — | `NOT NULL` | Processing tier (e.g. `'nrt'`, `'standard'`, `'urt'`) |
| `product_version` | `VARCHAR(64)` | — | `NOT NULL` | Source data product version string |
| `acquired_at` | `TIMESTAMPTZ` | UTC | `NOT NULL`, `INDEX` | Satellite observation/acquisition timestamp |
| `ingested_at` | `TIMESTAMPTZ` | UTC | `NOT NULL`, `DEFAULT now()` | Ingestion timestamp into canonical pipeline |
| `latitude` | `DOUBLE PRECISION` | ° | `NOT NULL`, `CHECK (latitude BETWEEN -90 AND 90)` | Pixel centroid latitude |
| `longitude` | `DOUBLE PRECISION` | ° | `NOT NULL`, `CHECK (longitude BETWEEN -180 AND 180)` | Pixel centroid longitude |
| `geometry` | `GEOMETRY(Point, 4326)`| EPSG:4326 | `NOT NULL`, `GIST INDEX` | PostGIS 2D Point centroid (`POINT(lon lat)`) |
| `frp_mw` | `DOUBLE PRECISION` | MW | `NULLABLE`, `CHECK (frp_mw >= 0)` | Fire Radiative Power in Megawatts |
| `brightness_ti4_k` | `DOUBLE PRECISION` | K | `NULLABLE`, `CHECK (brightness_ti4_k >= 0)` | TI4 / 4µm band brightness temperature in Kelvin |
| `brightness_ti5_k` | `DOUBLE PRECISION` | K | `NULLABLE`, `CHECK (brightness_ti5_k >= 0)` | TI5 / 11µm band brightness temperature in Kelvin |
| `confidence_raw` | `VARCHAR(64)` | — | `NULLABLE` | Source-provided raw confidence string/score |
| `day_night` | `VARCHAR(8)` | — | `NULLABLE`, `CHECK (day_night IN ('D', 'N', 'unknown'))`| Daytime/nighttime observation indicator |
| `scan` | `DOUBLE PRECISION` | km | `NULLABLE`, `CHECK (scan > 0)` | Along-scan pixel dimension in kilometers |
| `track` | `DOUBLE PRECISION` | km | `NULLABLE`, `CHECK (track > 0)` | Along-track pixel dimension in kilometers |
| `raw_identifier` | `VARCHAR(128)` | — | `NULLABLE` | External provider observation identifier |
| `raw_hash` | `VARCHAR(64)` | SHA-256 | `NOT NULL`, `CHECK (length = 64)`, `INDEX` | Cryptographic SHA-256 digest of raw record |
| `quality_status` | `VARCHAR(32)` | — | `NULLABLE` | Canonical quality classification |
| `created_at` | `TIMESTAMPTZ` | UTC | `NOT NULL`, `DEFAULT now()` | UTC database insertion timestamp |

### Provenance Hierarchy:
```text
source_registry (DB-004) -> source_snapshots (DB-005) -> source_records (DB-006) -> detections (DB-007)
```

---

## 10. Schema Reference: `thermal_events` & `event_detections` (DB-008)

The `thermal_events` table persists derived spatiotemporal event clusters formed from member canonical detections:

| Column | Type | Unit | Constraints | Description |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `UUID` | — | `PRIMARY KEY`, `DEFAULT gen_random_uuid()` | Immutable surrogate event primary key |
| `scientific_contract_id` | `UUID` | — | `NULLABLE`, `FK (scientific_contracts.id) ON DELETE RESTRICT`, `INDEX` | Algorithmic configuration contract FK |
| `formation_run_id` | `VARCHAR(128)` | — | `NULLABLE`, `INDEX` | Pipeline execution run identifier |
| `formation_status` | `VARCHAR(32)` | — | `NOT NULL`, `DEFAULT 'FORMED'`, `INDEX` | Event formation status (`FORMED`, `CANDIDATE`, `REFINED`) |
| `started_at` | `TIMESTAMPTZ` | UTC | `NOT NULL`, `INDEX` (composite) | Earliest observation timestamp in cluster |
| `ended_at` | `TIMESTAMPTZ` | UTC | `NOT NULL`, `INDEX` (composite), `CHECK (ended_at >= started_at)` | Latest observation timestamp in cluster |
| `duration_seconds` | `DOUBLE PRECISION` | s | `NULLABLE`, `CHECK (duration_seconds >= 0)` | Event temporal duration in seconds |
| `detection_count` | `INTEGER` | Count | `NOT NULL`, `CHECK (detection_count >= 1)` | Number of constituent detections |
| `centroid_geometry` | `GEOMETRY(Point, 4326)` | EPSG:4326 | `NOT NULL`, `GIST INDEX` | Representative spatial centroid (`POINT(lon lat)`) |
| `observation_geometry`| `GEOMETRY(Geometry, 4326)`| EPSG:4326 | `NULLABLE`, `GIST INDEX` | Bounding footprint / convex hull geometry |
| `mean_frp_mw` | `DOUBLE PRECISION` | MW | `NULLABLE`, `CHECK (mean_frp_mw >= 0)` | Mean Fire Radiative Power across detections |
| `max_frp_mw` | `DOUBLE PRECISION` | MW | `NULLABLE`, `CHECK (max_frp_mw >= 0)` | Peak Fire Radiative Power across detections |
| `total_frp_mw` | `DOUBLE PRECISION` | MW | `NULLABLE`, `CHECK (total_frp_mw >= 0)` | Summed instantaneous FRP across detections |
| `metadata_json` | `JSONB` | — | `NULLABLE` | Extended clustering parameters / dispersion metrics |
| `created_at` | `TIMESTAMPTZ` | UTC | `NOT NULL`, `DEFAULT now()` | UTC database persistence timestamp |

### Association Table: `event_detections`

The `event_detections` table maintains deterministic membership between thermal events and member detections:

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | `PRIMARY KEY`, `DEFAULT gen_random_uuid()` | Immutable surrogate membership PK |
| `event_id` | `UUID` | `NOT NULL`, `FK (thermal_events.id) ON DELETE RESTRICT`, `INDEX` | Parent event foreign key |
| `detection_id` | `UUID` | `NOT NULL`, `FK (detections.id) ON DELETE RESTRICT`, `INDEX` | Member detection foreign key |
| `membership_confidence`| `DOUBLE PRECISION`| `NULLABLE`, `CHECK (confidence BETWEEN 0 AND 1)` | Membership weight / confidence score |
| `metadata_json` | `JSONB` | `NULLABLE` | Association metadata |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL`, `DEFAULT now()` | Persistence timestamp |

**Invariants**: `UNIQUE (event_id, detection_id)` guarantees idempotent event composition.

### 5-Tier Provenance Hierarchy:
```text
source_registry (DB-004)
    ↓
source_snapshots (DB-005)
    ↓
source_records (DB-006)
    ↓
detections (DB-007)
    ↓
event_detections (DB-008) ──→ thermal_events (DB-008)
```

---

## 11. Resetting the Database

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


