# SIH26162_IMPLEMENTATION_PLAN.md

> **Status:** Implementation blueprint / source of truth for subsequent
> AI-assisted coding\
> **Problem Statement:** SIH26162\
> **Official Title:** AI-Based Detection and Classification of
> Industrial Fires and Persistent Thermal Sources Using NASA FIRMS, OSM
> & Satellite Data\
> **Organization:** National Technical Research Organisation (NTRO)\
> **Category:** Software\
> **Theme:** Miscellaneous\
> **Current Phase:** Specification refinement → scientific/data
> feasibility\
> **Implementation Status:** Not yet started\
> **UI Status:** Intentionally deferred
>
> **Source discipline:** Official SIH requirements, verified source
> behavior, project decisions, assumptions, recommendations, and open
> questions are explicitly distinguished. No unmeasured capability or
> metric is represented as achieved.

------------------------------------------------------------------------

# 1. Executive Summary

## 1.1 Objective

Build an evidence-driven geospatial intelligence system that converts
ambiguous NASA FIRMS thermal observations into contextualized,
uncertainty-aware intelligence.

The system will:

1.  ingest and preserve NASA FIRMS observations;
2.  validate and normalize them into canonical internal schemas;
3.  form spatio-temporal thermal events;
4.  associate repeated events into longer-lived persistent/recurring
    sources;
5.  enrich events/sources with industrial infrastructure, land cover,
    and satellite context when available;
6.  compute interpretable features;
7.  establish deterministic baselines;
8.  train a tabular ML model only if ground-truth feasibility and
    benchmark results justify it;
9.  calibrate confidence;
10. support abstention;
11. generate deterministic evidence and uncertainty;
12. persist GIS-ready intelligence;
13. expose analyst-facing REST APIs;
14. provide map overlays and investigation workflows.

## 1.2 Core Product Principle

> **A FIRMS detection is an observation, not an explanation.**

Therefore:

``` text
Detection
→ Event
→ Persistent/Recurring Source
→ Context
→ Features
→ Classification
→ Calibration
→ Abstention
→ Evidence
→ GIS Intelligence
```

The system must not equate:

-   FIRMS coordinate with exact facility location;
-   industrial proximity with proof of industrial fire;
-   OSM data with ground truth;
-   persistence with a specific phenomenon;
-   LLM output with factual evidence.

## 1.3 Official MUST-HAVE Outcomes

The implementation must directly satisfy:

1.  industrial-fire classification/segregation from forest/natural
    fires;
2.  GIS storage of resulting intelligence;
3.  GIS map-overlay visualization.

All other components exist to make those outcomes defensible,
reproducible, and useful.

## 1.4 Implementation Strategy

The project is intentionally built in gates:

``` text
Scientific Contract
    ↓
Data Feasibility
    ↓
FIRMS Data Spine
    ↓
Event + Persistent Source Intelligence
    ↓
Context Enrichment
    ↓
Deterministic Baselines
    ↓
Ground-Truth-Backed ML
    ↓
Calibration + Abstention
    ↓
Evidence
    ↓
REST API
    ↓
GIS
    ↓
Advanced Model only if justified
```

The architecture deliberately avoids Kafka, premature microservices,
UI-led development, and unnecessary deep learning.

------------------------------------------------------------------------

# 2. Current Project State

## 2.1 Status

**Phase:** Specification refinement → scientific/data feasibility.

**Implementation:** Not yet started.

**UI:** Deferred.

## 2.2 Completed Decisions

-   Official SIH requirements identified.
-   Project metadata corrected to `NTRO / Software / Miscellaneous`.
-   Product thesis defined.
-   Detection → Event → Persistent Source hierarchy defined.
-   Orthogonal ontology defined.
-   Evidence-first output defined.
-   Abstention accepted as a valid outcome.
-   Ground-truth provenance policy defined.
-   Spatial/temporal/source leakage prevention defined.
-   PostGIS selected.
-   Redis selected instead of Kafka for MVP job coordination.
-   Tabular ML selected before deep vision.
-   Satellite imagery treated as optional evidence per event.
-   Context ablation made mandatory.
-   Architecture invariants defined.
-   Development sequence defined.

## 2.3 Not Yet Validated

-   Demonstration geography.
-   Historical FIRMS event volume in the selected geography.
-   Sufficient Tier A/B ground-truth volume.
-   Final supported phenomenon taxonomy.
-   Exact event clustering parameters.
-   Exact persistence thresholds.
-   Exact contextual proximity threshold.
-   Exact benchmark window.
-   Exact geospatial attribution-error metric.
-   Satellite product priority for the selected geography.
-   Final ML acceptance thresholds.
-   Final demo scenario.

## 2.4 Current Priority

The immediate goal is to reduce uncertainty, not add features.

------------------------------------------------------------------------

# 3. Frozen Decisions

The following are protected unless new evidence causes an explicit
architecture/specification change.

  -----------------------------------------------------------------------------------------------
  Decision                                     Status                                    Priority
  -------------------------------------------- --------------------- ----------------------------
  Industrial-fire segregation + GIS are        FACT                                            P0
  official MUST requirements                                         

  FIRMS is an observation source, not ground   VERIFIED                                        P0
  truth                                                              

  Detection, Event, Persistent Source are      RECOMMENDATION                                  P0
  separate entities                                                  

  Phenomenon/context/persistence/attribution   RECOMMENDATION                                  P0
  are orthogonal                                                     

  Evidence must be data-backed                 RECOMMENDATION                                  P0

  Abstention is valid                          RECOMMENDATION                                  P0

  PostGIS is primary geospatial store          RECOMMENDATION                                  P0

  Redis-backed jobs for MVP                    RECOMMENDATION                                  P0

  No Kafka initially                           RECOMMENDATION                                  P0

  Baseline before ML                           RECOMMENDATION                                  P0

  No random point-level final benchmark        RECOMMENDATION                                  P0

  Context ablation is mandatory                RECOMMENDATION                                  P0

  Satellite absence must be explicit           RECOMMENDATION                                  P0

  LLM cannot generate factual evidence         RECOMMENDATION                                  P0

  Raw observations remain immutable            RECOMMENDATION                                  P0

  UI-led development is prohibited             RECOMMENDATION                                  P0

  Advanced vision is conditional               PROVISIONAL                                     P1
  -----------------------------------------------------------------------------------------------

------------------------------------------------------------------------

# 4. Open Questions

These must not be silently resolved.

  -----------------------------------------------------------------------
  ID                      Question                Blocks
  ----------------------- ----------------------- -----------------------
  OQ-001                  What Indian             Dataset/benchmark
                          demonstration geography 
                          has sufficient          
                          diversity and reference 
                          evidence?               

  OQ-002                  How many Tier A/B       ML scope
                          events are available?   

  OQ-003                  Which phenomenon        Ontology freeze
                          classes have real       
                          labels?                 

  OQ-004                  What exact rule defines Persistence
                          persistent vs           
                          recurring?              

  OQ-005                  What spatial distance   Context features
                          rule is appropriate for 
                          contextual proximity?   

  OQ-006                  What reference geometry Spatial metric
                          supports geospatial     
                          attribution error?      

  OQ-007                  Which satellite product Satellite branch
                          is preferred for the    
                          chosen geography?       

  OQ-008                  What is the final       Evaluation
                          benchmark time window?  

  OQ-009                  What selective          Abstention
                          precision/recall        
                          constraints define      
                          acceptable inference?   

  OQ-010                  What is the exact demo  Demo integration
                          scenario?               
  -----------------------------------------------------------------------

### Rule

An implementation unit may proceed behind a replaceable configuration
boundary when an open question does not block it. It must not convert a
provisional value into a scientific claim.

------------------------------------------------------------------------

# 5. Assumptions

  ----------------------------------------------------------------------------------
  ID                Assumption                 Status             Consequence
  ----------------- -------------------------- ------------------ ------------------
  A-001             FIRMS historical           ASSUMPTION         Must be validated
                    observations can be                           in
                    acquired for the selected                     data-feasibility
                    study area/time period                        gate

  A-002             OSM contains useful        ASSUMPTION         Must measure
                    industrial/context                            completeness
                    features in at least part                     
                    of the study area                             

  A-003             Suitable land-cover data   ASSUMPTION         Product/version
                    can be obtained for the                       must be recorded
                    study area                                    

  A-004             Some Tier A/B reference    ASSUMPTION         Determines ML
                    events can be assembled                       scope

  A-005             Tabular                    ASSUMPTION         Must be measured
                    temporal/spatial/context                      
                    features will provide a                       
                    useful baseline                               

  A-006             Satellite context will be  VERIFIED/ASSUMED   Pipeline must
                    unavailable for some       OPERATIONAL        tolerate missing
                    events                     CONDITION          imagery

  A-007             MVP workload does not      RECOMMENDATION     Revisit only with
                    require Kafka-level                           measured evidence
                    infrastructure                                

  A-008             A bounded Indian geography RECOMMENDATION     Enables evaluation
                    is preferable to                              and demo
                    uncontrolled global                           defensibility
                    coverage                                      
  ----------------------------------------------------------------------------------

------------------------------------------------------------------------

# 6. Target Architecture

## 6.1 Logical Architecture

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

## 6.2 Major Component Contract

### Architecture Orchestrator

-   **Build:** application boundaries connecting ingestion, processing,
    enrichment, ML, evidence, storage, API and GIS.
