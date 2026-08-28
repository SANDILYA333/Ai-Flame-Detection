# SIH26162 — Architecture & Technical Design

## 0. Architecture Objective

Build the smallest technically sophisticated architecture that can:

1. ingest NASA FIRMS thermal observations;
2. normalize and validate them;
3. group detections into events and persistent sources;
4. enrich events with OSM/industrial and land-cover context;
5. retrieve satellite context;
6. compute interpretable features;
7. classify events;
8. calibrate confidence and support abstention;
9. generate evidence;
10. expose GIS-ready intelligence.

The architecture must optimize for **correctness, reproducibility, latency, explainability and hackathon execution speed** rather than enterprise complexity.

---

# 1. Recommended Stack

| Layer | Technology | Role | Why |
|---|---|---|---|
| Frontend | Next.js + TypeScript | GIS analyst application | Fast development, strong web ecosystem |
| Map | MapLibre GL JS | Interactive map | Open-source, vector-tile friendly |
| Backend API | FastAPI | API + orchestration | Python-native geospatial/ML ecosystem |
| Validation | Pydantic | Request/data validation | Strong typed boundaries |
| Database | PostgreSQL + PostGIS | Events, geometry, infrastructure metadata | Mature spatial queries and relational integrity |
| Cache/queue | Redis | Short-lived cache and job coordination | Lower operational complexity than Kafka for MVP |
| Worker | Python worker process | Ingestion/enrichment/inference | Keeps heavy work outside request handlers |
| ML | scikit-learn + XGBoost initially | Baseline/tabular classification | Strong for heterogeneous engineered features |
| Deep learning | PyTorch, only if justified | Satellite image branch | Use only after baseline proves the need |
| Raster processing | Rasterio + GDAL | Satellite raster operations | Mature geospatial stack |
| Vector processing | GeoPandas + Shapely | ETL/analysis | Fast development |
| Object storage | S3-compatible storage / MinIO | Raster assets, exports, model artifacts | Separates large objects from metadata |
| Experiment tracking | MLflow | Model/evaluation tracking | Reproducibility |
| API schema | OpenAPI | Contract | Native FastAPI support |
| Containerization | Docker | Reproducible services | Easy deployment |
| Reverse proxy | Caddy/Nginx | TLS/routing | Production-like deployment |
| Monitoring | Prometheus + Grafana, optional | Metrics | Add only after core pipeline works |

### Deliberate decision

Do **not** introduce Kafka initially.

The project has a data pipeline, but a distributed event-streaming platform is not automatically required. Redis-backed jobs are sufficient for a hackathon-scale MVP. Kafka can be introduced later if measured throughput requires it.

---

# 2. System Boundary

```text
                  EXTERNAL DATA
                       |
       +---------------+----------------+
       |               |                |
    NASA FIRMS        OSM        Satellite catalogs
       |               |                |
       +---------------+----------------+
                       |
                [Ingestion Layer]
                       |
                [Validation Layer]
                       |
                [Event Store]
                       |
       +---------------+----------------+
       |               |                |
 [Temporal]       [Spatial]       [Context]
 [Persistence]    [Clustering]    [Enrichment]
       |               |                |
       +---------------+----------------+
                       |
                [Feature Builder]
                       |
              +--------+---------+
              |                  |
         [Rules]              [ML]
              |                  |
              +--------+---------+
                       |
              [Calibration/Abstain]
                       |
                [Evidence Engine]
                       |
             [Intelligence Store]
                       |
                 [FastAPI API]
                       |
                 [GIS Frontend]
```

---

# 3. Repository Boundaries

Recommended:

```text
/
├── apps/
│   └── web/                    # Analyst GIS application
│
├── services/
│   ├── api/                    # FastAPI application
│   ├── worker/                 # Background processing
│   └── ml/                     # Model/inference code
│
├── packages/
│   ├── schemas/                # Shared contracts
│   ├── geospatial/             # Spatial utilities
│   └── evidence/               # Evidence generation
│
├── data/
│   ├── raw/                    # Local development inputs
│   ├── interim/                # Processed intermediate artifacts
│   └── samples/                # Small committed demo data only
│
├── models/                     # Versioned model metadata/artifacts
├── scripts/                    # Data/bootstrap/evaluation scripts
├── tests/
├── docs/
└── docker/
```

### Boundary rule

The API must not perform expensive satellite download, large raster processing, clustering over historical data, or model training synchronously.

---

# 4. Storage Model

## PostgreSQL + PostGIS

Store:

