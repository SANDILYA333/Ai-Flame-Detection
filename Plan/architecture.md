# SIH26162 --- Architecture & Technical Design

## 0. Architecture Objective

Build the smallest technically sophisticated architecture that can:

1.  ingest NASA FIRMS observations;
2.  preserve raw provenance;
3.  normalize and validate observations;
4.  form thermal events;
5.  track recurring/persistent sources;
6.  enrich events with industrial/context and land-cover data;
7.  retrieve satellite context when available;
8.  compute interpretable features;
9.  establish deterministic baselines;
10. classify events/sources where ML is justified;
11. calibrate confidence and support abstention;
12. generate evidence and uncertainty;
13. expose GIS-ready intelligence.

The architecture optimizes for **correctness, reproducibility,
explainability, measured performance and hackathon execution speed**
rather than enterprise complexity.

------------------------------------------------------------------------

# 1. Recommended Stack

  ------------------------------------------------------------------------------------------
  Layer             Technology            Role                             Why
  ----------------- --------------------- -------------------------------- -----------------
  Frontend          Next.js + TypeScript  Analyst GIS application          Fast development
                                                                           and strong web
                                                                           ecosystem

  Map               MapLibre GL JS        GIS visualization                Open-source and
                                                                           flexible

  API               FastAPI               Typed API boundary               Python-native
                                                                           geospatial/ML
                                                                           ecosystem

  Validation        Pydantic              Runtime validation               Explicit data
                                                                           contracts

  Database          PostgreSQL + PostGIS  Events, sources, geometry,       Spatial
                                          metadata                         indexing +
                                                                           relational
                                                                           integrity

  Cache/job         Redis                 Short-lived cache and jobs       Lower MVP
  coordination                                                             complexity than
                                                                           Kafka

  Worker            Python worker         Ingestion/enrichment/inference   Keeps heavy work
                                                                           out of HTTP

  ML                scikit-learn +        Engineered-feature models        Strong baseline
                    XGBoost/LightGBM                                       for heterogeneous
                                                                           tabular features

  Deep learning     PyTorch, conditional  Satellite-image branch           Only if benchmark
                                                                           evidence
                                                                           justifies it

  Raster            Rasterio + GDAL       Raster operations                Mature geospatial
                                                                           tooling

  Vector            GeoPandas + Shapely   ETL/analysis                     Fast geospatial
                                                                           development

  Object storage    S3-compatible / MinIO Large artifacts                  Keeps large files
                                                                           outside DB

  Experiment        MLflow                Model/evaluation tracking        Reproducibility
  tracking                                                                 

  Contracts         OpenAPI               API contract                     Native FastAPI
                                                                           support

  Containers        Docker                Reproducible deployment          Simple deployment

  Proxy             Caddy/Nginx           TLS/routing                      Deployment
                                                                           boundary

  Monitoring        Prometheus/Grafana,   Operational metrics              Add after core
                    optional                                               pipeline
  ------------------------------------------------------------------------------------------

### Deliberate decision

Do **not** introduce Kafka initially.

Use Redis-backed jobs. Reconsider only if measured throughput,
durability or multi-worker coordination requirements exceed the MVP
design.

------------------------------------------------------------------------

# 2. System Architecture

``` text
                         EXTERNAL SOURCES
       ┌────────────────────┼──────────────────────┐
       │                    │                      │
   NASA FIRMS              OSM              Satellite catalogs/
 thermal observations   infrastructure       imagery assets
       │                    │                      │
       └────────────────────┼──────────────────────┘
                            ↓
                    INGESTION BOUNDARY
                            ↓
                RAW + PROVENANCE STORAGE
                            ↓
                 VALIDATION / NORMALIZATION
                            ↓
                    DETECTION STORE
                            ↓
                 EVENT FORMATION ENGINE
                            ↓
             ┌──────────────┼──────────────┐
             ↓              ↓              ↓
        Temporal        Spatial         Context
        persistence     clustering       enrichment
             └──────────────┼──────────────┘
                            ↓
                    FEATURE BUILDER
                            ↓
              ┌─────────────┴─────────────┐
              ↓                           ↓
        Deterministic                  ML model
          baselines                  (if justified)
              └─────────────┬─────────────┘
                            ↓
                    CALIBRATION
                            ↓
                    ABSTENTION
                            ↓
                  EVIDENCE ENGINE
                            ↓
              INTELLIGENCE / SOURCE STORE
                            ↓
                       FASTAPI
                            ↓
                     GIS FRONTEND
```