-   **Why:** prevent domain logic from collapsing into a monolith.
-   **Dependencies:** all domain modules.
-   **Inputs:** validated domain entities.
-   **Outputs:** persisted derived entities.
-   **Database:** coordinates repositories and transaction boundaries.
-   **API:** no direct domain logic in route handlers.
-   **Testing:** integration tests across bounded workflows.
-   **Acceptance:** each stage can be invoked independently and traced.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

------------------------------------------------------------------------

# 7. Backend Architecture

## 7.1 Stack

-   Python 3.11+
-   FastAPI
-   Pydantic
-   PostgreSQL + PostGIS
-   Redis
-   Python worker
-   GeoPandas/Shapely
-   Rasterio/GDAL where required
-   scikit-learn
-   XGBoost or LightGBM
-   Docker Compose for MVP

## 7.2 Domain Boundaries

``` text
services/api/
services/worker/
services/ml/
packages/schemas/
packages/geospatial/
packages/evidence/
```

The exact repository layout may evolve, but these boundaries must
remain.

## 7.3 API Service

-   **Build:** thin HTTP layer, request validation, authorization,
    service invocation, response serialization.
-   **Why:** keep HTTP concerns separate from domain/data logic.
-   **Dependencies:** schemas, services, repositories.
-   **Inputs:** HTTP requests.
-   **Outputs:** typed API responses.
-   **Database:** access only through repository/service boundaries.
-   **API:** owns public REST contract.
-   **Testing:** API contract, validation, authorization, failure tests.
-   **Acceptance:** handlers remain thin; external calls are not hidden
    in routes.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

## 7.4 Worker

-   **Build:** asynchronous jobs for ingestion, enrichment, event
    formation, persistence, classification and exports.
-   **Why:** heavy processing must not execute inside HTTP requests.
-   **Dependencies:** Redis, domain services.
-   **Inputs:** job payloads.
-   **Outputs:** persisted derived state + job status.
-   **Database:** job metadata and processing status.
-   **API:** jobs exposed through status endpoints.
-   **Testing:** idempotency, retry, failure and job-state tests.
-   **Acceptance:** HTTP requests remain bounded and jobs are
    observable.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

------------------------------------------------------------------------

# 8. Database Design

## 8.1 PostgreSQL + PostGIS

**Status:** RECOMMENDATION, P0.

Primary storage for relational and geospatial intelligence.

## 8.2 Core Tables

### `source_records`

Raw source/provenance metadata.

Key fields:

``` text
source_record_id
source_name
source_type
product
product_version
source_url/reference
acquired_at
ingested_at
raw_hash
storage_location
status
```

### `firms_detections`

Canonical thermal observations.

Key fields:

``` text
detection_id
source_record_id
source_identifier
satellite
instrument
product_type
product_version
acquisition_time
latitude
longitude
geometry
frp_mw
brightness_ti4_k
brightness_ti5_k
confidence
scan
track
day_night
ingestion_time
raw_payload_reference
```

### `thermal_events`

Derived spatio-temporal events.

``` text
event_id
formation_version
start_time
end_time
duration
geometry
centroid
detection_count
spatial_footprint
frp_statistics
created_at
```

### `event_detections`

Many-to-many/event membership relation where required.

``` text
event_id
detection_id
membership_version
```

### `persistent_sources`

Longer-lived spatial source entities.

``` text
source_id
geometry
first_seen
last_seen
active_days
event_count
recurrence_statistics
spatial_stability
centroid_drift
persistence_state
attribution_state
```

### `source_events`

Source/event association.

``` text
source_id
event_id
association_version
```

### `context_features`

Context evidence.

``` text
context_id
entity_type
entity_reference
geometry
feature_type
distance
attributes
source_name
source_version
retrieved_at
```

### `land_cover_observations`

``` text
id
geometry
product
product_version
class
retrieved_at
quality_metadata
```

### `satellite_observations`

``` text
id
event_id/source_id
catalog
asset_id
acquisition_time
cloud/quality metadata
availability_status
asset_reference
```

### `feature_sets`

``` text
feature_set_id
entity_type
entity_id
feature_version
features_json
generated_at
```

### `model_predictions`

``` text
prediction_id
entity_type
entity_id
model_version
feature_version
dataset_version
phenomenon
context
persistence_state
attribution_strength
raw_probabilities
calibrated_confidence
uncertainty_state
abstained
created_at
```

### `evidence_items`

``` text
evidence_id
entity_type
entity_id
evidence_type
evidence_value
source_reference
generated_from_feature_version
generated_at
```

### `evaluation_runs`

``` text
evaluation_run_id
dataset_version
split_definition
model_version
metrics
created_at
```

## 8.3 Database Rules

-   Raw observations immutable.
-   Derived records versioned.
-   Geometries remain distinct.
-   Provenance retained.
-   Model/data/feature versions linked.
-   No contextual feature is persisted as a ground-truth label merely
    because it is nearby.

## 8.4 Acceptance Criteria

-   migrations reproducibly create schema;
-   spatial indexes exist for primary geospatial tables;
-   foreign-key relationships preserve traceability;
-   raw and derived data are distinguishable;
-   historical data can be replayed.

------------------------------------------------------------------------

# 9. Data Ingestion Architecture

## 9.1 FIRMS Ingestion

-   **Build:** downloader/client → raw capture → validation → canonical
    normalization → deduplication → PostGIS.
-   **Why:** establish the immutable data spine.
-   **Dependencies:** FIRMS access, database, schemas.
-   **Inputs:** FIRMS product data.
-   **Outputs:** raw source record + canonical detection rows.
-   **Database:** `source_records`, `firms_detections`.
-   **API:** ingestion jobs and status.
-   **Testing:** fixtures, malformed rows, duplicate input, retries,
    provenance.
-   **Acceptance:** same source input can be replayed without corrupting
    or duplicating canonical observations.
-   **Priority:** P0.
-   **Status:** VERIFIED architecture pattern / RECOMMENDATION.

## 9.2 Provenance

Every observation must retain:

-   source;
-   satellite;
-   instrument;
-   acquisition timestamp;
-   product/version;
-   original identifier/hash;
-   ingestion timestamp;
-   raw reference.

**Priority:** P0. **Status:** RECOMMENDATION.

## 9.3 External Failure Handling

Every source client requires:

-   timeout;
-   retry policy;
-   rate-limit handling;
-   structured errors;
-   provenance;
-   fixture;
-   fallback behavior where meaningful.

External failure must be visible.

------------------------------------------------------------------------

# 10. Detection/Event/Persistent Source Architecture

## 10.1 Detection

**Definition:** one FIRMS source observation.

-   **Build:** canonical detection entity.
-   **Why:** preserve atomic observations.
-   **Dependencies:** ingestion.
-   **Inputs:** FIRMS records.
-   **Outputs:** immutable detection.
-   **Database:** `firms_detections`.
-   **API:** detection query endpoint.
-   **Testing:** schema/identity/provenance tests.
-   **Acceptance:** every derived entity can trace back to source
    observations.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

## 10.2 Event Formation

**Definition:** configurable spatio-temporal grouping of detections
believed to represent one episode.

-   **Build:** clustering engine.
-   **Why:** operational intelligence should not treat every satellite
    point as an independent incident.
-   **Dependencies:** detections, geospatial library.
-   **Inputs:** detections + configurable/versioned clustering
    configuration.
-   **Outputs:** event geometry, time span, membership, statistics.
-   **Database:** `thermal_events`, `event_detections`.
-   **API:** event retrieval.
-   **Testing:** synthetic clustering fixtures, boundary cases,
    reproducibility.
-   **Acceptance:** memberships are traceable and clustering version is
    stored.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

**Important:** exact spatial/temporal thresholds are OPEN QUESTIONS
until validated.

## 10.3 Persistent Source Association

-   **Build:** event-to-source association and persistence statistics.
-   **Why:** distinguish one-off events from repeated/persistent thermal
    sources.
-   **Dependencies:** events, geospatial association.
-   **Inputs:** event geometries/timestamps.
-   **Outputs:** source entities and persistence state.
-   **Database:** `persistent_sources`, `source_events`.
-   **API:** source endpoints/timelines.
-   **Testing:** repeated-event synthetic cases, source
    merging/splitting tests.
-   **Acceptance:** source identity is separate from event identity.
-   **Priority:** P1.
-   **Status:** RECOMMENDATION.

## 10.4 Persistence

Supported state vocabulary:

``` text
transient
recurring
persistent
insufficient_history
```

Exact thresholds remain **OPEN QUESTION OQ-004**.

------------------------------------------------------------------------

# 11. Context Enrichment

## 11.1 OSM / Industrial Context

-   **Build:** query/retrieval, normalization, geometry association,
    distance calculation.
-   **Why:** provide contextual evidence about industrial surroundings.
-   **Dependencies:** OSM/Overpass, geospatial package, study area.
-   **Inputs:** event/source geometry.
-   **Outputs:** facility/infrastructure features + distance +
    provenance.
-   **Database:** `context_features`.
-   **API:** context layers and event evidence.
-   **Testing:** fixtures, missing tags, distance/CRS tests, API failure
    tests.
-   **Acceptance:** OSM proximity is represented as evidence, never
    automatically as ground truth.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

## 11.2 Land Cover

-   **Build:** land-cover lookup/sampling pipeline.
-   **Why:** distinguish forest/vegetation/agricultural/other contextual
    environments.
-   **Dependencies:** selected land-cover product.
-   **Inputs:** event/source geometry.
-   **Outputs:** class + product/version + retrieval metadata.
-   **Database:** `land_cover_observations`.
-   **API:** context/layer endpoints.
-   **Testing:** CRS, raster lookup, missing-data fixtures.
-   **Acceptance:** land-cover version and sampling geometry are
    preserved.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