- FIRMS detection metadata;
- event clusters;
- persistent sources;
- industrial facilities;
- land-cover summaries;
- feature vectors;
- predictions;
- evidence;
- model version;
- audit metadata.

## Object storage

Store:

- satellite image/raster assets;
- generated map artifacts;
- model binaries;
- evaluation reports;
- large exports.

## Redis

Store:

- job state;
- short-lived API cache;
- deduplication keys;
- rate-limit state;
- transient processing state.

---

# 5. Core Data Model

## `firms_detections`

```text
id
source
satellite
instrument
latitude
longitude
acq_datetime
bright_ti4
bright_ti5
frp
confidence
scan
track
day_night
version
ingested_at
raw_hash
```

## `thermal_events`

```text
id
centroid
start_time
end_time
detection_count
spatial_radius
mean_frp
max_frp
mean_brightness
night_ratio
persistence_score
status
created_at
updated_at
```

## `persistent_sources`

```text
id
geometry
first_seen
last_seen
active_days
detection_count
mean_frp
frp_variance
spatial_stability
source_type
confidence
```

## `industrial_assets`

```text
id
osm_id
geometry
name
industrial_type
tags
source
retrieved_at
```

## `context_features`

```text
event_id
industrial_distance_m
industrial_asset_count
landcover_class
vegetation_fraction
water_fraction
built_fraction
road_distance_m
facility_density
satellite_available
cloud_fraction
feature_version
```

## `predictions`

```text
id
event_id
model_version
predicted_class
probability_vector
confidence
abstained
created_at
```

## `evidence_items`

```text
id
event_id
type
value
strength
source
timestamp
```

---

# 6. Event Identity

Never use only latitude/longitude as event identity.

A detection belongs to an event if:

- temporal proximity is within a configurable window;
- spatial distance is within a configurable radius;
- optionally, contextual consistency supports the grouping.

Use clustering such as:

- DBSCAN/HDBSCAN for exploratory event grouping;
- geodesic distance;
- time-window constraints.

### Important

A persistent flare should become one **persistent source** with many events/detections, not thousands of separate alerts.

---

# 7. Persistence Engine

Compute:

```text
persistence_score =
    f(
      active_days,
      detection_count,
      temporal_span,
      spatial_stability,
      observation_frequency
    )
```

Do not hard-code the final formula before evaluation.

### Candidate features

- active days / observed days;
- longest continuous run;
- mean inter-detection interval;
- centroid standard deviation;
- radius of gyration;
- FRP stability;
- day/night ratio;
- seasonal consistency.

---

# 8. Context Enrichment

## OSM

Query nearby:

- industrial land-use polygons;
- factories/works;
- power plants;
- oil/gas infrastructure where mapped;
- mining features;
- pipelines;
- storage/industrial facilities;
- roads and settlements when relevant.

OSM is **context**, not ground truth.

### Proximity features

Examples:

```text
distance_to_nearest_industrial_area
distance_to_power_plant
distance_to_mine
distance_to_oil_gas_asset
industrial_asset_count_500m
industrial_asset_count_1km
```

Use multiple radii because a 375 m observation pixel and a facility polygon do not have identical footprints.

---

# 9. Satellite Context

## Primary candidates

### Sentinel-2

Use for:

- land/vegetation context;
- visible/SWIR evidence;
- burn-scar/contextual change;
- industrial site characterization.

It has 10 m bands and a nominal 5-day revisit for the constellation.

### Landsat Collection 2

Use for:

- historical context;
- surface reflectance;
- surface temperature where available;
- longer time series.

### NASA HLS

Use when higher observation frequency from harmonized Landsat/Sentinel data is useful.

### Important constraint

Optical imagery is not guaranteed at event time.

Clouds and revisit gaps mean:

```text
satellite evidence unavailable
```

must be a valid state.

Do not invent evidence.

---

# 10. Data Pipeline

```text
FIRMS API
  ↓
Raw response
  ↓
Schema validation
  ↓
Deduplication
  ↓
Canonical detection record
  ↓
Event clustering
  ↓
OSM enrichment
  ↓
Land-cover enrichment
  ↓
Satellite search
  ↓
Feature extraction
  ↓
Classification
  ↓
Calibration
  ↓
Persistence update
  ↓
Evidence generation
  ↓
PostGIS
  ↓
API
```

---

# 11. FIRMS Ingestion Design

NASA FIRMS provides area APIs and multiple sources including VIIRS NOAA-20, NOAA-21, Suomi-NPP and MODIS variants.

The API requires a MAP_KEY.

The documented area API supports:

```text
/api/area/csv/[MAP_KEY]/[SOURCE]/[AREA_COORDINATES]/[DAY_RANGE]
```