------------------------------------------------------------------------

# 3. Canonical Domain Model

## 3.1 Detection

One source observation from FIRMS.

Fields include:

-   source
-   satellite
-   instrument
-   acquisition timestamp
-   latitude/longitude
-   brightness temperatures where available
-   FRP where available
-   confidence
-   scan/track where available
-   day/night
-   product/version
-   ingestion timestamp
-   source identifier/hash

## 3.2 Thermal Event

A spatio-temporal grouping of detections believed to represent one
episode.

Fields:

-   event_id
-   detection_ids
-   geometry
-   start_time
-   end_time
-   duration
-   detection_count
-   spatial footprint
-   centroid
-   FRP statistics
-   source provenance
-   event formation algorithm/version

## 3.3 Persistent Source

A longer-lived spatial entity associated with repeated events.

Fields:

-   source_id
-   linked_event_ids
-   geometry
-   first_seen
-   last_seen
-   active_days
-   recurrence statistics
-   spatial stability
-   temporal signature
-   context
-   attribution state

## 3.4 Context

Context is stored independently:

-   industrial facility geometry/type
-   land-cover class
-   nearby infrastructure
-   satellite observation metadata
-   distance/proximity measures
-   source freshness
-   provenance

## 3.5 Intelligence Result

Never collapse the ontology into one flat class.

Store separate dimensions:

``` text
phenomenon
context
persistence_state
attribution_strength
confidence
uncertainty
evidence
model_version
```

------------------------------------------------------------------------

# 4. Classification Ontology

## Phenomenon

``` text
fire
flare
industrial_thermal_source
agricultural_burn
vegetation_wildfire
other_thermal_anomaly
unknown
```

## Context

``` text
industrial
oil_gas
power
mining
agricultural
forest_vegetation
urban
other
unknown
```

## Persistence

``` text
transient
recurring
persistent
insufficient_history
```

## Attribution

``` text
strong
moderate
weak
unknown
```

This prevents context or persistence from becoming accidental class
labels.

------------------------------------------------------------------------

# 5. Data Storage

## PostgreSQL + PostGIS

Store:

-   detections
-   events
-   persistent sources
-   facility metadata
-   geometries
-   land-cover summaries
-   model predictions
-   evidence metadata
-   provenance
-   evaluation records
-   configuration/version metadata

## Object storage

Store:

-   downloaded raster assets
-   generated map artifacts
-   model files
-   experiment artifacts
-   exports
-   large raw files when appropriate

## Raw data rule

Raw source observations must remain immutable.

Derived data may be versioned/recomputed.

------------------------------------------------------------------------

# 6. Data Contracts

Every external source gets a canonical internal schema.

Example:

``` python
class FirmsDetection(BaseModel):
    latitude: float
    longitude: float
    acquisition_time: datetime
    frp_mw: float | None
    brightness_ti4_k: float | None
    brightness_ti5_k: float | None
    confidence: str | None
    satellite: str
    instrument: str
    source_version: str
```

Do not allow vendor-specific field names to leak through the
application.

------------------------------------------------------------------------

# 7. Geospatial Rules

## CRS

-   `EPSG:4326` for API interchange where appropriate.
-   Geography/projected CRS for distance/area calculations.

Never use naïve Euclidean distance directly on latitude/longitude.

## Spatial precision

Maintain:

``` text
detection_geometry
event_geometry
source_geometry
facility_geometry
distance_to_facility
attribution_confidence
```

Never replace one geometry with another merely because they are nearby.

------------------------------------------------------------------------

# 8. FIRMS Data Handling

NASA FIRMS provides active-fire/thermal-anomaly products including VIIRS
375 m products. NASA notes that detections are satellite observations
and may represent fire, hot smoke, agriculture or other sources; pixel
size does not imply that the entire pixel is burning.

Engineering implications:

1.  FIRMS is an observation source, not ground truth.
2.  Preserve satellite/product/version metadata.
3.  Preserve acquisition time separately from ingestion time.
4.  Preserve NRT/RT/URT/standard product identity.
5.  Cache immutable historical results.
6.  Respect NASA access limits.
7.  Keep credentials server-side.
8.  Distinguish external-data latency from internal processing latency.

------------------------------------------------------------------------

# 9. Context Enrichment

## Industrial/OSM

Use OSM as contextual evidence.

Store:

-   feature type
-   geometry
-   tags
-   source timestamp if available
-   query/version metadata
-   distance to event/source

Never convert:

``` text
OSM industrial polygon nearby
```

into:

``` text
confirmed industrial fire
```

## Land cover

Use a documented land-cover product such as ESA WorldCover when
suitable.

Store:

-   product/version
-   class
-   sampling geometry
-   retrieval date
-   confidence/quality metadata if available

## Satellite context

Satellite imagery is a required **capability/integration path**, but
imagery availability is not a prerequisite for every inference.

Use a tiered strategy:

``` text
Tier 1: FIRMS + temporal + spatial features
Tier 2: land cover + industrial context
Tier 3: satellite imagery when available
Tier 4: advanced vision model only if justified
```

------------------------------------------------------------------------

# 10. Event Formation

Do not train directly on raw points if the product task is event/source
intelligence.

Pipeline:

``` text
detections
→ spatial-temporal clustering
→ thermal events
→ source tracking
```

Clustering parameters must be configurable and versioned.

Every event must retain its source detections.

------------------------------------------------------------------------

# 11. Persistence Engine

Compute:

-   detection count
-   active days
-   observation span
-   recurrence
-   temporal gaps
-   mean/median/max FRP
-   FRP variability
-   spatial stability
-   centroid drift
-   day/night distribution
-   seasonal behavior where enough history exists

Persistence is an independent feature/state.

Example:

``` text
repeated detections
+ stable footprint
+ industrial context
→ stronger persistent-source attribution
```

This remains probabilistic evidence, not proof.

------------------------------------------------------------------------

# 12. Feature Groups

## FIRMS features

-   confidence
-   FRP
-   brightness temperatures
-   scan/track
-   day/night
-   satellite
-   acquisition timing

## Temporal features

-   active days
-   recurrence
-   duration
-   gaps
-   periodicity
-   day/night pattern

## Spatial features

-   cluster size
-   spatial density
-   centroid drift
-   footprint stability

## Context features

-   distance to industrial facilities
-   facility type
-   land-cover class
-   nearby road/rail/infrastructure context

## Satellite features

Only where imagery is available and quality is sufficient.

------------------------------------------------------------------------

# 13. Model Strategy

Use the following sequence:

``` text
Rule baseline
      ↓
Feature baseline
      ↓
XGBoost/LightGBM
      ↓
Calibration
      ↓
Abstention
      ↓
Advanced vision only if justified
```

The model must not be selected because it sounds advanced.

It must beat a meaningful baseline under a defensible evaluation
protocol.

------------------------------------------------------------------------

# 14. Leakage Prevention

Random point-level train/test splits are prohibited.

Evaluation must prevent:

-   spatial leakage
-   temporal leakage
-   source leakage
-   repeated-event leakage

Recommended split dimensions:

``` text
geographic holdout
+
temporal holdout
+
persistent-source holdout where feasible
```

If multiple detections belong to one event/source, they must not be
scattered across train and test.

------------------------------------------------------------------------

# 15. Shortcut-Learning Tests

Run ablations:

``` text
A: FIRMS only
B: FIRMS + temporal
C: FIRMS + temporal + industrial context
D: FIRMS + temporal + land cover
E: FIRMS + satellite
F: all features
```

The goal is to demonstrate which evidence actually contributes.

Also test whether the model collapses when industrial-context features
are removed.

------------------------------------------------------------------------

# 16. Calibration and Abstention

A model prediction must produce:

``` text
class probabilities
calibrated confidence
uncertainty state
```

Possible result:

``` text
predicted class = unknown
reason = insufficient evidence
```

Coverage must be evaluated jointly with reliability.

Do not force low-evidence cases into a confident class merely to improve
coverage.

------------------------------------------------------------------------

# 17. Evidence Engine

Evidence must be generated deterministically from stored features and
source records.

Evidence can include:

-   repeated detections
-   stable location
-   industrial proximity
-   land-cover context
-   satellite availability/quality
-   temporal signature
-   FRP behavior
-   model contribution where supported

Never let an LLM invent factual evidence.

An LLM may summarize already-verified evidence later, but the underlying
evidence must come from the data pipeline.

------------------------------------------------------------------------

# 18. API Boundaries

Example resources:

``` text
GET /detections
GET /events
GET /events/{id}
GET /sources
GET /sources/{id}
GET /events/{id}/evidence
GET /events/{id}/timeline
GET /layers/industrial
GET /layers/land-cover
POST /jobs/ingest
POST /jobs/enrich
POST /jobs/classify
```