## 11.3 Satellite Context

-   **Build:** catalog search and asset metadata retrieval; imagery
    processing only when justified.
-   **Why:** provide additional evidence where optical/other satellite
    data is available.
-   **Dependencies:** selected catalog/product, STAC or equivalent
    interface where applicable.
-   **Inputs:** event/source geometry + time range.
-   **Outputs:** availability/quality metadata and optional asset
    reference.
-   **Database:** `satellite_observations`.
-   **API:** event satellite-context endpoint.
-   **Testing:** unavailable imagery, cloud/quality filtering, catalog
    failure.
-   **Acceptance:** missing imagery is explicitly represented as
    unavailable; no fake evidence is produced.
-   **Priority:** P1.
-   **Status:** PROVISIONAL.

## 11.4 Context Ablation

Mandatory benchmark:

``` text
FIRMS only
vs
FIRMS + temporal
vs
FIRMS + context
vs
FIRMS + satellite
vs
all
```

The exact experimental matrix may expand after data inspection.

------------------------------------------------------------------------

# 12. Feature Engineering

## 12.1 Feature Groups

### FIRMS

-   confidence;
-   FRP;
-   brightness temperatures where available;
-   scan/track;
-   day/night;
-   satellite/instrument;
-   acquisition timing.

### Temporal

-   active days;
-   recurrence;
-   duration;
-   temporal gaps;
-   periodicity where enough history exists;
-   day/night pattern.

### Spatial

-   cluster size;
-   spatial density;
-   centroid drift;
-   footprint stability.

### Context

-   distance to industrial facilities;
-   facility type;
-   land-cover class;
-   nearby infrastructure context.

### Satellite

Only when availability and quality are sufficient.

## 12.2 Feature Builder Contract

-   **Build:** deterministic feature-generation layer.
-   **Why:** provide reproducible inputs to baselines and ML.
-   **Dependencies:** detection/event/source/context tables.
-   **Inputs:** canonical entities and context.
-   **Outputs:** versioned feature set.
-   **Database:** `feature_sets`.
-   **API:** feature details only where useful for analyst/audit
    endpoints.
-   **Testing:** feature correctness, null/missing context, CRS,
    temporal aggregation.
-   **Acceptance:** same versioned input produces reproducible features.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

## 12.3 Missingness

Missing context must remain explicit.

Examples:

``` text
satellite_evidence_status = unavailable
land_cover_status = unavailable
osm_context_status = unavailable
```

Missingness must not silently become a negative feature unless the
feature semantics explicitly define it.

------------------------------------------------------------------------

# 13. Ground Truth & Dataset Strategy

## 13.1 Reference Event Registry

Minimum fields:

``` text
event_id
label
label_source
source_url
source_date
geographic_evidence
temporal_evidence
label_confidence
annotator
annotation_notes
```

## 13.2 Label Tiers

### Tier A --- authoritative

-   government/official incident reports;
-   credible regulatory records;
-   appropriate company disclosures.

### Tier B --- strong independent evidence

-   reputable reporting with time/location;
-   multiple independent sources;
-   validated reference databases.

### Tier C --- weak/proxy

-   OSM proximity;
-   inferred context;
-   unsourced reports.

Tier C cannot be represented as equivalent to Tier A.

## 13.3 Dataset Construction

-   Build candidate events from FIRMS.
-   Search for independent reference evidence.
-   Record provenance.
-   Assign label tier.
-   Reject unsupported hard labels.
-   Freeze dataset version before benchmark.
-   Keep annotation notes.

## 13.4 Ground-Truth Feasibility Gate

Measure:

-   candidate event count;
-   Tier A count;
-   Tier B count;
-   Tier C count;
-   class distribution;
-   geographic coverage;
-   temporal coverage;
-   source diversity.

If sufficient labels do not exist:

``` text
reduce taxonomy
→ retain deterministic baselines
→ use weak supervision only for exploration
→ keep uncertainty explicit
```

**No label manufacturing is permitted.**

## 13.5 Component Contract

-   **Build:** reference-event registry + dataset versioning workflow.
-   **Why:** establish defensible evaluation.
-   **Dependencies:** selected geography, FIRMS history, reference
    research.
-   **Inputs:** candidate events + evidence.
-   **Outputs:** versioned labeled dataset.
-   **Database:** reference registry + evaluation metadata.
-   **API:** not necessarily user-facing in MVP.
-   **Testing:** provenance completeness, duplicate labels,
    temporal/geographic consistency.
-   **Acceptance:** every hard label has traceable provenance.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

------------------------------------------------------------------------

# 14. ML Architecture

## 14.1 Model Sequence

``` text
Baseline 1: FIRMS confidence
        ↓
Baseline 2: industrial/context proximity
        ↓
Baseline 3: persistence
        ↓
Baseline 4: combined deterministic rules
        ↓
simple feature model
        ↓
XGBoost / LightGBM
        ↓
calibration
        ↓
abstention
```

## 14.2 ML Component Contract

-   **Build:** versioned training/evaluation/inference pipeline.
-   **Why:** improve over deterministic evidence combinations only when
    justified.
-   **Dependencies:** valid labels, feature sets, benchmark protocol.
-   **Inputs:** versioned feature set + labeled training data.
-   **Outputs:** model artifact + raw predictions + metadata.
-   **Database:** model/prediction/evaluation metadata.
-   **API:** inference result endpoints.
-   **Testing:** feature consistency, inference determinism, model
    serialization, leakage tests.
-   **Acceptance:** ML materially improves over a meaningful baseline
    under the frozen benchmark.
-   **Priority:** P1.
-   **Status:** PROVISIONAL until feasibility gate.

## 14.3 Deep Vision

PyTorch/deep vision is **not part of the guaranteed MVP**.

It may be introduced only if:

1.  imagery availability is sufficient;
2.  labels support image supervision;
3.  tabular/context baselines show a meaningful error gap;
4.  added complexity is justified.

**Priority:** P3 initially. **Status:** PROVISIONAL.

## 14.4 LLM

LLM is not the primary classifier.

Potential later role:

``` text
validated evidence
→ LLM summary
```

Never:

``` text
raw FIRMS
→ LLM
→ factual classification/evidence
```

------------------------------------------------------------------------

# 15. Calibration & Abstention

## 15.1 Calibration

-   **Build:** probability calibration after model selection.
-   **Why:** exposed confidence must be meaningful enough for analyst
    use.
-   **Dependencies:** trained model + validation data.
-   **Inputs:** raw model probabilities.
-   **Outputs:** calibrated probabilities/confidence.
-   **Database:** prediction metadata stores calibration/model version.
-   **API:** calibrated confidence returned with intelligence result.
-   **Testing:** calibration metrics and calibration-set separation.
-   **Acceptance:** probabilities are evaluated, not merely emitted.
-   **Priority:** P1.
-   **Status:** RECOMMENDATION.

## 15.2 Abstention

Possible output:

``` text
unknown / uncertain
reason = insufficient evidence
```

-   **Build:** confidence/evidence-based selective classification
    policy.
-   **Why:** open-world thermal anomalies cannot all be classified
    reliably.
-   **Dependencies:** calibration + evidence availability.
-   **Inputs:** calibrated confidence, evidence completeness, model
    state.
-   **Outputs:** class or abstention.
-   **Database:** `abstained`, uncertainty state, reason.
-   **API:** explicit uncertainty/abstention fields.
-   **Testing:** risk-coverage behavior.
-   **Acceptance:** low-evidence cases can abstain and are not silently
    forced into a class.
-   **Priority:** P1.
-   **Status:** RECOMMENDATION.

Exact operating thresholds remain OPEN until benchmark evidence exists.

------------------------------------------------------------------------

# 16. Evidence & Uncertainty

## 16.1 Evidence Engine

Evidence must be generated deterministically from validated system
state.

Potential evidence:

``` text
+ repeated detections
+ active-day count
+ stable spatial footprint
+ industrial facility within configured threshold
+ land-cover context
+ temporal signature
+ FRP behavior
+ satellite evidence availability/quality
- missing satellite imagery
- insufficient historical coverage
```

## 16.2 Component Contract

-   **Build:** deterministic evidence rule engine.
-   **Why:** make every prediction auditable.
-   **Dependencies:** feature store, provenance, prediction state.
-   **Inputs:** validated facts/features.
-   **Outputs:** evidence items + limitations + uncertainty.
-   **Database:** `evidence_items`.
-   **API:** `/events/{id}/evidence` and intelligence result fields.
-   **Testing:** evidence correctness against fixtures;
    forbidden-inference tests.
-   **Acceptance:** every factual evidence statement can be traced to
    stored data.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

## 16.3 Uncertainty

Uncertainty should distinguish:

-   model confidence;
-   insufficient history;
-   missing context;
-   unavailable imagery;
-   weak attribution;
-   ambiguous phenomenon.

Do not compress all uncertainty into a single unexplained number.

------------------------------------------------------------------------

# 17. Intelligence Result

## 17.1 Canonical Result

Conceptual representation:

``` json
{
  "phenomenon": "flare",
  "context": "oil_gas",
  "persistence": "persistent",
  "attribution": "strong",
  "confidence": 0.91,
  "evidence": [],
  "limitations": [],
  "provenance": {},
  "model_version": ""
}
```

The exact production schema must be defined in the API/schema
implementation unit and versioned.