and historical queries can include a date.

### Ingestion safeguards

- retry with exponential backoff;
- validate source/version;
- record ingestion timestamp;
- preserve source record;
- hash raw record for deduplication;
- never silently overwrite observations;
- track API failures;
- respect NASA service limits.

---

# 12. Geospatial Precision Policy

This is critical.

A FIRMS point represents the center of a nominal sensor pixel/detection, not an exact facility location.

Therefore the UI/API should distinguish:

- **detection coordinate**
- **event centroid**
- **probable source area**
- **nearby facility**
- **confidence**

Do not state:

> “The fire is exactly at Factory X.”

Prefer:

> “The thermal event overlaps/occurs within the vicinity of mapped industrial facility X; attribution confidence is Y.”

---

# 13. ML Architecture

## Stage 1 — Baseline

Use a transparent tabular classifier.

Candidates:

- Logistic Regression
- Random Forest
- XGBoost / LightGBM

Recommended starting point:

**XGBoost or LightGBM-style gradient boosting on engineered event features.**

Why:

- heterogeneous numerical/categorical features;
- small-to-medium labelled dataset;
- fast training;
- strong baseline;
- feature importance;
- easier debugging than deep vision models.

## Stage 2 — Satellite image branch

Only if baseline is insufficient.

Candidate architecture:

```text
Satellite patch
    ↓
CNN / pretrained vision encoder
    ↓
embedding
    +
tabular event features
    ↓
fusion model
    ↓
classification
```

Do not start here.

---

# 14. Feature Groups

## FIRMS

- FRP
- brightness temperature
- brightness difference
- confidence
- day/night
- scan
- track
- sensor
- satellite

## Temporal

- active days
- detection count
- temporal span
- inter-arrival time
- recurrence
- weekday/month/season
- night ratio

## Spatial

- cluster radius
- centroid drift
- detection density
- neighboring hotspot density
- spatial stability

## Infrastructure

- nearest industrial asset distance
- asset type
- industrial density
- power-plant proximity
- mining proximity
- oil/gas proximity

## Land cover

- vegetation fraction
- built-up fraction
- cropland fraction
- forest fraction
- water proximity

## Satellite

- cloud fraction
- spectral indices
- texture
- recent change
- thermal/spectral indicators where available

---

# 15. Training/Validation Protocol

## The biggest mistake to avoid

Do not randomly split individual detections if detections from the same persistent source appear in both train and test.

That causes leakage.

## Better split

Group by:

- source;
- facility;
- geographic region;
- event cluster.

Preferred:

```text
Train: regions/sources A,B,C
Validation: sources D
Test: unseen sources/regions E
```

Use spatial and temporal holdouts.

---

# 16. Evaluation

## Primary

- Precision
- Recall
- F1
- Macro F1
- PR-AUC
- confusion matrix

## Industrial class

Because industrial attribution is the central requirement:

- industrial precision;
- industrial recall;
- industrial F1;
- false-positive rate.

## Persistence

- source-level precision;
- source-level recall;
- persistence F1;
- track continuity.

## Calibration

- reliability diagram;
- Expected Calibration Error;
- Brier score.

## Coverage

Measure:

```text
accuracy vs coverage
```

as the confidence threshold changes.

A system that abstains on ambiguous events can be stronger than one that classifies everything incorrectly.

---

# 17. Evidence Engine

Evidence must be deterministic where possible.

### Evidence categories

1. FIRMS observation evidence
2. Temporal evidence
3. Spatial evidence
4. Infrastructure evidence
5. Land-cover evidence
6. Satellite evidence
7. Model evidence
8. Uncertainty

### Example

```text
Classification:
Persistent industrial source

Supporting evidence:
+ 27 detections across 19 active days
+ 210 m from mapped industrial facility
+ spatial radius 160 m
+ repeated nighttime observations
+ high persistence score

Limiting evidence:
- optical image unavailable for 3 observations due to cloud
```

This is much more defensible than:

> “AI says gas flare.”

---

# 18. Explainability

Use:

- feature importance;
- SHAP for tabular model;
- nearest/reference event comparisons;
- explicit rule evidence;
- confidence calibration.

Do not use an LLM to invent explanations.

An LLM may later convert structured evidence into natural language, but the underlying evidence must originate from the pipeline.

---

# 19. API Contract

Recommended endpoints:

```text
GET  /health

GET  /events
GET  /events/{event_id}

GET  /sources
GET  /sources/{source_id}

GET  /events/{event_id}/evidence

GET  /events/{event_id}/timeline

GET  /map/events

GET  /map/sources

POST /ingestion/run

GET  /models/current

GET  /metrics
```