Heavy work must run through workers.

API handlers remain focused on:

``` text
validate → authorize → invoke service → return result
```

------------------------------------------------------------------------

# 19. Performance Targets

Initial engineering targets:

-   bounded FIRMS ingestion: \<30 s
-   enrichment: \<30 s/event in batch mode
-   classification: \<1 s/event excluding external downloads
-   end-to-end demo event: \<2 min when required external data is
    available
-   10,000-event offline batch: \<5 min

These are **engineering targets**, not SIH requirements.

------------------------------------------------------------------------

# 20. Deployment

Hackathon deployment:

``` text
web
api
worker
postgres-postgis
redis
object-storage
```

Optional only when justified:

``` text
mlflow
prometheus
grafana
```

Use Docker Compose for the MVP.

------------------------------------------------------------------------

# 21. Architecture Invariants

1.  Heavy processing never happens inside an HTTP request.
2.  Raw observations are immutable.
3.  Every derived artifact has provenance.
4.  Every prediction has model/version metadata.
5.  Every prediction has evidence and uncertainty metadata.
6.  OSM is contextual evidence, not ground truth.
7.  FIRMS coordinates are not treated as exact facility coordinates.
8.  Satellite absence is represented explicitly.
9.  Evaluation prevents source/spatial/temporal leakage.
10. Low-confidence predictions may abstain.
11. Large raster artifacts do not live directly in PostgreSQL.
12. External inputs are validated at boundaries.
13. External API failures are observable.
14. No metric is optimized by changing evaluation rules after seeing the
    result.
15. Context features must be tested for shortcut learning.
16. Classification ontology is separate from persistence/context
    dimensions.

------------------------------------------------------------------------

# 22. Implementation Order

## Phase 0 --- Scientific contract

Before substantial ML:

-   freeze ontology
-   define event/source semantics
-   define ground-truth schema
-   define evaluation split
-   define geospatial error metric
-   define acceptance criteria

## Phase 1 --- Data spine

-   FIRMS downloader
-   raw capture
-   canonical schema
-   validation
-   PostGIS
-   deduplication

## Phase 2 --- Event intelligence

-   clustering
-   temporal grouping
-   persistent-source tracker

## Phase 3 --- Context

-   OSM
-   land cover
-   satellite catalog/context
-   feature builder

## Phase 4 --- Baseline intelligence

-   heuristic baselines
-   feature baseline
-   XGBoost/LightGBM
-   grouped evaluation
-   calibration

## Phase 5 --- Evidence

-   evidence schema
-   deterministic evidence generation
-   uncertainty
-   provenance

## Phase 6 --- GIS integration

-   map endpoints
-   event details
-   timeline
-   source watchlist
-   map overlays

## Phase 7 --- Advanced model

Only if baseline performance and error analysis justify it.

------------------------------------------------------------------------

# 23. ADRs

## ADR-001 --- PostGIS

**Decision:** PostgreSQL + PostGIS.

**Reason:** spatial indexing, joins and relational integrity.

## ADR-002 --- Redis over Kafka for MVP

**Decision:** Redis-backed jobs.

**Reason:** lower operational complexity for bounded hackathon
workloads.

## ADR-003 --- Tabular ML before deep vision

**Decision:** engineered-feature model first.

**Reason:** ground truth is the limiting factor; model complexity cannot
rescue weak labels.

## ADR-004 --- Evidence-first predictions

**Decision:** every prediction exposes evidence and uncertainty.

**Reason:** analyst trust, auditability and differentiation.

## ADR-005 --- Abstention

**Decision:** `unknown/uncertain` is a valid result.

**Reason:** open-world thermal anomalies cannot always be classified
reliably.

## ADR-006 --- Orthogonal ontology

**Decision:** phenomenon, context, persistence and attribution are
separate dimensions.

**Reason:** prevents scientifically invalid mixing of event type,
infrastructure type and temporal behavior.

## ADR-007 --- Satellite as optional evidence per event

**Decision:** satellite integration is supported, but missing imagery
does not automatically invalidate an inference.

**Reason:** cloud cover, acquisition gaps and access constraints make
universal imagery availability unrealistic.

## ADR-008 --- Context-ablation requirement

**Decision:** context contribution must be measured with ablation tests.

**Reason:** prevents shortcut learning from industrial proximity alone.