## 17.2 Required Dimensions

``` text
phenomenon
context
persistence_state
attribution_strength
confidence
uncertainty
evidence
limitations
provenance
model_version
feature_version
dataset_version
```

## 17.3 Component Contract

-   **Build:** versioned intelligence-result schema and persistence.
-   **Why:** create the canonical analyst-facing output.
-   **Dependencies:** classification, calibration, evidence.
-   **Inputs:** event/source + model/evidence state.
-   **Outputs:** intelligence result.
-   **Database:** predictions/evidence/provenance.
-   **API:** core response object.
-   **Testing:** schema, provenance, uncertainty, backward
    compatibility.
-   **Acceptance:** no result can omit required provenance/evidence
    state.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

------------------------------------------------------------------------

# 18. REST API Specification

## 18.1 API Principles

Routes must:

``` text
validate
→ authorize
→ invoke service
→ return typed response
```

Heavy processing must run through workers.

## 18.2 Detection Endpoints

``` text
GET /detections
GET /detections/{id}
```

**Purpose:** retrieve canonical FIRMS observations.

## 18.3 Event Endpoints

``` text
GET /events
GET /events/{id}
GET /events/{id}/timeline
GET /events/{id}/evidence
GET /events/{id}/context
GET /events/{id}/satellite
```

## 18.4 Persistent Source Endpoints

``` text
GET /sources
GET /sources/{id}
GET /sources/{id}/timeline
GET /sources/{id}/events
GET /sources/{id}/evidence
```

## 18.5 Layer Endpoints

``` text
GET /layers/industrial
GET /layers/land-cover
GET /layers/events
GET /layers/sources
```

## 18.6 Job Endpoints

``` text
POST /jobs/ingest
POST /jobs/enrich
POST /jobs/classify
GET /jobs/{id}
```

## 18.7 API Contract

-   **Build:** OpenAPI-backed typed REST interface.
-   **Why:** expose intelligence and GIS data consistently.
-   **Dependencies:** domain services, schemas, repositories.
-   **Inputs:** validated HTTP requests.
-   **Outputs:** typed JSON/GeoJSON as appropriate.
-   **Database:** read/write through service boundaries.
-   **Testing:** contract tests, validation tests, authorization, error
    handling.
-   **Acceptance:** API documentation generated from the actual
    implementation and matches response schemas.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

Exact pagination/filter semantics may be finalized during API
implementation without changing scientific contracts.

------------------------------------------------------------------------

# 19. Worker/Job Architecture

## 19.1 Job Types

``` text
INGEST_FIRMS
VALIDATE_NORMALIZE
FORM_EVENTS
ASSOCIATE_SOURCES
ENRICH_OSM
ENRICH_LAND_COVER
RETRIEVE_SATELLITE_CONTEXT
BUILD_FEATURES
RUN_BASELINE
RUN_ML
CALIBRATE
GENERATE_EVIDENCE
EXPORT_GIS
```

## 19.2 Job Contract

Each job should have:

``` text
job_id
job_type
status
created_at
started_at
completed_at
input_reference
configuration_version
attempt_count
error_code
error_message
```

## 19.3 Redis

Redis is used for MVP job coordination/cache where appropriate.

**No Kafka.**

Kafka can only be reconsidered after measured evidence of a
workload/coordination limitation.

-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

## 19.4 Idempotency

Jobs must be safe to retry.

A repeated ingestion or enrichment job must not create uncontrolled
duplicate derived records.

------------------------------------------------------------------------

# 20. GIS Integration

## 20.1 Objective

Provide the required GIS storage and map-overlay visualization.

## 20.2 Map Layers

Minimum:

-   thermal detections;
-   thermal events;
-   persistent sources;
-   industrial/context features;
-   land-cover context;
-   classification/attribution state.

## 20.3 Geometry Discipline

Maintain separately:

``` text
detection_geometry
event_geometry
source_geometry
facility_geometry
```

Never overwrite event/source geometry with facility geometry merely
because of proximity.

## 20.4 Frontend

Target:

-   Next.js;
-   TypeScript;
-   MapLibre GL JS.

UI implementation remains downstream of intelligence validation.

## 20.5 GIS Component Contract

-   **Build:** GIS-ready APIs + map overlay rendering.
-   **Why:** satisfy official GIS requirement and enable analyst
    investigation.
-   **Dependencies:** PostGIS, API, intelligence results.
-   **Inputs:** GeoJSON/map-ready features.
-   **Outputs:** interactive overlays/details.
-   **Database:** PostGIS geometries and spatial indexes.
-   **API:** layer endpoints.
-   **Testing:** geometry validity, CRS, API contract, map rendering
    smoke tests.
-   **Acceptance:** analyst can visualize events/sources and inspect
    associated intelligence/evidence.
-   **Priority:** P0.
-   **Status:** FACT requirement + RECOMMENDATION implementation.

------------------------------------------------------------------------

# 21. Testing Strategy

## 21.1 Unit Tests

Required for:

-   schemas;
-   FIRMS parsing;
-   normalization;
-   deduplication;
-   CRS/distance;
-   clustering;
-   persistence;
-   feature generation;
-   evidence generation;
-   calibration;
-   inference.

## 21.2 Integration Tests

Test:

``` text
FIRMS fixture
→ ingestion
→ database
→ event formation
→ enrichment
→ features
→ baseline
→ evidence
→ API
```

## 21.3 External API Tests

Fixtures must cover:

-   timeout;
-   rate limiting;
-   malformed response;
-   unavailable resource;
-   partial response.

## 21.4 Leakage Tests

Explicit tests must ensure:

-   one event cannot cross train/test;
-   persistent source observations cannot cross source-grouped splits;
-   duplicate observations cannot cross splits;
-   future information cannot leak into historical features.

## 21.5 Evidence Correctness Tests

Every evidence type must be tested against known stored state.

An LLM-generated statement is not accepted as evidence.

## 21.6 Definition

A feature without tests is incomplete.

**Priority:** P0.\
**Status:** RECOMMENDATION.

------------------------------------------------------------------------

# 22. Evaluation & Benchmarking

## 22.1 Benchmark Principle

Do not optimize for one headline accuracy number.

Report, where applicable:

-   precision;
-   recall;
-   macro F1;
-   PR-AUC;
-   calibration;
-   selective risk/coverage;
-   event-level false-positive rate;
-   persistence-source F1;
-   spatial attribution error where a valid reference geometry exists;
-   latency;
-   evidence completeness.

## 22.2 Split Rules

Final benchmark must prevent:

-   spatial leakage;
-   temporal leakage;
-   event leakage;
-   persistent-source leakage;
-   duplicated observation leakage.

Preferred design:

``` text
geographic holdout
+
temporal holdout
+
source/event grouping where feasible
```

## 22.3 Baseline Ladder

``` text
B1: FIRMS confidence
B2: industrial proximity/context
B3: persistence
B4: combined rules
B5: simple feature model
B6: XGBoost/LightGBM
```

## 22.4 Mandatory Ablation

``` text
A: FIRMS only
B: FIRMS + temporal
C: FIRMS + temporal + industrial context
D: FIRMS + temporal + land cover
E: FIRMS + satellite
F: all
```

## 22.5 Context Shortcut Test

Test whether the model can succeed mainly from:

``` text
industrial facility proximity
```

If so, evaluate performance with context removed.

## 22.6 Performance Claims

No metric is considered achieved until measured on a frozen, valid
benchmark.

Existing engineering targets are targets only:

-   bounded FIRMS ingestion: `<30 s`;
-   enrichment: `<30 s/event` in batch mode;
-   classification: `<1 s/event` excluding external downloads;
-   end-to-end demo event: `<2 min` when required external data is
    available;
-   10,000-event offline batch: `<5 min`.

These are **team engineering targets**, not official SIH requirements.

------------------------------------------------------------------------

# 23. Security

## 23.1 Secrets

-   FIRMS keys remain server-side.
-   Secrets live in environment/secret storage.
-   No credentials in source control.
-   No credentials in logs.

## 23.2 Input Validation

Validate:

-   API input;
-   external payloads;
-   file imports;
-   job parameters;
-   geometry;
-   configuration.

## 23.3 Authorization

Authorization must be enforced before mutations and administrative
actions.

## 23.4 Security Logging

Record security-relevant failures without exposing secrets.

## 23.5 Component Contract

-   **Build:** secret management, validation, authorization, safe
    logging.
-   **Why:** protect external credentials and system integrity.
-   **Dependencies:** API and deployment.
-   **Inputs:** credentials/user/external inputs.
-   **Outputs:** authorized operations + structured failures.
-   **Database:** do not persist secrets.
-   **API:** authenticated/authorized mutation endpoints.
-   **Testing:** secret leakage, unauthorized access, malformed input.
-   **Acceptance:** no secret reaches browser/client/logs.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

------------------------------------------------------------------------

# 24. Observability

## 24.1 Minimum Operational Metrics

Track:

-   ingestion success/failure;
-   external API latency;
-   external API error rate;
-   jobs queued/running/failed;
-   processing latency by stage;
-   event formation counts;
-   enrichment success/missingness;
-   model inference latency;
-   abstention rate;
-   evidence completeness;
-   database errors.

## 24.2 Provenance/Traceability

Every derived result should be traceable through:

``` text
prediction
→ model version
→ feature version
→ event/source
→ detections
→ source/provenance record
```

## 24.3 Monitoring Stack

Prometheus/Grafana may be added after the core pipeline is functional.

**Priority:** P2.\
**Status:** PROVISIONAL.

