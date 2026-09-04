# Global Forest Intelligence & Ingestion Layer (Phase 2)

## 1. Overview & Data Provenance

The **Global Forest Intelligence** subsystem provides authoritative geographic boundaries and metadata for forest reserves, national parks, and wooded lands worldwide.

### Conceptual Separation of Concerns
- **OpenStreetMap (OSM) via Overpass API**: Provides geographic forest boundaries (Polygons, MultiPolygons, centroids, areas, protected statuses).
- **NASA FIRMS**: Provides real-time thermal anomaly and fire detections.
- **Phase 3 Integration**: Joins NASA FIRMS fire events with proximate OSM forest boundaries to evaluate forest threat proximity and risk.

```
┌────────────────────────┐              ┌───────────────────────────┐
│   NASA FIRMS Pipeline  │              │ OpenStreetMap Overpass    │
│  (Thermal Detections)  │              │ (Forest Polygons & Zones) │
└───────────┬────────────┘              └─────────────┬─────────────┘
            │                                         │
            │ (lat, lon, FRP)                         │ (Polygon / MultiPolygon)
            ▼                                         ▼
┌───────────────────────────────────────────────────────────────────┐
│         Phase 3: Spatial Proximity & Threat Evaluation            │
└───────────────────────────────────────────────────────────────────┘
```

---

## 2. Supported OSM Tags & Elements

The ingestion pipeline retrieves and processes:
1. `natural=wood` — Natural virgin or secondary woods and forests.
2. `landuse=forest` — Managed forests, timber reserves, and silvicultural lands.
3. `boundary=national_park` / `boundary=protected_area` — Officially demarcated conservation areas.

Supported OSM element types:
- **`way`**: Closed rings converted to GeoJSON `Polygon`.
- **`relation`**: Multi-way relations with `outer` and `inner` roles converted to GeoJSON `MultiPolygon` or `Polygon` with holes.

---

## 3. Geospatial Normalization & Validation

1. **Geometry Integrity**:
   - Polygons are validated using `Shapely 2.x`.
   - Self-intersecting outer rings or knot-ties are safely repaired using `shapely.make_valid()`.
   - Invalid or degenerate elements (< 3 vertices, NaN coordinates) are logged and skipped without halting the batch.
2. **Geodesic Surface Area**:
   - Area is computed via spherical excess integrals on the WGS-84 radius ($R = 6,371,008.8\text{ m}$):
   $$\text{Area} = R^2 \sum \Delta \lambda (2 + \sin \phi_1 + \sin \phi_2) / 2$$
   - Avoids distortion from naive degree-multiplication calculations.
3. **Centroid**:
   - Exact geographic centroid is calculated and indexed as supplementary search metadata.
4. **Idempotency & Deduplication**:
   - Every entity maintains a composite `osm_identity` (`osm_type:osm_id`, e.g. `way:12345`).
   - Re-ingesting existing elements performs an idempotent update of attributes and `updated_at` without duplicating records.

---

## 4. API Endpoints

### Ingest Forests via Bounding Box
- **Method**: `POST /forests/ingest`
- **Description**: Trigger administrative ingestion for a specific bounding box.
- **Request Body**:
```json
{
  "south": 21.0,
  "west": 70.5,
  "north": 21.5,
  "east": 71.0,
  "country_code": "IN",
  "limit": 500,
  "dry_run": false,
  "include_boundary": false
}
```
- **Response**:
```json
{
  "success": true,
  "source": "openstreetmap",
  "bounding_box": {
    "south": 21.0,
    "west": 70.5,
    "north": 21.5,
    "east": 71.0
  },
  "statistics": {
    "scope": "bbox=[21.0,70.5,21.5,71.0]",
    "source": "OPENSTREETMAP",
    "objects_received": 5,
    "polygons_parsed": 5,
    "invalid_geometries": 0,
    "geometry_repairs": 0,
    "inserted": 5,
    "updated": 0,
    "duplicates_skipped": 0,
    "rejected": 0,
    "is_dry_run": false,
    "duration_seconds": 3.26
  },
  "message": "Forest ingestion completed successfully."
}
```

### Query Forests (GeoJSON)
- **Method**: `GET /forests`
- **Parameters**: `country_code`, `bbox`, `min_lat`, `max_lat`, `min_lon`, `max_lon`, `forest_type`, `search`, `limit`, `offset`.
- **Response**: RFC 7946 GeoJSON `FeatureCollection`.

### Proximity Search
- **Method**: `GET /forests/nearby`
- **Parameters**: `latitude`, `longitude`, `radius_km` (default 25.0), `limit` (default 50).
- **Response**: List of proximate forest entities sorted by ascending geodesic distance in km.

---

## 5. Environment Configuration

| Variable | Default | Description |
| :--- | :--- | :--- |
| `OSM_OVERPASS_URL` | `https://overpass-api.de/api/interpreter` | Overpass API endpoint URL. |
| `OSM_USER_AGENT` | `PyroSat-AI/1.0 (Forest Proximity Service)` | User-Agent identifying platform. |
| `OSM_TIMEOUT_SECONDS` | `60.0` | Overpass HTTP request timeout in seconds. |
| `OSM_MAX_RETRIES` | `3` | Maximum retry attempts on transient network errors / HTTP 429. |
| `OSM_RETRY_BACKOFF_FACTOR` | `1.5` | Exponential backoff multiplier between retries. |

---

## 6. How to Run & Verify Ingestion

### Command Line Interface (CLI)
```bash
# Ingest by Country ISO Code
.venv/bin/python scripts/ingest_forests.py --country IN --limit 100

# Ingest by Bounding Box (Gir Forest Reserve)
.venv/bin/python scripts/ingest_forests.py --bbox "21.0,70.5,21.5,71.0" --limit 50

# Dry-run validation with JSON output
.venv/bin/python scripts/ingest_forests.py --bbox "21.0,70.5,21.5,71.0" --limit 10 --dry-run --json
```

### Automated Tests
```bash
# Run dedicated forest intelligence suite
.venv/bin/pytest tests/test_forest_intelligence.py

# Run full project test suite
.venv/bin/pytest
```

---

## 7. Rate Limiting & Safety Controls

1. **Bounding Box Constraints**: Ingestion requests are constrained to a maximum span of $5.0^\circ$ and maximum area of $25.0\text{ deg}^2$ to prevent accidental planetary Overpass overload.
2. **Exponential Backoff**: Automatic retry backoff handles transient 429 (Too Many Requests) or 504 (Gateway Timeout) errors.
3. **No Fake API Keys**: Public Overpass instances require no API keys. Custom self-hosted mirrors can be configured via `OSM_OVERPASS_URL`.