### API rule

Every endpoint must:

1. validate input;
2. enforce access policy;
3. perform bounded work;
4. return predictable schemas;
5. avoid long-running computation.

---

# 20. Security

Minimum:

- environment variables for secrets;
- no API keys in frontend;
- authentication for non-public analyst functions;
- input validation;
- rate limiting;
- audit logs;
- signed/controlled exports;
- least-privilege service accounts;
- dependency scanning;
- no sensitive operational credentials in Git.

---

# 21. Reliability

The pipeline should tolerate:

- FIRMS API failure;
- OSM timeout;
- satellite catalog unavailable;
- malformed records;
- duplicate records;
- partial enrichment;
- model failure.

A single missing enrichment should not destroy the event.

Use:

```text
event_status:
  detected
  enriching
  enriched
  classified
  partial
  failed
```

---

# 22. Observability

Track:

- ingestion success rate;
- records ingested;
- duplicates;
- enrichment latency;
- satellite lookup failures;
- model latency;
- queue depth;
- classification coverage;
- abstention rate;
- API latency.

---

# 23. Performance Targets

Initial internal targets:

- FIRMS ingestion: <30 s for a bounded demo area
- event enrichment: <30 s/event in batch mode
- classification: <1 s/event excluding external downloads
- end-to-end demo event: target <2 min where external data is available
- 10,000-event offline batch: target <5 min

These are engineering targets, not SIH requirements.

External API latency should be reported separately from internal processing latency.

---

# 24. Deployment

## Hackathon

Use Docker Compose:

```text
web
api
worker
postgres-postgis
redis
object-storage
```

Optional:

```text
mlflow
prometheus
grafana
```

Do not deploy optional infrastructure until required.

---

# 25. Architecture Invariants

1. Heavy processing never happens inside an HTTP request.
2. Raw source observations are never silently mutated.
3. Every prediction has a model version.
4. Every prediction has evidence and uncertainty metadata.
5. OSM is contextual evidence, not ground truth.
6. FIRMS coordinates are not treated as exact facility coordinates.
7. Satellite absence is represented explicitly.
8. Model evaluation uses source/spatially separated test data.
9. No classifier is allowed to force a low-confidence prediction.
10. Large raster artifacts do not live directly in PostgreSQL.
11. API boundaries validate external input.
12. Data provenance is preserved.

---

# 26. Implementation Order

## Phase 1 — Data spine

- FIRMS downloader
- schema
- PostGIS
- raw storage
- deduplication

## Phase 2 — Event intelligence

- spatial clustering
- temporal grouping
- persistent source tracker

## Phase 3 — Context

- OSM
- land cover
- satellite catalog
- feature builder

## Phase 4 — Baseline intelligence

- heuristic baseline
- XGBoost/LightGBM model
- evaluation
- calibration

## Phase 5 — Evidence

- evidence schema
- evidence generation
- uncertainty

## Phase 6 — GIS integration

- map endpoints
- event details
- timeline
- source watchlist

## Phase 7 — Advanced model

Only if metrics show the baseline is inadequate.

---

# 27. ADRs

## ADR-001 — PostGIS as primary geospatial store

**Decision:** PostgreSQL + PostGIS.

**Reason:** spatial indexing, joins, relational integrity and mature production ecosystem.

## ADR-002 — Redis instead of Kafka for MVP

**Decision:** Redis-backed jobs.

**Reason:** lower operational burden and sufficient scale for a bounded hackathon pipeline.

## ADR-003 — Tabular ML before deep vision

**Decision:** engineered-feature model first.

**Reason:** ground truth is the bottleneck; a sophisticated vision model cannot rescue weak labels.

## ADR-004 — Evidence-first predictions

**Decision:** every prediction must expose evidence and uncertainty.

**Reason:** analyst trust and judge differentiation.

## ADR-005 — Abstention is a first-class outcome

**Decision:** model may return `uncertain`.

**Reason:** open-world thermal anomalies cannot be completely classified from available data.

---

# 28. External Standards/Resources

- NASA FIRMS active fire documentation
- NASA Earthdata VIIRS 375 m documentation
- NASA FIRMS API
- ESA Sentinel-2 mission
- USGS Landsat Collection 2
- NASA Harmonized Landsat Sentinel-2
- ESA WorldCover
- OpenStreetMap
- Overpass API
- OGC STAC
- OGC API Features
- PostGIS
- GDAL/Rasterio

See `ai-workflow-rules.md` for research and implementation discipline.