------------------------------------------------------------------------

# 25. Deployment

## 25.1 MVP

Use Docker Compose with:

``` text
web
api
worker
postgres-postgis
redis
object-storage
```

Optional:

``` text
mlflow
prometheus
grafana
```

## 25.2 Deployment Rules

-   external credentials supplied through environment/secret
    configuration;
-   migrations run explicitly;
-   raw data can be restored/replayed;
-   model artifacts versioned;
-   service health checks available.

## 25.3 Component Contract

-   **Build:** reproducible local/hackathon deployment.
-   **Why:** minimize operational complexity.
-   **Dependencies:** Docker, configuration, database, Redis.
-   **Inputs:** container configuration and artifacts.
-   **Outputs:** running application stack.
-   **Database:** persistent PostGIS volume.
-   **API:** service discovery/routing.
-   **Testing:** clean-environment startup and migration tests.
-   **Acceptance:** stack starts from documented configuration and
    passes smoke tests.
-   **Priority:** P1.
-   **Status:** RECOMMENDATION.

------------------------------------------------------------------------

# 26. Offline/Failure Strategy

## 26.1 External Data Failure

If FIRMS is unavailable:

-   use previously captured immutable historical data;
-   expose ingestion failure;
-   do not fabricate current data.

If OSM is unavailable:

-   retain event intelligence;
-   mark context unavailable.

If satellite imagery is unavailable:

``` text
satellite_evidence_status = unavailable
```

Do not pretend imagery was analyzed.

## 26.2 Partial Pipeline Failure

The pipeline should permit completed stages to remain valid.

Example:

``` text
FIRMS ingestion succeeds
→ event formation succeeds
→ OSM fails
→ event remains valid
→ context marked unavailable
→ downstream classification decides whether evidence is sufficient
```

## 26.3 Retry

Retries must be bounded and observable.

## 26.4 Replay

Historical source records must support deterministic reprocessing.

**Priority:** P0.\
**Status:** RECOMMENDATION.

------------------------------------------------------------------------

# 27. Performance Strategy

## 27.1 Principles

Optimize only after measurement.

Primary strategies:

-   batch external requests where supported;
-   spatial indexes;
-   indexed temporal queries;
-   bounded worker concurrency;
-   caching immutable external data;
-   avoid unnecessary raster downloads;
-   precompute reusable event/source features;
-   keep heavy work out of API requests.

## 27.2 Latency Accounting

Report separately:

``` text
external acquisition latency
internal processing latency
end-to-end latency
```

Never hide external network time inside an unexplained model-latency
claim.

## 27.3 Scaling Boundary

MVP scaling target:

``` text
single deployment
+
multiple worker processes
+
PostGIS
+
Redis
```

Do not introduce distributed streaming infrastructure without measured
need.

------------------------------------------------------------------------

# 28. Development Phases

## Phase 0 --- Scientific Contract

Deliver:

-   ontology;
-   event/source semantics;
-   ground-truth schema;
-   benchmark protocol;
-   geospatial error definition;
-   acceptance criteria.

**Gate:** no unresolved scientific ambiguity that blocks data
interpretation.

## Phase 1 --- Data Feasibility

Deliver:

-   selected geography;
-   FIRMS sample;
-   event-volume estimate;
-   label feasibility estimate;
-   class balance;
-   OSM completeness assessment;
-   satellite availability assessment.

**Gate:** determine supported taxonomy and ML feasibility.

## Phase 2 --- Data Spine

Deliver:

-   FIRMS client;
-   raw storage;
-   canonical schema;
-   validation;
-   deduplication;
-   PostGIS.

**Gate:** reproducible historical ingestion.

## Phase 3 --- Event Intelligence

Deliver:

-   clustering;
-   event persistence statistics;
-   source association.

**Gate:** traceable detection → event → source hierarchy.

## Phase 4 --- Context

Deliver:

-   OSM;
-   land cover;
-   satellite catalog/context;
-   feature builder.

**Gate:** context availability and ablation-ready features.

## Phase 5 --- Baseline

Deliver:

-   deterministic baselines;
-   benchmark;
-   error analysis.

**Gate:** establish real baseline before ML complexity.

## Phase 6 --- ML

Conditional on labels:

-   feature model;
-   XGBoost/LightGBM;
-   calibration;
-   abstention;
-   ablations.

**Gate:** ML must materially improve over baseline.

## Phase 7 --- Evidence

Deliver:

-   evidence schema;
-   deterministic evidence generation;
-   uncertainty;
-   provenance.

**Gate:** every result auditable.

## Phase 8 --- API + GIS

Deliver:

-   REST API;
-   map layers;
-   event/source detail;
-   timelines;
-   evidence views.

**Gate:** official GIS requirement demonstrably satisfied.

## Phase 9 --- Advanced Capability

Only if justified:

-   satellite-image model;
-   advanced representation;
-   additional monitoring capabilities.

------------------------------------------------------------------------

# 29. Dependency Graph

``` text
PHASE 0
Scientific contract
├── ontology
├── event semantics
├── source semantics
├── GT policy
├── benchmark protocol
└── geospatial metric
        │
        ▼
PHASE 1
Data feasibility
├── geography
├── FIRMS volume
├── labels
├── OSM coverage
└── satellite availability
        │
        ├───────────────┐
        ▼               ▼
PHASE 2              GT Registry
FIRMS Data Spine        │
        │               │
        ▼               │
PHASE 3                 │
Events + Sources        │
        │               │
        └───────┬───────┘
                ▼
PHASE 4
Context + Features
                │
                ▼
PHASE 5
Deterministic Baselines
                │
                ├───────────────┐
                ▼               ▼
          Benchmark        Error Analysis
                │               │
                └───────┬───────┘
                        ▼
PHASE 6
ML + Calibration + Abstention
                        │
                        ▼
PHASE 7
Evidence + Uncertainty
                        │
                        ▼
PHASE 8
REST API + GIS
                        │
                        ▼
PHASE 9
Advanced Model (conditional)
```

------------------------------------------------------------------------

# 30. Detailed Implementation Units

Each unit is intentionally small enough for an AI coding agent to
execute independently.

## Scientific / Data Contract Units

### DATA-001 --- Select Demonstration Geography

-   **Build:** documented candidate-geography evaluation and final
    selection.
-   **Why:** all downstream feasibility depends on geography.
-   **Dependencies:** none.
-   **Inputs:** candidate Indian regions, FIRMS/context/reference
    availability.
-   **Outputs:** selected geography + rationale.
-   **DB:** configuration/metadata only.
-   **API:** none.
-   **Tests:** validation of required selection criteria.
-   **Acceptance:** written evidence-based rationale exists.
-   **Priority:** P0.
-   **Status:** OPEN QUESTION.

### DATA-002 --- Ground-Truth Registry Schema

-   **Build:** reference-event schema and persistence model.
-   **Dependencies:** DATA-001.
-   **Acceptance:** all minimum provenance fields supported; invalid
    provenance rejected.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### DATA-003 --- Ground-Truth Label Policy

-   **Build:** Tier A/B/C labeling policy and annotation workflow.
-   **Dependencies:** DATA-002.
-   **Acceptance:** Tier C cannot be silently promoted to hard ground
    truth.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### DATA-004 --- Data Feasibility Report

-   **Build:** reproducible analysis of event volume, labels, class
    balance, geography, OSM and satellite availability.
-   **Dependencies:** DATA-001, DATA-002.
-   **Acceptance:** report supports taxonomy/ML go-no-go decision.
-   **Priority:** P0.
-   **Status:** OPEN QUESTION / REQUIRED EXPERIMENT.

### DATA-005 --- Benchmark Dataset Versioning

-   **Build:** immutable dataset manifest and version identifier.
-   **Dependencies:** DATA-003, DATA-004.
-   **Acceptance:** benchmark inputs can be reproduced exactly.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

------------------------------------------------------------------------

## Backend Units

### BE-001 --- Repository Skeleton

-   **Build:** project directories and package boundaries.
-   **Dependencies:** Phase 0.
-   **Acceptance:** API/worker/ML/schemas/geospatial/evidence boundaries
    exist.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### BE-002 --- Configuration System

-   **Build:** typed environment/configuration management.
-   **Dependencies:** BE-001.
-   **Acceptance:** secrets are not hard-coded; invalid config fails
    clearly.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### BE-003 --- Domain Schema Package

-   **Build:** Pydantic models for
    Detection/Event/Source/Context/Intelligence.
-   **Dependencies:** BE-001.
-   **Acceptance:** vendor-specific fields do not leak through domain
    boundaries.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### BE-004 --- Repository/Data Access Layer

-   **Build:** typed database access boundaries.
-   **Dependencies:** database schema.
-   **Acceptance:** domain services do not directly issue uncontrolled
    production SQL.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

------------------------------------------------------------------------

## Database Units

### DB-001 --- PostGIS Setup

-   **Build:** PostgreSQL/PostGIS migration baseline.
-   **Dependencies:** BE-001.
-   **Acceptance:** clean environment creates database successfully.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### DB-002 --- Provenance Tables

-   **Build:** `source_records` and related provenance structures.
-   **Dependencies:** DB-001.
-   **Acceptance:** source/version/hash/acquisition/ingestion metadata
    persists.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### DB-003 --- Detection Schema

-   **Build:** `firms_detections` + indexes.
-   **Dependencies:** DB-002.
-   **Acceptance:** canonical detection data persists with geometry and
    provenance.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### DB-004 --- Event Schema

-   **Build:** events + membership relation.
-   **Dependencies:** DB-003.
-   **Acceptance:** event membership is traceable.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### DB-005 --- Persistent Source Schema

-   **Build:** source + source-event relations.
-   **Dependencies:** DB-004.
-   **Acceptance:** event/source distinction is enforced.
-   **Priority:** P1.
-   **Status:** RECOMMENDATION.

### DB-006 --- Context Schema

-   **Build:** industrial/context, land cover and satellite metadata
    tables.
-   **Dependencies:** DB-001.
-   **Acceptance:** provenance and missingness supported.
-   **Priority:** P0/P1 depending on source.
-   **Status:** RECOMMENDATION / PROVISIONAL.

### DB-007 --- ML/Evidence Schema

-   **Build:** feature, prediction, evidence and evaluation tables.
-   **Dependencies:** DB-005, DB-006.
-   **Acceptance:** model/feature/dataset versions are linked.
-   **Priority:** P1.
-   **Status:** RECOMMENDATION.

------------------------------------------------------------------------

## FIRMS/Data Ingestion Units

### DATA-010 --- FIRMS Client

-   **Build:** authenticated server-side FIRMS client.
-   **Dependencies:** BE-002, BE-003.
-   **Acceptance:** successful retrieval and structured failure
    handling.
-   **Priority:** P0.
-   **Status:** VERIFIED source integration / RECOMMENDATION
    implementation.

### DATA-011 --- Raw FIRMS Capture

-   **Build:** immutable raw response storage.
-   **Dependencies:** DATA-010, DB-002.
-   **Acceptance:** raw source can be replayed.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### DATA-012 --- FIRMS Parser

-   **Build:** source-specific parser to canonical schema.
-   **Dependencies:** DATA-010, BE-003.
-   **Acceptance:** fixture data parses correctly; malformed records are
    surfaced.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### DATA-013 --- FIRMS Deduplication

-   **Build:** deterministic duplicate detection using source
    identity/hash and defined canonical identity.
-   **Dependencies:** DATA-012, DB-003.
-   **Acceptance:** repeated ingestion does not create uncontrolled
    duplicates.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION; exact identity rule is implementation
    detail.

### DATA-014 --- Historical Replay

-   **Build:** repeatable historical ingestion command/job.
-   **Dependencies:** DATA-011--013.
-   **Acceptance:** same historical input can regenerate canonical data.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

------------------------------------------------------------------------

## Geospatial Units

### GEO-001 --- CRS Utilities

-   **Build:** centralized CRS transformations and validation.
-   **Dependencies:** BE-003.
-   **Acceptance:** no naïve lat/lon Euclidean distance in production
    geospatial logic.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### GEO-002 --- Spatial Distance Service

-   **Build:** PostGIS/geodesic distance calculations.
-   **Dependencies:** GEO-001, DB-001.
-   **Acceptance:** known-distance fixtures pass within documented
    numerical tolerance.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### GEO-003 --- Geometry Validation

-   **Build:** geometry validity/normalization utilities.
-   **Dependencies:** GEO-001.
-   **Acceptance:** invalid geometries are detected and handled
    explicitly.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### GEO-004 --- Geospatial Error Metric

-   **Build:** benchmark metric only after valid reference geometry is
    defined.
-   **Dependencies:** DATA-001--005.
-   **Acceptance:** metric definition documents what geometry is
    compared and why.
-   **Priority:** P0.
-   **Status:** OPEN QUESTION.

------------------------------------------------------------------------

## Event/Source Units

### GEO-010 --- Event Feature Aggregation

-   **Build:** event geometry/time/FRP aggregation from detections.
-   **Dependencies:** DATA-014, GEO-001--003, DB-004.
-   **Acceptance:** event statistics are reproducible.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### GEO-011 --- Event Clustering Engine

-   **Build:** configurable spatio-temporal clustering.
-   **Dependencies:** GEO-010.
-   **Acceptance:** synthetic fixtures produce expected membership;
    configuration is versioned.
-   **Priority:** P0.
-   **Status:** OPEN QUESTION for exact parameters.

### GEO-012 --- Source Association

-   **Build:** event-to-persistent-source association.
-   **Dependencies:** GEO-011, DB-005.
-   **Acceptance:** repeated events can form source histories without
    conflating events.
-   **Priority:** P1.
-   **Status:** RECOMMENDATION.

### GEO-013 --- Persistence Statistics

-   **Build:** active days, recurrence, gaps, footprint stability,
    drift, FRP statistics.
-   **Dependencies:** GEO-012.
-   **Acceptance:** all statistics trace to source events.
-   **Priority:** P1.
-   **Status:** RECOMMENDATION.

### GEO-014 --- Persistence State Policy

-   **Build:** `transient/recurring/persistent/insufficient_history`.
-   **Dependencies:** GEO-013, OQ-004.
-   **Acceptance:** thresholds are documented and versioned before
    benchmark use.
-   **Priority:** P1.
-   **Status:** OPEN QUESTION.

------------------------------------------------------------------------

## Context Units

### CTX-001 --- OSM Client

-   **Build:** OSM/Overpass retrieval boundary.
-   **Dependencies:** BE-002, GEO-001.
-   **Acceptance:** timeout/rate-limit/failure handling works.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### CTX-002 --- Industrial Feature Normalizer

-   **Build:** normalize OSM feature types/tags into internal context
    schema.
-   **Dependencies:** CTX-001, BE-003.
-   **Acceptance:** source tags remain traceable.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### CTX-003 --- Industrial Proximity Features

-   **Build:** distance/count/type features.
-   **Dependencies:** CTX-002, GEO-002.
-   **Acceptance:** no proximity feature is interpreted as ground truth.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION; exact threshold remains OPEN.

### CTX-004 --- Land-Cover Adapter

-   **Build:** selected land-cover product adapter.
-   **Dependencies:** DATA-004, GEO-001.
-   **Acceptance:** product/version/class/retrieval metadata retained.
-   **Priority:** P0.
-   **Status:** PROVISIONAL until product selected.

### CTX-005 --- Satellite Catalog Adapter

-   **Build:** satellite metadata/catalog lookup.
-   **Dependencies:** DATA-004, GEO-001.
-   **Acceptance:** unavailable imagery is explicit.
-   **Priority:** P1.
-   **Status:** PROVISIONAL.

### CTX-006 --- Context Missingness Contract

-   **Build:** explicit unavailable/unknown states across context
    sources.
-   **Dependencies:** CTX-001--005.
-   **Acceptance:** no unavailable source becomes silently
    false/negative.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

------------------------------------------------------------------------

## Feature Units

### FEAT-001 --- FIRMS Feature Builder

-   **Dependencies:** DB-003, BE-003.
-   **Acceptance:** versioned deterministic feature output.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### FEAT-002 --- Temporal Feature Builder

-   **Dependencies:** GEO-013.
-   **Acceptance:** active days, gaps, duration and recurrence are
    reproducible.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### FEAT-003 --- Spatial Feature Builder

-   **Dependencies:** GEO-010.
-   **Acceptance:** footprint/centroid/drift features are reproducible.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### FEAT-004 --- Context Feature Builder

-   **Dependencies:** CTX-003--006.
-   **Acceptance:** missing context is explicit and versioned.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### FEAT-005 --- Satellite Feature Builder

-   **Dependencies:** CTX-005.
-   **Acceptance:** only valid/available satellite features are
    generated.
-   **Priority:** P1.
-   **Status:** PROVISIONAL.

### FEAT-006 --- Feature Manifest

-   **Build:** feature names, versions, dependencies and generation
    metadata.
-   **Dependencies:** FEAT-001--005.
-   **Acceptance:** prediction can identify exact feature version.
-   **Priority:** P1.
-   **Status:** RECOMMENDATION.

------------------------------------------------------------------------

## Baseline/Evaluation Units

### EVAL-001 --- Benchmark Split Generator

-   **Build:** geographic/temporal/source-aware split generation.
-   **Dependencies:** DATA-005.
-   **Acceptance:** event/source members cannot leak across splits.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### EVAL-002 --- FIRMS-Only Baseline

-   **Dependencies:** FEAT-001, EVAL-001.
-   **Acceptance:** baseline metrics recorded on frozen benchmark.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### EVAL-003 --- Context Baseline

-   **Dependencies:** FEAT-004, EVAL-001.
-   **Acceptance:** industrial/context-only contribution measured.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### EVAL-004 --- Persistence Baseline

-   **Dependencies:** FEAT-002, EVAL-001.
-   **Acceptance:** persistence contribution measured.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### EVAL-005 --- Combined Deterministic Baseline

-   **Dependencies:** EVAL-002--004.
-   **Acceptance:** combined baseline benchmark exists.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### EVAL-006 --- Ablation Runner

-   **Dependencies:** EVAL-001--005, satellite features if available.
-   **Acceptance:** A--F evidence configurations are benchmarkable.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### EVAL-007 --- Leakage Audit

-   **Dependencies:** EVAL-001.
-   **Acceptance:** automated checks fail on event/source leakage.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

------------------------------------------------------------------------

## ML Units

### ML-001 --- Training Dataset Builder

-   **Dependencies:** DATA-005, FEAT-006.
-   **Acceptance:** only approved label tiers enter hard-ground-truth
    benchmark.
-   **Priority:** P1.
-   **Status:** PROVISIONAL.

### ML-002 --- Simple Feature Model

-   **Dependencies:** ML-001, EVAL-001.
-   **Acceptance:** benchmarked against deterministic baseline.
-   **Priority:** P1.
-   **Status:** RECOMMENDATION.

### ML-003 --- XGBoost/LightGBM Model

-   **Dependencies:** ML-002.
-   **Acceptance:** improvement is measured, not assumed.
-   **Priority:** P1.
-   **Status:** PROVISIONAL.

### ML-004 --- Model Versioning

-   **Dependencies:** ML-003.
-   **Acceptance:** model, dataset and feature versions are stored with
    predictions.
-   **Priority:** P1.
-   **Status:** RECOMMENDATION.

### ML-005 --- Model Error Analysis

-   **Dependencies:** ML-003.
-   **Acceptance:** false positives/negatives categorized by
    evidence/context.
-   **Priority:** P1.
-   **Status:** RECOMMENDATION.

------------------------------------------------------------------------

## Calibration/Abstention Units

### ML-010 --- Probability Calibration

-   **Dependencies:** ML-003, ML-004.
-   **Acceptance:** calibration is evaluated on appropriate held-out
    data.
-   **Priority:** P1.
-   **Status:** RECOMMENDATION.

### ML-011 --- Abstention Policy

-   **Dependencies:** ML-010, ML-005.
-   **Acceptance:** risk/coverage curve available; low-evidence cases
    can abstain.
-   **Priority:** P1.
-   **Status:** OPEN QUESTION for operating threshold.

------------------------------------------------------------------------

## Evidence Units

### EVID-001 --- Evidence Schema

-   **Dependencies:** BE-003.
-   **Acceptance:** evidence includes type, value, provenance and
    generation version.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### EVID-002 --- Deterministic Evidence Rules

-   **Dependencies:** FEAT-001--006, EVID-001.
-   **Acceptance:** every factual evidence statement maps to validated
    data.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### EVID-003 --- Limitation Generator

-   **Dependencies:** CTX-006, ML-011.
-   **Acceptance:** missing imagery/history/context can be exposed as
    limitations.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### EVID-004 --- Evidence Audit

-   **Dependencies:** EVID-002--003.
-   **Acceptance:** automated tests reject unsupported evidence.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

------------------------------------------------------------------------

## API Units

### API-001 --- FastAPI Bootstrap

-   **Dependencies:** BE-001--003, DB-001.
-   **Acceptance:** health endpoint and OpenAPI generation work.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### API-002 --- Detection Endpoints

-   **Dependencies:** DATA-013, API-001.
-   **Acceptance:** typed paginated/filterable detection retrieval.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### API-003 --- Event Endpoints

-   **Dependencies:** GEO-011, API-001.
-   **Acceptance:** event details include geometry/time/statistics.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### API-004 --- Source Endpoints

-   **Dependencies:** GEO-012--014.
-   **Acceptance:** source timeline and linked events available.
-   **Priority:** P1.
-   **Status:** RECOMMENDATION.

### API-005 --- Evidence Endpoints

-   **Dependencies:** EVID-002--003.
-   **Acceptance:** evidence and limitations are retrievable.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### API-006 --- Job Endpoints

-   **Dependencies:** worker implementation.
-   **Acceptance:** job creation/status is observable.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### API-007 --- GIS Layer Endpoints

-   **Dependencies:** API-003--005, GIS schema.
-   **Acceptance:** map-ready GeoJSON/layer responses work.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

------------------------------------------------------------------------

## Worker Units

### WORK-001 --- Redis Job Infrastructure

-   **Dependencies:** BE-002, DB-001.
-   **Acceptance:** job can be queued/executed/retried with status.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### WORK-002 --- FIRMS Ingestion Job

-   **Dependencies:** DATA-010--014, WORK-001.
-   **Acceptance:** end-to-end historical ingestion works
    asynchronously.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### WORK-003 --- Event Formation Job

-   **Dependencies:** GEO-011, WORK-001.
-   **Acceptance:** job is idempotent/versioned.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### WORK-004 --- Enrichment Jobs

-   **Dependencies:** CTX-001--006, WORK-001.
-   **Acceptance:** failures are visible and partial results preserved.
-   **Priority:** P0/P1.
-   **Status:** RECOMMENDATION.

### WORK-005 --- Classification Job

-   **Dependencies:** ML pipeline, WORK-001.
-   **Acceptance:** predictions persist with model/feature/dataset
    versions.
-   **Priority:** P1.
-   **Status:** PROVISIONAL.

### WORK-006 --- Evidence Job

-   **Dependencies:** EVID-002--003.
-   **Acceptance:** evidence is deterministic and reproducible.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

------------------------------------------------------------------------

## GIS Units

### GIS-001 --- GeoJSON Serialization

-   **Dependencies:** API, PostGIS.
-   **Acceptance:** geometries serialize correctly without precision/CRS
    confusion.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### GIS-002 --- Event Map Layer

-   **Dependencies:** GIS-001, API-007.
-   **Acceptance:** event overlay renders and links to event details.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### GIS-003 --- Persistent Source Layer

-   **Dependencies:** GIS-001, API-007, GEO-012.
-   **Acceptance:** source overlay renders and links to timelines.
-   **Priority:** P1.
-   **Status:** RECOMMENDATION.

### GIS-004 --- Industrial/Land-Cover Layers

-   **Dependencies:** CTX modules, API-007.
-   **Acceptance:** contextual layers can be toggled and interpreted
    separately from predictions.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### GIS-005 --- Analyst Detail View

-   **Dependencies:** API-003--005.
-   **Acceptance:** event/source detail exposes classification,
    evidence, uncertainty and provenance.
-   **Priority:** P1.
-   **Status:** RECOMMENDATION.

------------------------------------------------------------------------

## Security/Operations Units

### OPS-001 --- Secret Handling

-   **Dependencies:** BE-002.
-   **Acceptance:** no credentials committed/exposed.
-   **Priority:** P0.
-   **Status:** RECOMMENDATION.

### OPS-002 --- Structured Logging

-   **Dependencies:** BE-001.
-   **Acceptance:** jobs/API/external failures are searchable without
    sensitive values.
-   **Priority:** P1.
-   **Status:** RECOMMENDATION.

### OPS-003 --- Health/Readiness Checks

-   **Dependencies:** API/DB/Redis.
-   **Acceptance:** dependency failures are distinguishable.
-   **Priority:** P1.
-   **Status:** RECOMMENDATION.

### OPS-004 --- Performance Benchmark Harness

-   **Dependencies:** pipeline stages.
-   **Acceptance:** ingestion/enrichment/classification/end-to-end
    timing is measured separately.
-   **Priority:** P1.
-   **Status:** RECOMMENDATION.

------------------------------------------------------------------------

# 31. AI Coding Agent Execution Protocol

AI coding agents must execute implementation units, not invent
architecture.

## 31.1 Required Input to Agent

Every coding task must specify:

``` text
Unit ID
Objective
Dependencies
Files/modules allowed to change
Inputs
Outputs
Acceptance criteria
Tests required
Architecture invariants
Known assumptions/open questions
```

## 31.2 Agent Workflow

``` text
1. Read relevant specification
2. Inspect existing implementation
3. Identify exact unit boundary
4. Implement smallest change
5. Add/update tests
6. Run targeted tests
7. Run relevant integration checks
8. Check architecture invariants
9. Report files changed
10. Report assumptions
11. Report unresolved failures
```

## 31.3 Agent Prohibitions

The agent must not:

-   introduce Kafka;
-   create unnecessary microservices;
-   alter scientific thresholds without approval;
-   invent labels;
-   change benchmark splits to improve results;
-   use LLM-generated evidence as factual evidence;
-   silently change ontology;
-   overwrite raw source observations;
-   replace event/source geometry with facility geometry;
-   bypass schema validation;
-   hide external API failures;
-   modify unrelated modules to make a local test pass.

## 31.4 Change Discipline

Prefer:

``` text
one implementation unit
→ one focused change
→ tests
→ review
→ next unit
```

Avoid large speculative rewrites.

## 31.5 Agent Completion Report

Every completed unit should report:

``` text
Implemented:
Tests:
Files changed:
Assumptions:
Open questions:
Performance impact:
Architecture invariants checked:
Acceptance criteria:
```

------------------------------------------------------------------------

# 32. Risk Register

  -------------------------------------------------------------------------------------------
  ID         Risk                      Severity     Likelihood Mitigation         Status
  ---------- ------------------- -------------- -------------- ------------------ -----------
  R-001      Insufficient              Critical           High Feasibility gate;  OPEN
             high-quality ground                               reduce taxonomy    
             truth                                                                

  R-002      OSM incompleteness            High         Medium Explicit           OPEN
                                                               missingness;       
                                                               ablation           

  R-003      FIRMS spatial             Critical        Certain Separate           PROTECTED
             ambiguity                                         geometries; honest 
                                                               attribution        

  R-004      Industrial                    High           High Context            PROTECTED
             proximity shortcut                                ablation/removal   
                                                               test               

  R-005      Spatial leakage           Critical         Medium Grouped spatial    PROTECTED
                                                               benchmark          

  R-006      Temporal leakage          Critical         Medium Time-aware split   PROTECTED

  R-007      Persistent-source         Critical         Medium Source-grouped     PROTECTED
             leakage                                           split              

  R-008      Class imbalance               High         Likely Metrics, weighting OPEN
                                                               where justified,   
                                                               abstention         

  R-009      Satellite imagery           Medium           High Tiered evidence    PROTECTED
             unavailable                                       and explicit       
                                                               unavailable state  

  R-010      External API                  High         Medium Cache, retry,      PROTECTED
             outage/rate limits                                replay, failure    
                                                               state              

  R-011      Overly ambitious              High           High Ground-truth       OPEN
             taxonomy                                          feasibility gate   

  R-012      Deep-learning                 High         Medium Baseline-first     PROTECTED
             complexity without                                gate               
             value                                                                

  R-013      LLM hallucinated          Critical         Medium Deterministic      PROTECTED
             evidence                                          evidence engine    

  R-014      Performance target            High         Medium Benchmark before   PROTECTED
             overclaim                                         claims             

  R-015      Premature                   Medium         Medium Redis + Compose    PROTECTED
             infrastructure                                    MVP                
             complexity                                                           

  R-016      UI consumes                   High           High UI-led development PROTECTED
             development time                                  prohibited         
             before intelligence                                                  
             works                                                                

  R-017      Geospatial metric         Critical         Medium Define reference   OPEN
             becomes                                           geometry first     
             scientifically                                                       
             meaningless                                                          

  R-018      Weak labels               Critical         Medium Tiered registry +  PROTECTED
             silently become                                   validation         
             ground truth                                                         
  -------------------------------------------------------------------------------------------

------------------------------------------------------------------------

# 33. Definition of Done

A unit is complete only when:

1.  implementation works within its defined scope;
2.  tests exist and pass;
3.  external failures are handled;
4.  provenance is preserved;
5.  uncertainty is preserved;
6.  documentation is updated;
7.  progress tracker is updated where relevant;
8.  build/type/lint checks pass;
9.  no architecture invariant is violated;
10. no open question has silently become a fact;
11. acceptance criteria are explicitly demonstrated.

## 33.1 System-Level Definition of Done

The MVP is complete only when:

-   FIRMS historical data can be ingested reproducibly;
-   detections are immutable and traceable;
-   events are reproducibly formed;
-   persistent/recurring sources can be represented;
-   industrial/context and land-cover evidence can be attached;
-   satellite availability is explicit;
-   deterministic baselines are benchmarked;
-   valid ground truth is versioned;
-   final evaluation prevents leakage;
-   ML, if included, beats a meaningful baseline;
-   probabilities are evaluated/calibrated if exposed;
-   abstention is supported;
-   evidence is deterministic and auditable;
-   intelligence results contain uncertainty/provenance;
-   REST APIs expose the required information;
-   GIS storage and map overlays work;
-   failure states are visible;
-   no unsupported performance claim is made.

------------------------------------------------------------------------

# 34. Immediate Next Steps

Execute in this order.

## Step 1 --- DATA-001

Select the demonstration geography.

**Do not start ML.**

## Step 2 --- DATA-002 / DATA-003

Freeze the ground-truth registry and label provenance policy.

## Step 3 --- DATA-004

Perform the data-feasibility experiment:

``` text
FIRMS volume
+
candidate events
+
Tier A/B label availability
+
class distribution
+
OSM completeness
+
satellite availability
```

## Step 4 --- Resolve Scientific Contract

Resolve:

-   ontology scope;
-   event semantics;
-   persistence definition;
-   attribution definition;
-   geospatial metric;
-   benchmark time window.

## Step 5 --- DB-001 → DB-003

Create the PostGIS foundation and FIRMS canonical data spine.

## Step 6 --- DATA-010 → DATA-014

Implement reproducible FIRMS ingestion.

## Step 7 --- GEO-001 → GEO-011

Implement geometry utilities and event formation.

## Step 8 --- GEO-012 → GEO-014

Implement source association and persistence only after event semantics
are validated.

## Step 9 --- CTX-001 → CTX-006

Add context enrichment and explicit missingness.

## Step 10 --- FEAT-001 → FEAT-006

Build the versioned feature layer.

## Step 11 --- EVAL-001 → EVAL-007

Freeze benchmark and establish deterministic baselines.

## Step 12 --- Make the ML Go/No-Go Decision

Only proceed to ML if:

-   sufficient labels exist;
-   taxonomy is supportable;
-   benchmark is valid;
-   baseline errors justify ML.

## Step 13 --- ML-001 → ML-005

Build and evaluate the tabular model.

## Step 14 --- ML-010 → ML-011

Calibrate and implement abstention.

## Step 15 --- EVID-001 → EVID-004

Make every result explainable from verified data.

## Step 16 --- API + Worker + GIS

Implement:

``` text
API-001 → API-007
WORK-001 → WORK-006
GIS-001 → GIS-005
```

## Step 17 --- Hostile Review Gate

Before demo freeze, attempt to disprove:

1.  the labels;
2.  the spatial attribution;
3.  the event clustering;
4.  the persistence definition;
5.  the industrial-context shortcut;
6.  the benchmark split;
7.  the confidence calibration;
8.  the evidence statements;
9.  the latency claim;
10. the GIS interpretation.

Fix the weakest defensible claim first.

------------------------------------------------------------------------

# Hostile Architectural & Scientific Self-Review

This section is mandatory before treating the plan as the implementation
source of truth.

## Attack 1 --- "Is FIRMS being treated as ground truth?"

**Finding:** The architecture could accidentally allow downstream
derived labels to inherit FIRMS semantics.

**Correction:** raw FIRMS observations, reference-event labels, and
model predictions must remain separate database/domain concepts. No
ingestion pipeline may create a ground-truth label.

## Attack 2 --- "Is industrial proximity secretly the classifier?"

**Finding:** Industrial proximity is an extremely strong shortcut
candidate.

**Correction:** context ablation is mandatory. Performance must be
reported with and without industrial-context features. The system must
represent context as evidence, not confirmation.

## Attack 3 --- "Are persistence thresholds invented?"

**Finding:** The project documents define persistence states but do not
establish scientific numerical thresholds.

**Correction:** exact thresholds remain OPEN. They must be
experimentally justified, documented, versioned, and frozen before
benchmark use.

## Attack 4 --- "Is geospatial accuracy meaningful?"

**Finding:** A detection centroid cannot automatically be compared
against a facility point as though both were exact incident locations.

**Correction:** define the reference geometry and error semantics before
reporting attribution error. Until then, do not claim a meter-level
accuracy metric.

## Attack 5 --- "Can the benchmark leak?"

**Finding:** Multiple detections from one event/source can make random
splitting deceptively strong.

**Correction:** final evaluation must group event/source identities and
include geographic/temporal separation where feasible.

## Attack 6 --- "Does missing satellite imagery bias the system?"

**Finding:** A model could learn that imagery availability itself
predicts class.

**Correction:** satellite availability is represented explicitly, and
the ablation matrix must distinguish satellite-derived evidence from
availability artifacts.

## Attack 7 --- "Can the system classify everything?"

**Finding:** The real world contains unknown thermal phenomena and
incomplete evidence.

**Correction:** `unknown/uncertain` and `insufficient_history` remain
valid outcomes. Coverage is evaluated jointly with reliability.

## Attack 8 --- "Can an LLM manufacture convincing explanations?"

**Finding:** Natural-language explanations can appear credible even when
unsupported.

**Correction:** factual evidence is generated deterministically from
stored data. Any future LLM only summarizes validated evidence.

## Attack 9 --- "Are performance targets being mistaken for results?"

**Finding:** Engineering targets could be repeated as claims.

**Correction:** all latency/accuracy/precision/recall targets are
explicitly labeled as targets. No result is claimed until measured on a
frozen benchmark.

## Attack 10 --- "Is architecture complexity distracting from the actual problem?"

**Finding:** Kafka, microservices, advanced vision and UI polish could
consume time without improving scientific validity.

**Correction:** Redis-backed jobs, modular services, tabular ML and
deferred UI remain the MVP path. Advanced infrastructure/modeling
requires measured justification.

## Attack 11 --- "Could weak labels contaminate the benchmark?"

**Finding:** Proxy labels are tempting when authoritative incidents are
sparse.

**Correction:** Tier C may support exploration/weak supervision but
cannot be treated as equivalent to Tier A/B ground truth.

## Attack 12 --- "Does the architecture overclaim facility-level localization?"

**Finding:** A nearby facility can be spatially related without being
the source.

**Correction:** detection, event, source and facility geometries remain
separate, with distance and attribution confidence stored explicitly.

## Attack 13 --- "Can external failures silently become model behavior?"

**Finding:** Missing OSM/satellite/FIRMS data can otherwise look like
negative evidence.

**Correction:** all important external-data states use explicit
availability/error metadata.

## Attack 14 --- "Can the implementation change the scientific contract accidentally?"

**Finding:** AI coding agents may optimize locally and introduce hidden
assumptions.

**Correction:** every implementation unit carries status, dependencies
and acceptance criteria; agents are prohibited from silently changing
ontology, labels, thresholds, benchmark splits or protected boundaries.

------------------------------------------------------------------------

# Final Source-of-Truth Rules

When this document conflicts with an implementation convenience, this
document wins.

When an authoritative SIH/source fact conflicts with a project
recommendation, the authoritative fact wins.

When an experiment contradicts an assumption, the measured result wins.

When an open question is unresolved, the implementation must either:

1.  wait for resolution; or
2.  isolate the decision behind a clearly marked provisional
    configuration.

The project must continuously optimize for:

``` text
scientific defensibility
+
traceability
+
evidence
+
honest uncertainty
+
measured performance
+
SIH requirement alignment
+
execution speed
```

The winning implementation is not the largest system.

It is the smallest technically sophisticated system that makes a
hard-to-fake claim, proves it with evidence, and maps directly to
SIH26162.
