# SIH26162 --- IMPLEMENTATION EXECUTION PLAN

**Status:** Final implementation execution blueprint\
**Project:** SIH26162 --- AI-Based Detection and Classification of
Industrial Fires and Persistent Thermal Sources Using NASA FIRMS, OSM &
Satellite Data\
**Implementation state at plan creation:** Not started\
**Primary purpose:** Convert the approved architecture and scientific
constraints into atomic, safe, AI-agent-executable implementation work.

> **Source authority:** Tier 1 project documents are authoritative. The
> verified data-source stack is a resource reference; its usage
> recommendations are provisional unless validated. The hostile
> implementation review is mandatory corrective input. The V2 plan is
> the immediate architectural source of truth. The execution plan below
> operationalizes those decisions without silently resolving open
> scientific questions.

------------------------------------------------------------------------

# 0. Final Implementation Readiness Review

## 0.1 Readiness decision

**Overall status: IMPLEMENTATION-READY EXCEPT FOR SCIENTIFIC DECISIONS
THAT MUST REMAIN ISOLATED BEHIND CONFIGURATION/REFERENCE-DATA
BOUNDARIES.**

Coding can begin immediately for infrastructure, contracts, provenance,
source adapters, database foundations, offline replay, API foundations,
and deterministic pipeline scaffolding.

Coding must **not** invent or freeze unresolved values for: - final
demonstration geography; - final event clustering thresholds; - final
persistence definition/thresholds; - final contextual proximity rule; -
final supported taxonomy; - final attribution semantics; - final
benchmark time window; - final reference geometry/error metric; - final
benchmark labels; - final calibration parameters; - final abstention
threshold; - final ML model/hyperparameters; - final acceptance
thresholds.

The project documents explicitly identify these as unresolved and
require the implementation to reduce uncertainty before model
development. The progress tracker states that implementation has not yet
started and that geography, ground truth, taxonomy, persistence, and
evaluation remain open. `architecture.md` also prohibits random
point-level splits and requires spatial/temporal/source-grouped
evaluation.

## 0.2 Decision status matrix

  -----------------------------------------------------------------------------------------------------------------------------------------------------
  Decision                                     Current Status   Evidence                Dependency             Can Coding       Required Action
                                                                                                               Start?           
  -------------------------------------------- ---------------- ----------------------- ---------------------- ---------------- -----------------------
  SIH deliverables: industrial-fire            LOCKED / FACT    Official project        None                   YES              Preserve as P0
  segregation + GIS storage/visualization                       definition                                                      

  FIRMS as primary thermal observation source  LOCKED /         Project architecture +  None                   YES              Implement adapter and
                                               VERIFIED         NASA source                                                     provenance
                                                                documentation                                                   

  FIRMS as ground truth                        LOCKED / FACT:   Project invariants      None                   YES              Enforce semantic
                                               NO                                                                               boundary

  PostgreSQL + PostGIS as system of record     LOCKED /         Architecture            None                   YES              Build database
                                               RECOMMENDATION                                                                   foundation

  Redis for MVP job coordination instead of    LOCKED /         Architecture + hostile  DB/API foundation      YES, but not     Add only after
  Kafka                                        RECOMMENDATION   review                                         required for     synchronous service
                                                                                                               first sync slice path

  No microservices                             LOCKED /         Architecture            None                   YES              Keep modular monolith +
                                               RECOMMENDATION                                                                   worker

  Detection → Event → Persistent Source        LOCKED /         Architecture/progress   Scientific event       YES as domain    Keep physical
                                               RECOMMENDATION   tracker                 contract               abstraction      interpretation separate

  Phenomenon/context/persistence/attribution   LOCKED /         Architecture/code       Ontology               YES              Prevent collapsed class
  orthogonal                                   RECOMMENDATION   standards                                                       semantics

  OSM as contextual evidence                   LOCKED /         Code standards/hostile  Context schema         YES              Bulk/local ingestion
                                               VERIFIED         review                                                          preferred

  OSM as ground truth                          LOCKED / FACT:   Code standards          None                   YES              Enforce
                                               NO                                                                               provenance/semantic
                                                                                                                                role

  Facility proximity = attribution             LOCKED / FACT:   Architecture/code       Attribution definition YES              Store relationship
                                               NO               standards                                                       separately

  Satellite evidence optional                  LOCKED /         Architecture + review   Satellite adapter      YES              Explicit availability
                                               RECOMMENDATION                                                                   state

  Advanced CV before tabular baseline          LOCKED / FACT:   Architecture/progress   Benchmark              NO               Gate behind measured
                                               NO               tracker                                                         improvement

  Baseline before ML                           LOCKED           Progress                Reference dataset      YES for baseline 
                                                                tracker/architecture                           framework;       
                                                                                                               actual benchmark 
                                                                                                               waits for labels 

  Calibration                                  CONDITIONAL /    Architecture            Valid predictions +    Scaffold YES;    Choose after validation
                                               PROVISIONAL                              calibration split      final method NO  protocol
                                               method                                                                           

  Abstention                                   LOCKED concept / Architecture            Calibration/evidence   Scaffold YES;    Make threshold/config
                                               OPEN threshold                                                  threshold NO     required

  Evidence deterministic                       LOCKED           Architecture/code       Feature/source state   YES              Implement independent
                                                                standards                                                       evidence derivation

  LLM factual evidence generation              LOCKED / FACT:   Architecture/code       None                   YES              Never implement
                                               NO               standards                                                       

  Source semantic preservation                 LOCKED           V2 hardening            All adapters           YES              Add source-role
                                                                                                                                registry

  Versioned scientific configuration           LOCKED           V2 hardening            DB foundation          YES              Missing required values
                                                                                                                                must fail

  Pipeline-run lineage                         LOCKED /         Hostile review/V2       DB foundation          YES              Add run identity and
                                               RECOMMENDATION                                                                   artifact lineage

  Dataset version + membership                 LOCKED           Evaluation rules/V2     Reference pipeline     YES              Build before benchmark

  Feature registry/versioning                  LOCKED           V2 hardening            Dataset/feature layer  YES              Add definitions and
                                                                                                                                provenance

  Offline replay                               LOCKED           Architecture/review     Raw fixtures           YES              Build before live-demo
                                                                                                                                dependence

  Final geography                              OPEN QUESTION    Progress tracker        Data feasibility       NO for           Run DATA-001
                                                                                                               benchmark; YES   
                                                                                                               for generic      
                                                                                                               infrastructure   

  Event clustering values                      OPEN QUESTION    Progress tracker/review FIRMS profiling        NO               Config only until
                                                                                                                                experiment

  Persistence definition                       OPEN QUESTION    Progress tracker        Event history          NO               Experiment and freeze

  Attribution definition                       OPEN QUESTION    Progress tracker/review Reference              NO               Keep contextual
                                                                                        geometry/context                        relation only

  Ground-truth labels                          OPEN QUESTION    Progress tracker        Reference evidence     NO               Build
                                                                                                                                registry/adjudication

  Final taxonomy                               OPEN QUESTION    Progress tracker        Ground truth           NO               Support only validated
                                                                                                                                classes

  Benchmark split                              OPEN QUESTION    Progress tracker        Geography/reference    NO               Freeze before ML
                                                                                        data                                    comparison

  Final model                                  CONDITIONAL      Architecture            Baselines + labels     NO               Benchmark-driven

  Final performance targets                    CONDITIONAL      Team targets            Frozen benchmark       NO               Treat as targets only

  Demo scenario                                OPEN QUESTION    Progress tracker        Working intelligence   NO               Freeze after system
                                                                                                                                path works
  -----------------------------------------------------------------------------------------------------------------------------------------------------

------------------------------------------------------------------------

# 0.3 Remaining coding blockers

## BLOCKER --- Scientific configuration cannot be silently defaulted

Affected: - event clustering; - persistence; - contextual proximity; -
attribution; - calibration; - abstention; - benchmark policy.

Correction: - configuration fields may exist now; - unresolved
scientific values must be nullable/explicitly unset; - execution must
fail with a typed configuration error when a required value is absent; -
test fixtures may use clearly marked `TEST_ONLY` configuration.

## BLOCKER --- Reference labels are not yet available

Affected: - supervised ML; - benchmark; - calibration; - final
abstention tuning.

Correction: - implement reference-data infrastructure now; - do not
train production ML until reference protocol is frozen.

## BLOCKER --- Final taxonomy is not frozen

Affected: - final prediction enum; - model target; - benchmark labels; -
UI claims.

Correction: - use internal provisional/reference-safe representations; -
do not expose unsupported final classes.

## BLOCKER --- Attribution semantics are not frozen

Affected: - facility attribution output; - geospatial error metric.

Correction: - implement proximity/context relationships; - do not
implement facility-causation claims.

## BLOCKER --- Temporal inference mode is not frozen

Affected: - persistence features; - future-observation leakage; - online
vs retrospective behavior.

Correction: - implement `as_of_time` throughout; - make the inference
mode explicit before feature freeze.

------------------------------------------------------------------------

# 0.4 Can Build Now

1.  Repository foundation.
2.  Python 3.11 environment.
3.  Docker Compose development environment.
4.  PostgreSQL/PostGIS.
5.  Configuration loading and validation.
6.  Scientific configuration registry without final values.
7.  Source registry.
8.  Source snapshots/provenance.
9.  Raw source artifact storage abstraction.
10. Canonical schemas.
11. Detection persistence model.
12. FIRMS adapter skeleton and fixture path.
13. Idempotency/hash utilities.
14. Pipeline-run infrastructure.
15. Job abstraction without requiring Redis.
16. API foundation.
17. Structured logging.
18. Health/readiness checks.
19. Offline replay harness.
20. Test fixtures and test framework.
21. Geospatial utility boundary.
22. Reference-event schema and evidence schema.
23. Dataset-version infrastructure.
24. Feature-definition registry.
25. Evidence-engine interfaces.
26. API response contracts.
27. Security middleware foundation.
28. Progress/context synchronization.

# 0.5 Must Wait

1.  Final event clustering parameters.
2.  Final persistence thresholds/semantics.
3.  Final taxonomy.
4.  Final ground-truth labels.
5.  Final benchmark split.
6.  Final feature set.
7.  Final model/hyperparameters.
8.  Calibration method/parameters.
9.  Abstention threshold.
10. Facility attribution claim.
11. Geospatial attribution-error metric.
12. Satellite feature commitment based on availability.
13. Performance claims.

------------------------------------------------------------------------

# 1. Execution Principles

## 1.1 Core rule

The coding agent implements **approved contracts**, not scientific
decisions.

Every unit is atomic, testable, reversible, and scoped.

## 1.2 Dependency direction

``` text
API
 ↓
Application Services
 ↓
Domain / Pipeline Contracts
 ↓
Repositories / Adapters
 ↓
Database / External Sources
```

Cross-domain rule:

``` text
API → service
service → repository/domain
domain → no API
ML → feature contracts, not raw production tables
evidence → validated stored state
source adapters → canonical source contracts
```

No circular imports.

## 1.3 Scientific safety rule

A missing decision must never become a default.

Required behavior:

``` text
missing required scientific configuration
→ typed configuration error
→ job/run blocked
→ ambiguity reported
```

------------------------------------------------------------------------

# 2. Recommended Repository Blueprint

``` text
SIH26162/
├── apps/
│   └── web/
│       ├── src/
│       ├── tests/
│       └── package.json
│
├── services/
│   ├── api/
│   │   ├── routes/
│   │   ├── schemas/
│   │   ├── dependencies/
│   │   └── main.py
│   │
│   ├── worker/
│   │   ├── jobs/
│   │   ├── runners/
│   │   └── main.py
│   │
│   └── ml/
│       ├── features/
│       ├── training/
│       ├── evaluation/
│       ├── inference/
│       └── calibration/
│
├── packages/
│   ├── schemas/
│   ├── config/
│   ├── db/
│   ├── geospatial/
│   ├── sources/
│   ├── pipelines/
│   ├── evidence/
│   └── observability/
│
├── migrations/
├── scripts/
│   ├── seed/
│   ├── replay/
│   ├── validation/
│   └── benchmark/
│
├── tests/
│   ├── fixtures/
│   ├── integration/
│   ├── contract/
│   ├── leakage/
│   └── e2e/
│
├── configs/
│   ├── scientific/
│   ├── sources/
│   ├── demo/
│   └── test_only/
│
├── data/
│   ├── raw/
│   ├── replay/
│   ├── reference/
│   └── manifests/
│
├── docs/
│   └── implementation/
│
├── docker-compose.yml
├── pyproject.toml
├── Makefile
└── README.md
```

## 2.1 Module boundaries

### `apps/web/`

**Responsibility:** future analyst GIS UI.\
**Belongs:** map state, server state, UI state, typed API client.\
**Does not belong:** scientific logic, source credentials, ML
computation.\
**Dependencies:** API contract only.\
**Priority:** P1/P0 once backend intelligence works.

### `services/api/`

**Responsibility:** HTTP boundary.\
**Belongs:** routing, request validation, authorization, response
serialization.\
**Does not belong:** database algorithms, clustering, ML training,
external data transformation.\
**Dependencies:** application services and schemas.\
**Priority:** P0.

### `services/worker/`

**Responsibility:** asynchronous orchestration.\
**Belongs:** job execution and pipeline invocation.\
**Does not belong:** scientific definitions themselves.\
**Dependencies:** pipeline services, repositories, queue.\
**Priority:** P1 initially; P0 for expensive asynchronous workflows.

### `services/ml/`

**Responsibility:** feature construction, training, evaluation,
inference, calibration.\
**Belongs:** model artifacts and experiment code.\
**Does not belong:** direct arbitrary production-table queries or API
logic.\
**Dependencies:** versioned feature contracts and dataset versions.\
**Priority:** P1/conditional.

### `packages/schemas/`

Canonical cross-boundary types.\
**Does not contain:** business logic.

### `packages/config/`

Scientific and operational configuration loading, validation, and
versioning.\
**Does not contain:** hard-coded scientific defaults.

### `packages/db/`

Database sessions, repository primitives, transaction helpers.\
**Does not contain:** clustering or ML logic.

### `packages/geospatial/`

CRS-safe geometry utilities and spatial operations.\
**Does not contain:** classification semantics.

### `packages/sources/`

External source adapters and normalization.\
**Does not contain:** model training or label assignment.

### `packages/pipelines/`

Deterministic domain transformations: detection→event, event→source,
enrichment orchestration.\
**Does not contain:** HTTP concerns.

### `packages/evidence/`

Deterministic evidence derivation from validated state.\
**Does not contain:** LLM-generated factual claims.

------------------------------------------------------------------------

# 3. Database Implementation Order

The database is authoritative for operational state and analytical
lineage. Caches/queues are never authoritative.

## Migration 001 --- `scientific_contracts`

**Purpose:** versioned scientific/configuration contracts.

**PK:** `scientific_contract_id` UUID.

**Fields:** - `scientific_contract_id` - `name` - `version` - `status` -
`parameters_json` - `created_at` - `created_by` - `notes`

**Constraints:** - unique `(name, version)`; - status enum; - required
parameters validated by application layer.

**Immutable:** name/version/parameters after activation.\
**Mutable:** lifecycle metadata only.\
**Retention:** permanent for reproducibility.\
**Scale:** very small.

## Migration 002 --- `source_registry`

**Purpose:** define external/internal data sources and semantic roles.

**Fields:** - `source_id` - `name` - `provider` - `source_type` -
`role` - `observation_family` - `coverage_notes` - `access_method` -
`auth_required` - `license_notes` - `rate_limit_notes` -
`fallback_source_id` - `status` - timestamps.

**Role enum:** `OBSERVATION`, `REFERENCE`, `CONTEXT`, `VALIDATION`,
`ENVIRONMENTAL`, `DERIVED`, `GROUND_TRUTH_CANDIDATE`,
`GROUND_TRUTH_EVIDENCE`, `OPTIONAL`, `DEMO_ONLY`.

## Migration 003 --- `source_snapshots`

**Purpose:** identify exact source/version/retrieval state.

**Fields:** - `source_snapshot_id` - `source_id` - `external_version` -
`retrieved_at` - `acquired_from` - `request_fingerprint` -
`content_hash` - `availability_status` - `error_code` - `metadata_json`

**Important:** external failure and empty result are different states.

## Migration 004 --- `source_records`

**Purpose:** normalized reference to raw source records.

**Fields:** - `source_record_id` - `source_snapshot_id` -
`external_record_id` - `raw_artifact_uri` - `record_hash` -
`record_time` - `geometry` - `raw_metadata_json`

**Unique:** `(source_snapshot_id, record_hash)`.

## Migration 005 --- `detections`

**Purpose:** canonical thermal observations.

**Fields:** - `detection_id` - `source_record_id` -
`source_snapshot_id` - `source` - `satellite` - `instrument` -
`product_type` - `product_version` - `acquired_at` - `ingested_at` -
`latitude` - `longitude` - `geometry` - `frp_mw` - `brightness_ti4_k` -
`brightness_ti5_k` - `confidence_raw` - `day_night` - `scan` - `track` -
`raw_identifier` - `raw_hash` - `quality_status`

**Immutable:** source semantics and observation values.\
**Indexes:** GiST geometry; acquisition time; source snapshot; hash.\
**Scale:** potentially large.

## Migration 006 --- `events`

**Purpose:** deterministic grouping of detections.

**Fields:** - `event_id` - `formation_run_id` -
`scientific_contract_id` - `start_time` - `end_time` -
`centroid_geometry` - `observation_geometry` - `detection_count` -
`formation_status` - `created_at`.

**Derived:** yes.\
**Indexes:** GiST geometry; time range.\
**Unique:** deterministic event identity for same input snapshot +
algorithm/config version where practical.

## Migration 007 --- `event_detections`

Many-to-many or one-to-many association table.

**Fields:** `event_id`, `detection_id`, association metadata.

**Purpose:** traceability.

## Migration 008 --- `persistent_sources`

**Purpose:** represent observed recurrence/persistence without asserting
physical source identity.

**Fields:** - `persistent_source_id` - `source_run_id` - `geometry` -
`first_observed_at` - `last_observed_at` - `event_count` -
`observation_count` - `persistence_state` -
`persistence_statistics_json` - `scientific_contract_id`.

**Terminology:** `CANDIDATE_PERSISTENT_SOURCE` is preferred until
scientifically validated.

## Migration 009 --- `event_persistent_sources`

Association between events and candidate persistent sources.

## Migration 010 --- `facilities`

**Purpose:** normalized industrial/context assets.

**Fields:** - `facility_id` - `source_id` - `external_object_id` -
`facility_type` - `geometry` - `tags_json` - `retrieved_at` -
`source_snapshot_id` - `quality_status`.

OSM absence is never stored as facility absence.

## Migration 011 --- `event_context`

**Purpose:** explicit context relationships.

**Fields:** - `event_id` - `context_type` - `context_source_id` -
`context_source_snapshot_id` - `facility_id` nullable - `distance_m`
nullable - `relationship_status` - `derived_at` - `derivation_version` -
`metadata_json`.

`distance_m` is a contextual measurement, not attribution.

## Migration 012 --- `reference_events`

**Purpose:** candidate/reference incidents used for ground-truth
construction.

**Fields:** - `reference_event_id` - `event_id` nullable -
`reference_type` - `proposed_label` - `annotation_status` -
`adjudication_status` - `created_at` - `notes`.

Allowed label states: `POSITIVE_REFERENCE`, `NEGATIVE_REFERENCE`,
`UNRESOLVED`.

## Migration 013 --- `reference_evidence`

**Purpose:** evidence supporting or contradicting a reference
annotation.

**Fields:** - `reference_evidence_id` - `reference_event_id` -
`source_id` - `source_snapshot_id` - `evidence_type` -
`source_record_id` nullable - `publication_time` nullable -
`evidence_time` nullable - `retrieved_at` - `content_hash` -
`geographic_relationship` - `temporal_relationship` - `strength_class` -
`notes`.

## Migration 014 --- `reference_adjudications`

**Purpose:** preserve disagreements/review history.

**Fields:** - `adjudication_id` - `reference_event_id` - `annotator` -
`decision` - `reason` - `created_at`.

No adjudication row may overwrite evidence history.

## Migration 015 --- `dataset_versions`

**Purpose:** immutable dataset snapshots.

**Fields:** - `dataset_version_id` - `name` - `version` - `purpose` -
`created_at` - `frozen_at` - `manifest_hash` - `source_policy` -
`split_policy`.

## Migration 016 --- `dataset_memberships`

**Purpose:** exact membership in dataset versions.

**Fields:** - `dataset_version_id` - `event_id` / `reference_event_id` -
`membership_type` - `split` - `group_key` - `included_at` -
`exclusion_reason`.

Allowed split values: `TRAIN`, `CALIBRATION`, `VALIDATION`, `TEST`,
`SHOWCASE`, `UNRESOLVED`.

## Migration 017 --- `feature_definitions`

**Purpose:** feature registry.

**Fields:** - `feature_definition_id` - `name` - `version` -
`definition` - `source_role` - `unit` - `aggregation` -
`allowed_inference_modes` - `missingness_policy` - `leakage_notes`.

## Migration 018 --- `feature_sets`

**Purpose:** frozen collection of feature definitions.

**Fields:** - `feature_set_id` - `version` - `feature_definition_ids` -
`dataset_version_id` - `created_at` - `frozen_at`.

## Migration 019 --- `feature_values`

**Purpose:** materialized versioned features.

**Fields:** - `feature_value_id` - `event_id` - `feature_set_id` -
`as_of_time` - `values_json` - `provenance_json` - `missingness_json` -
`created_at`.

## Migration 020 --- `model_versions`

**Purpose:** model artifact registry.

**Fields:** - `model_version_id` - `name` - `algorithm` -
`feature_set_id` - `dataset_version_id` - `training_run_id` -
`artifact_uri` - `code_version` - `random_seed` -
`hyperparameters_json` - `status`.

## Migration 021 --- `predictions`

**Purpose:** model outputs.

**Fields:** - `prediction_id` - `event_id` - `model_version_id` -
`feature_set_id` - `predicted_class` - `raw_probabilities` -
`calibrated_probabilities` - `prediction_time` -
`inference_as_of_time` - `abstained` - `abstention_reason` -
`uncertainty_state`.

## Migration 022 --- `calibration_versions`

**Purpose:** calibration artifact registry.

**Fields:** - `calibration_version_id` - `model_version_id` - `method` -
`fit_dataset_version_id` - `artifact_uri` - `created_at` - `status`.

Test data may not appear as the calibration fitting dataset.

## Migration 023 --- `evidence_items`

**Purpose:** deterministic evidence records.

**Fields:** - `evidence_id` - `event_id` - `prediction_id` nullable -
`source_id` - `source_snapshot_id` - `evidence_category` -
`derivation_rule` - `derivation_version` - `value_json` -
`observed_at` - `derived_at` - `provenance_json`.

## Migration 024 --- `intelligence_results`

**Purpose:** final analyst-facing intelligence object.

**Fields:** - `intelligence_result_id` - `event_id` - `prediction_id` -
`phenomenon` - `context` - `persistence_state` - `attribution_state` -
`uncertainty_state` - `evidence_completeness` - `created_at` -
`pipeline_run_id`.

Do not use a single generic confidence field as the semantic container
for all uncertainty.

## Migration 025 --- `pipeline_runs`

**Purpose:** reproducibility and lineage.

**Fields:** - `pipeline_run_id` - `pipeline_name` - `pipeline_version` -
`scientific_contract_id` - `input_snapshot_ids` - `dataset_version_id`
nullable - `model_version_id` nullable - `started_at` - `completed_at` -
`status` - `code_version` - `configuration_hash` -
`output_manifest_hash` - `error_code`.

## Migration 026 --- `jobs`

**Purpose:** authoritative job state.

**Fields:** - `job_id` - `job_type` - `pipeline_run_id` -
`idempotency_key` - `state` - `attempt_count` - `created_at` -
`started_at` - `completed_at` - `error_code` - `error_message_safe` -
`input_reference`.

Allowed states: `QUEUED`, `RUNNING`, `SUCCEEDED`, `FAILED`,
`CANCEL_REQUESTED`, `CANCELLED`, `BLOCKED`.

Redis is transient coordination only.

## Migration 027 --- optional `evaluations`

Create when benchmark infrastructure begins.

Fields: - `evaluation_id` - `dataset_version_id` - `model_version_id` -
`feature_set_id` - `split_definition` - `metrics_json` -
`calibration_metrics_json` - `coverage_metrics_json` -
`ablation_definition` - `created_at`.

------------------------------------------------------------------------

# 4. Canonical Data Contracts

All timestamps are UTC internally unless explicitly documented
otherwise.

## 4.1 Detection

Required: - `detection_id` - `source` - `source_snapshot_id` -
`acquired_at` - `geometry` - `satellite` - `instrument` -
`product_type` - `product_version` - `raw_hash`

Optional: - FRP - brightness temperatures - confidence - scan - track -
day/night - quality fields.

Semantics: - `acquired_at` = observation/acquisition time supplied by
source. - `ingested_at` = system ingestion time. - `retrieved_at`
belongs to source snapshot, not observation.

## 4.2 Event

Required: - `event_id` - formation configuration/version - detection
membership - temporal span - event geometry - formation run.

`centroid_geometry` is an event representation, not exact
source/facility location.

## 4.3 Persistent Source

Required: - identity - event associations - observation history -
persistence statistics - persistence configuration/version.

Semantics: - observed persistence ≠ proven physical persistence.

## 4.4 Facility

Required: - source identity - external identifier where available -
geometry - facility/context type - source snapshot.

OSM facility presence is contextual evidence.

## 4.5 SourceRecord

Represents a raw/normalized external record with source snapshot and
hash.

## 4.6 SourceSnapshot

Represents a versioned retrieval state, including: - retrieval time; -
source version; - content hash; - request fingerprint; -
availability/error state.

## 4.7 ReferenceEvent

Represents a candidate benchmark/reference incident.

Must support: - positive; - negative; - unresolved.

Unresolved is never automatically converted to negative.

## 4.8 ReferenceEvidence

Represents evidence used to support a reference annotation.

Timestamp semantics: - `evidence_time`: time the evidence refers to,
when known. - `publication_time`: when the evidence was published, when
known. - `retrieved_at`: when the system obtained it.

## 4.9 DatasetVersion

Frozen logical dataset definition plus manifest hash.

## 4.10 FeatureDefinition

Required: - name/version; - mathematical/semantic definition; -
source; - unit; - aggregation; - inference mode; - `as_of_time` rule; -
missingness; - leakage risk.

## 4.11 Prediction

Must distinguish: - raw probabilities; - calibrated probabilities; -
abstention; - uncertainty; - model version; - feature set; - inference
`as_of_time`.

## 4.12 Evidence

Every evidence item must identify: - source; - source snapshot; -
derivation rule/version; - observed/derived timestamps; - value; -
provenance.

## 4.13 IntelligenceResult

Must keep orthogonal: - phenomenon; - context; - persistence; -
attribution; - uncertainty; - evidence completeness.

## 4.14 PipelineRun

The reproducibility unit:
`inputs + configuration + code + model + outputs`.

## 4.15 Job

Operational execution state only. It does not replace pipeline lineage.

------------------------------------------------------------------------

# 5. Verified Data-Source Execution Registry

The supplied data-source stack is incorporated, but its recommendations
are treated as provisional. In particular, claims such as "strongest
signal," "ground truth," "auto-tag," "likely industrial," or "best
discriminator" are not automatically accepted as scientific truth.

## 5.1 NASA FIRMS

**Role:** `OBSERVATION`, P0.\
**Use:** primary thermal anomaly observation stream and historical
source.\
**Does not mean:** confirmed industrial fire, exact facility location,
or ground truth.

Known fields include observation time, location, FRP, brightness
temperatures, confidence, satellite/instrument and product/version
metadata. The project code standards require source/version/provenance
preservation and server-side credentials.

Implementation:
`source adapter → raw capture → validation → normalization → deduplication → Detection`.

Unknown operational values such as current API limits must be discovered
from official documentation/runtime testing, not invented.

## 5.2 FIRMS Archive

**Role:** `OBSERVATION`, `REFERENCE INPUT`, P0.\
**Use:** historical replay/training candidate source.\
**Does not mean:** labels.

Historical source/product availability must be recorded per snapshot.

## 5.3 VIIRS Nightfire

**Role:** `OBSERVATION`, `CORROBORATION`, `REFERENCE`, P1/conditional P0
only after feasibility.\
**Use:** candidate thermal-source characterization and
persistence-related signal.\
**Does not mean:** independently validated industrial-fire ground truth.

If VNF contributes to a reference label, VNF-derived features must be
excluded from that benchmark case's feature set or the label-source
leakage must be explicitly accounted for.

## 5.4 Global Gas Flare Survey

**Role:** `REFERENCE`, `CORROBORATION`, `GROUND-TRUTH CANDIDATE`, P1.\
**Use:** known historical flare-source reference.\
**Does not mean:** universal independent ground truth.

Temporal and source-family overlap with VIIRS-derived features must be
audited.

## 5.5 World Bank Global Gas Flaring Tracker

**Role:** `REFERENCE`, `CORROBORATION`, P1.\
**Use:** persistent flare-source reference/corroboration.\
**Critical semantic correction:** it is satellite-derived VIIRS-based
reference data, not automatically independent ground truth.

A known flare must never be auto-tagged as "non-alert" by default. Use
`known_persistent_flare_reference` instead.

## 5.6 OpenStreetMap / Geofabrik / Overpass

**Role:** `CONTEXT`, P0.\
**Use:** industrial infrastructure/context.\
**Does not mean:** facility completeness or incident truth.

Preferred architecture:
`bulk/local source → normalized facilities → PostGIS → spatial index → event enrichment`.

Overpass is not the default per-event dependency.

Store: - OSM object ID; - tags; - geometry; - retrieval time; - query
parameters/source snapshot.

`not_found_in_osm` is not equivalent to `facility_absent`.

## 5.7 ESA WorldCover

**Role:** `CONTEXT`, P0/P1.\
**Use:** land-cover context.

Do not equate `built-up` with industrial or `tree cover` with wildfire.
Land-cover values are features/evidence, not hard routing decisions.

## 5.8 Dynamic World

**Role:** `CONTEXT`, `DERIVED`, P1/conditional.\
**Use:** time-varying land-cover probability features.

Every value must be tied to imagery acquisition time and feature
`as_of_time`.

Do not use a later image to represent historical inference unless the
inference mode explicitly permits retrospective evidence.

## 5.9 Sentinel-2

**Role:** `OBSERVATION`, `CORROBORATION`, `CONTEXT`, P1.\
**Use:** optional optical corroboration and feature extraction.

Catalog presence is not equivalent to usable imagery. Model state:
`NOT_SEARCHED → NO_ASSET → ASSET_FOUND → UNSUITABLE → USABLE → ANALYZED`.

Satellite is never mandatory for the core intelligence path.

## 5.10 Sentinel-3 SLSTR FRP

**Role:** `OBSERVATION`, `VALIDATION`, `CORROBORATION`, P1.\
**Use:** independent sensor/product corroboration.\
**Does not automatically mean:** ground truth.

## 5.11 MCD64A1 Burned Area

**Role:** `VALIDATION`, `CORROBORATION`, P1.\
**Use:** burned-area evidence for vegetation-fire hypotheses.

"No burned area detected" is not equivalent to "did not burn." Preserve:
`DETECTED`, `NOT_DETECTED`, `UNAVAILABLE`, `INCONCLUSIVE`.

## 5.12 Landsat / HLS

**Role:** `OBSERVATION`, `CONTEXT`, `CORROBORATION`, P1/P2.\
**Use:** historical/optical alternatives where needed.

## 5.13 ERA5-Land / NASA POWER / GFWED

**Role:** `ENVIRONMENTAL`, P1/P2.\
**Use:** weather/fire-weather context.

Do not hard-code the data-source recommendation that weather should only
be applied to non-industrial events; that is a provisional
feature-selection hypothesis and must be experimentally evaluated.

## 5.14 Google Open Buildings

**Role:** `CONTEXT`, P2.\
**Use:** building-density/context feature where coverage and
licensing/access are acceptable.

## 5.15 Bhuvan / ISRO forest-fire alerts

**Role:** `VALIDATION`, `CORROBORATION`, potentially `REFERENCE`, P1.\
**Use:** India-specific cross-validation/reference source.

Its actual access, licensing, historical availability, and programmatic
interface must be verified before production ingestion.

## 5.16 NOAA HMS

**Role:** `OPTIONAL`, `VALIDATION`, `CORROBORATION`, P2.\
**Use:** only where coverage is applicable.

## 5.17 GOES

**Role:** `OPTIONAL`, `DEMO-ONLY` architecture compatibility.\
**India MVP:** do not use as a data dependency because the supplied
source stack identifies India as outside GOES coverage.

## 5.18 Earth Engine

**Role:** `PROCESSING/ACCESS MECHANISM`, `OPTIONAL`.\
It is not ground truth, not a model, and not an authoritative evidence
layer.

Use for prototyping only unless operational testing proves it suitable
for production inference.

------------------------------------------------------------------------

# 6. FIRMS Implementation Contract

## Pipeline

``` text
FIRMS configuration
→ authenticated server-side client
→ bounded request
→ raw capture
→ source snapshot
→ schema validation
→ normalization
→ duplicate detection
→ canonical Detection
→ PostGIS
→ pipeline-run lineage
```

## Required behavior

-   Credentials only in server-side environment/secret storage.
-   No frontend credential access.
-   Timeout configured operationally.
-   Retry policy distinguishes retryable/non-retryable errors.
-   Rate-limit handling must use documented/runtime-observed limits.
-   Historical immutable results should be cached.
-   NRT and historical/other product identities must not be silently
    mixed.
-   Empty result and request failure must remain distinct.
-   Raw source payload/hash must be preserved where permitted.

## Deduplication

Deduplication must be deterministic and source-aware.

Candidate identity may use: - source snapshot; - source-provided ID if
reliable; - canonical record hash.

Do not merge spatially similar detections merely because they are close.

## Acceptance

-   Same fixture produces same canonical detections.
-   Raw provenance remains queryable.
-   Duplicate fixture records do not create duplicate canonical records.
-   External failure produces explicit failure state.
-   Empty valid response produces explicit empty-result state.
-   No secret appears in logs/tests/browser.

------------------------------------------------------------------------

# 7. Detection → Event Architecture

## Interface

``` text
EventFormationService.form(
    detections,
    scientific_contract,
    inference_mode,
    as_of_time
) -> EventFormationResult
```

The implementation must not contain a scientific default.

Configuration fields may include: - spatial radius; - temporal gap; -
minimum observations; - algorithm version.

All values remain unset until scientifically selected.

## Determinism

Same: `input snapshot + scientific contract + code version` must produce
the same event assignments.

## Required tests

-   points outside study bounds;
-   timestamps out of order;
-   duplicate detections;
-   identical timestamps;
-   events crossing date boundaries;
-   detections near spatial boundary;
-   single detection;
-   disconnected clusters;
-   empty input;
-   missing scientific parameter.

## Acceptance

-   every assigned detection is traceable;
-   no detection is silently lost;
-   event geometry is deterministic;
-   event temporal span is correct;
-   configuration/version is persisted;
-   missing required configuration blocks execution.

------------------------------------------------------------------------

# 8. Persistent-Source Architecture

The software abstraction is:

``` text
events
→ source association
→ observed persistence statistics
→ candidate persistent source
```

Terminology: - `TRANSIENT` - `RECURRING` -
`CANDIDATE_PERSISTENT_SOURCE` - `INSUFFICIENT_HISTORY` - `UNKNOWN`

Final semantic thresholds remain OPEN.

Persistence features must be computed from observations available at
`as_of_time` for the chosen inference mode.

Do not claim: `persistent cluster = gas flare`, or:
`persistent cluster = industrial facility`.

------------------------------------------------------------------------

# 9. Industrial Context Architecture

## Preferred pipeline

``` text
bulk/local OSM or Geofabrik
→ source snapshot
→ normalization
→ facilities
→ PostGIS spatial index
→ event-context relation
```

Per-event Overpass is an exception, not the default.

## Context output

For each event, produce: - nearby facility references; - facility
type; - distance measurement; - source provenance; - context
availability; - relationship status.

Do not output: `facility_caused_event = true` from proximity alone.

## Reporting-bias handling

Track: - OSM coverage observed; - missingness; - source snapshot; -
region; - retrieval date.

Do not interpret missing OSM objects as evidence of absence.

------------------------------------------------------------------------

# 10. Land-Cover Architecture

WorldCover/Dynamic World pipeline:

``` text
catalog/source
→ versioned asset
→ acquisition metadata
→ spatial sampling
→ nodata handling
→ feature definition
→ feature value + provenance
```

Required fields: - dataset/version; - acquisition time; - CRS; - nominal
resolution; - sampling geometry; - nodata state; - retrieval time; -
source snapshot.

Do not hard-route: `built-up → industrial` or: `tree cover → wildfire`.

These may be candidate model features.

------------------------------------------------------------------------

# 11. Satellite Architecture

## State machine

``` text
NOT_REQUESTED
→ SEARCHING
→ NO_ASSET
→ ASSET_FOUND
→ UNSUITABLE
→ USABLE
→ RETRIEVAL_FAILED
→ ANALYZED
```

An unavailable satellite asset must never become: `absence`,
`negative evidence`, or: `not a fire`.

## Abstraction

``` text
SatelliteCatalog
→ discover assets
→ evaluate availability
→ optional retrieval
→ optional processing
→ derived evidence
```

The core event intelligence path must remain functional without
satellite data.

------------------------------------------------------------------------

# 12. Reference / Ground-Truth Pipeline

## Required separation

``` text
Reference source
→ evidence record
→ candidate reference event
→ annotation
→ adjudication
→ dataset membership
```

Never:

``` text
external source
→ automatic label
→ ML
```

without explicit scientific justification.

## Label states

``` text
POSITIVE_REFERENCE
NEGATIVE_REFERENCE
UNRESOLVED
```

Unresolved must never become negative.

## Evidence hierarchy

Use source-role semantics rather than assuming all sources have equal
authority.

Potential evidence categories: - authoritative incident/government
record; - strong independent report; - satellite corroboration; -
contextual reference; - proxy/weak evidence.

Satellite-derived flare databases remain reference/corroboration unless
independent evidence establishes a stronger role.

## Required temporal fields

Where available: - event time; - evidence time; - publication time; -
retrieval time.

This allows retrospective reference construction without pretending the
evidence was available at historical inference time.

------------------------------------------------------------------------

# 13. Dataset Versioning

Dataset lifecycle:

``` text
BUILDING
→ REVIEWED
→ FROZEN
→ SUPERSEDED
```

A frozen dataset is immutable.

Manifest must include: - member IDs; - labels; - split; - group keys; -
source versions; - reference evidence versions; - creation timestamp; -
manifest hash.

## Split isolation

Minimum conceptual split: - train; - calibration; - validation where
used; - untouched test; - showcase.

No random point-level split for final benchmark.

Group repeated detections from the same event/source.

Use spatial and temporal holdout where feasible.

Showcase data is never benchmark evidence.

------------------------------------------------------------------------

# 14. Feature Engineering Architecture

## Feature lifecycle

``` text
FeatureDefinition
→ leakage audit
→ availability test
→ implementation
→ fixture test
→ feature set version
→ dataset materialization
```

Every feature must declare: - name; - definition; - unit; - source; -
version; - aggregation; - `as_of_time`; - inference modes; -
missingness; - provenance; - leakage risk.

## Feature categories

1.  `OBSERVATION_DERIVED`
2.  `SOURCE_HISTORY`
3.  `CONTEXT`
4.  `LAND_COVER`
5.  `SATELLITE`
6.  `ENVIRONMENTAL`
7.  `REFERENCE` --- generally forbidden as a model input if it is
    label-generating evidence for the same benchmark case.

## Leakage rule

For every feature ask:

> Could this exact value have been known at the declared inference
> `as_of_time`?

If no, it cannot enter that inference mode.

------------------------------------------------------------------------

# 15. ML Implementation Order

## B0 --- Class-prior/majority baseline

Purpose: - establish trivial performance; - reveal class imbalance.

No scientific assumptions beyond frozen labels.

## B1 --- Detection-quality diagnostic baseline

Candidate: - FIRMS confidence/quality information.

Interpretation: - detection-quality baseline, not industrial-fire
classifier.

## B2 --- Deterministic contextual baseline

Candidate evidence: - persistence/context/land-cover relationships.

Do not invent hard thresholds. Any threshold must come from a frozen
scientific configuration or an experiment.

## B3 --- Simple statistical model

Use a simple interpretable classifier if labels/features support it.

## B4 --- Tree-based model

XGBoost/LightGBM remain candidate families, not mandatory winners.

## B5 --- Advanced model

Only if: - benchmark is valid; - baseline is insufficient; - data volume
supports it; - measurable gain justifies complexity.

## Required model artifact

-   dataset version;
-   feature set;
-   code version;
-   random seed;
-   algorithm;
-   hyperparameters;
-   training timestamp;
-   artifact hash;
-   evaluation configuration.

------------------------------------------------------------------------

# 16. Calibration

Pipeline:

``` text
raw prediction
→ calibration artifact
→ calibrated probability
```

Calibration fitting must use only the designated calibration/training
data.

The untouched test set is never used to fit calibration.

The calibration method remains PROVISIONAL until experiments determine
an appropriate approach.

Required tests: - artifact loads; - calibration dataset is not test; -
model/calibration version mismatch fails; - probabilities remain
valid; - deterministic output for deterministic model/config.

------------------------------------------------------------------------

# 17. Abstention

Abstention is a decision layer, not merely a low-probability class.

Possible inputs: - calibrated probability; - uncertainty; - evidence
sufficiency; - history sufficiency; - context availability; - satellite
state.

Outputs: - decision; - abstained; - reason.

Possible reasons: - `INSUFFICIENT_HISTORY` - `INSUFFICIENT_EVIDENCE` -
`MODEL_UNCERTAINTY` - `CONTEXT_UNAVAILABLE` - `SATELLITE_UNAVAILABLE` -
`CONFIGURATION_INCOMPLETE`

Final thresholds are OPEN.

Evaluation must report: - coverage; - selective risk/error; -
class-specific recall/precision; - abstention rate; - trivial abstention
baseline.

Never optimize only precision by abstaining on nearly everything.

------------------------------------------------------------------------

# 18. Evidence Engine

## Rule

Evidence is generated independently from validated source state and
deterministic derivation rules.

Preferred flow:

``` text
source records
→ deterministic evidence derivation
→ evidence items
→ intelligence result
```

Not:

``` text
prediction
→ choose only supporting features
→ explanation
```

## Evidence categories

-   observation;
-   temporal;
-   spatial;
-   infrastructure;
-   land-cover;
-   satellite;
-   persistence;
-   model contribution.

Each evidence item stores: - source; - source snapshot; - derivation
rule; - derivation version; - value; - observed time; - derived time; -
provenance.

## Evidence completeness

The existing project definition may be used as a framework:

`available expected evidence / expected evidence`

but exact expected-slot policy must be frozen before benchmark claims.

Missing satellite evidence reduces completeness where expected; it does
not imply a negative class.

------------------------------------------------------------------------

# 19. Intelligence Result

The final object must distinguish:

``` text
phenomenon
context
persistence_state
attribution_state
uncertainty_state
evidence_completeness
```

It may also contain: - calibrated probability; - raw probability; -
model version; - feature version; - evidence references; - source
provenance; - geometry.

Avoid a generic `confidence` field that conflates: - model
probability; - evidence strength; - attribution; - data quality.

------------------------------------------------------------------------

# 20. API Implementation Order

## API-001 --- Health

`GET /health`

Returns service status only.

## API-002 --- Readiness

`GET /ready`

Checks required dependencies without exposing secrets.

## API-003 --- Version

`GET /version`

Returns application/code contract version.

## API-004 --- Source status

`GET /sources/status`

Returns source availability/failure state.

## API-005 --- Detections

`GET /detections`

Core filters: - bounding box; - time range; - source; - pagination.

Exact pagination semantics must be frozen before UI integration.

## API-006 --- Events

`GET /events`

Filters: - time; - bbox; - status; - classification state.

## API-007 --- Event detail

`GET /events/{event_id}`

Returns: - event geometry; - temporal span; - detection count; - context
status; - intelligence status.

## API-008 --- Timeline

`GET /events/{event_id}/timeline`

## API-009 --- Evidence

`GET /events/{event_id}/evidence`

## API-010 --- Sources

`GET /sources` `GET /sources/{source_id}`

## API-011 --- Intelligence

`GET /events/{event_id}/intelligence`

## API-012 --- Map layers

`GET /layers/events` `GET /layers/persistent-sources`
`GET /layers/industrial` `GET /layers/land-cover`

All map endpoints require bounded spatial/time queries.

## API-013 --- Jobs

`POST /jobs/ingest` `POST /jobs/enrich` `POST /jobs/classify`

Mutation requests require: - authentication/authorization as
configured; - idempotency key; - input reference; - pipeline/scientific
configuration version.

## API-014 --- Pipeline runs

`GET /pipeline-runs/{id}`

## API-015 --- Datasets/evaluations

Expose only once benchmark infrastructure exists.

------------------------------------------------------------------------

# 21. Async Job Architecture

Start with synchronous domain services.

Then add:

``` text
API
→ job record
→ Redis queue
→ worker
→ domain service
→ authoritative DB state
```

## Job states

``` text
QUEUED
RUNNING
SUCCEEDED
FAILED
BLOCKED
CANCEL_REQUESTED
CANCELLED
```

## Idempotency

A retry must not create duplicate logical analytical artifacts.

Logical artifact identity should be derived from: - input snapshot; -
algorithm/config version; - code version; - model version where
applicable.

## Failure semantics

-   retryable external error → bounded retry;
-   non-retryable validation error → failed;
-   missing scientific configuration → blocked;
-   external source unavailable → partial/blocked according to
    dependency contract;
-   empty valid result → successful empty result.

Redis is not the source of truth.

------------------------------------------------------------------------

# 22. Offline Demo Architecture

The demo must work without live external APIs.

## Replay bundle

Include captured/versioned: - FIRMS records; - OSM context; - land-cover
assets/features; - reference evidence; - optional satellite
assets/metadata; - model/calibration artifacts if available.

## Commands

Conceptual commands: - `seed-demo` - `run-demo` - `reset-demo` -
`replay-demo` - `verify-demo`

Exact command names may be selected during repository initialization,
but behavior must match these contracts.

## Demo acceptance

A fresh environment can: 1. seed the bundle; 2. run pipeline; 3.
retrieve intelligence; 4. retrieve evidence; 5. render GIS layers; 6.
repeat and obtain deterministic results.

------------------------------------------------------------------------

# 23. GIS Architecture

Canonical internal geospatial storage: - PostGIS; - spatial indexes; -
geometry constraints.

API interchange: - GeoJSON with explicitly documented CRS semantics; -
avoid claiming more precision than source supports.

Map layers: 1. raw FIRMS detections; 2. event geometries; 3. candidate
persistent sources; 4. industrial/context layers; 5. land-cover context;
6. intelligence overlays.

Never replace an event geometry with facility geometry merely for visual
convenience.

------------------------------------------------------------------------

# 24. Testing Strategy

## Unit

Required: - schema validation; - timestamps; - configuration
validation; - hashing; - deduplication; - event algorithm; - persistence
statistics; - feature construction; - evidence generation; -
calibration; - abstention.

## Integration

Required: - FIRMS fixture → source snapshot → detection; - OSM fixture →
facility/context; - event → feature set; - prediction → evidence; -
PostGIS spatial queries; - API → service → DB.

## Contract

Every external adapter has: - fixture; - schema; - error fixture; -
empty-response fixture; - version/provenance fixture.

## Geospatial

Test: - CRS; - geodesic/projected distance; - geometry validity; -
bbox; - antimeridian/boundary edge cases where relevant; - no naïve
degree-to-meter distance.

## Leakage

Required tests: - repeated event/source does not cross splits; - future
feature values are rejected; - test labels unavailable to training; -
reference-derived features cannot enter the same benchmark case if they
generated the label; - satellite availability bias is measurable; -
OSM/context shortcut ablations exist.

## End-to-end

Fixed replay event:

``` text
FIRMS
→ event
→ persistence
→ context
→ features
→ baseline/model
→ calibration
→ abstention
→ evidence
→ intelligence
→ API
→ GIS
```

------------------------------------------------------------------------

# 25. Evaluation and Benchmarking

## Required baseline ladder

``` text
B0 majority/prior
B1 FIRMS detection-quality
B2 deterministic context/persistence
B3 simple statistical model
B4 tree-based model
B5 advanced model only if justified
```

## Required metrics

At minimum, when applicable: - precision; - recall; - macro F1; -
PR-AUC; - class-specific metrics; - calibration; - coverage/selective
risk; - false-positive rate; - persistent-source performance; - latency.

Team targets remain **unvalidated targets**, including the previously
proposed: - accuracy ≥95%; - macro F1 ≥0.92; - industrial
precision/recall ≥95%; - high-confidence FPR \<3%; - coverage ≥95%; -
persistent-source F1 ≥0.85; - median geospatial error \<500 m; - 10,000
events \<5 min; - evidence completeness ≥90%.

No target is a result until measured on a frozen benchmark.

## Benchmark gates

A model may advance only if: 1. dataset is frozen; 2. leakage tests
pass; 3. baseline is measured; 4. model is reproducible; 5. calibration
is valid; 6. ablations are complete; 7. error analysis is documented; 8.
improvement is demonstrated under the frozen evaluation protocol.

The meaning of "material improvement" remains an explicit decision to be
frozen before final model selection; it must not be changed after seeing
results.

------------------------------------------------------------------------

# 26. Security

Minimum: - secrets in environment/secret storage; - no FIRMS MAP_KEY in
frontend; - authorization before mutations; - rate limiting; -
audit/security logs; - input validation; - bounded request size; - safe
error responses; - dependency scanning; - least privilege.

External payloads must be bounded and validated.

Job submission must be protected because it can trigger expensive
external work.

Never log: - API keys; - credentials; - tokens; - full large payloads
unnecessarily.

------------------------------------------------------------------------

# 27. Observability

Structured logs: - timestamp; - service; - request ID; - pipeline run
ID; - job ID; - event ID where applicable; - operation; - duration; -
status; - error code.

Every external source must distinguish: - request failure; -
authentication failure; - rate limit; - timeout; - malformed payload; -
empty successful response; - unavailable source.

Metrics: - ingestion success; - duplicate rate; - records processed; -
enrichment latency; - external failure counts; - model latency; - queue
depth; - coverage; - abstention rate; - API latency.

Prometheus/Grafana remain optional until operational need is measured.

------------------------------------------------------------------------

# 28. Performance Strategy

Do not optimize before profiling.

Measure separately: 1. external download latency; 2. parsing/validation;
3. database operations; 4. spatial operations; 5. raster processing; 6.
feature computation; 7. model inference; 8. serialization; 9.
end-to-end.

High-risk bottlenecks: - per-event OSM/Overpass calls; - per-event
satellite retrieval; - large unindexed spatial joins; - repeated
downloads; - Python loops over large datasets; - sending raw point
clouds to browser.

Preferred order: 1. cache/download elimination; 2. database/index/query
optimization; 3. raster operations; 4. vectorization; 5. serialization;
6. model inference.

Targets remain engineering targets only.

------------------------------------------------------------------------

# 29. Deployment

## MVP Docker Compose

``` text
api
worker
postgres-postgis
redis
```

Add:

``` text
web
```

when API intelligence is usable.

Object storage: - introduce only when large artifacts require it; - keep
large raster/model/raw artifacts outside PostgreSQL; - DB stores
metadata and URI/hash.

Optional: - MLflow; - Prometheus; - Grafana.

No Kafka.

No microservices.

------------------------------------------------------------------------

# 30. Dependency Graph

``` text
PHASE 0
Repository + environment
        ↓
PHASE 1
Scientific/config + source/provenance contracts
        ↓
PHASE 2
PostGIS + migrations
        ↓
PHASE 3
Canonical schemas + repositories
        ↓
PHASE 4
FIRMS adapter + offline fixtures
        ↓
PHASE 5
Detection persistence
        ↓
PHASE 6
Event engine framework
        ↓
PHASE 7
Observed persistent-source framework
        ↓
PHASE 8
OSM/context + land-cover
        ↓
PHASE 9
Reference/ground-truth registry
        ↓
PHASE 10
Dataset versioning
        ↓
PHASE 11
Feature registry + leakage controls
        ↓
PHASE 12
Baselines
        ↓
PHASE 13
ML
        ↓
PHASE 14
Calibration
        ↓
PHASE 15
Abstention
        ↓
PHASE 16
Evidence
        ↓
PHASE 17
Intelligence
        ↓
PHASE 18
API
        ↓
PHASE 19
Async jobs
        ↓
PHASE 20
GIS
        ↓
PHASE 21
Offline demo hardening
        ↓
PHASE 22
Performance/security/reproducibility hardening
```

## Parallelizable tracks

After Phase 1: - database foundation; - source adapter scaffolding; -
API foundation; - offline replay framework; - test fixtures.

After Phase 5: - OSM adapter; - land-cover adapter; - reference
registry; - API read models.

ML work can begin only after valid dataset/feature contracts exist.

Frontend can begin only after stable API contracts and working
intelligence.

------------------------------------------------------------------------

# 31. Atomic Implementation Units

Every task below is intentionally small. A task may be split further if
an agent discovers it is larger than one reviewable change.

## Foundation

### BE-001 --- Repository skeleton

**Priority:** P0\
**Status:** READY\
**Dependencies:** none\
**Objective:** create the approved directory/module structure and
build/test configuration.\
**Files:** repository root, `apps/`, `services/`, `packages/`, `tests/`,
config files.\
**DB:** none.\
**API:** none.\
**Tests:** import/build smoke test.\
**Acceptance:** repository structure exists; imports work; no circular
dependency introduced; lint/test commands execute.\
**Definition of done:** clean baseline commit.\
**Risks:** over-scaffolding.\
**Rollback:** remove unused scaffolding.\
**Scientific decisions:** none.

### BE-002 --- Python/tooling contract

**Priority:** P0\
**Status:** LOCKED\
**Dependencies:** BE-001\
**Objective:** establish Python 3.11+, Ruff, Pytest, type checking.\
**Tests:** intentional lint/type failure fixture where practical, then
clean pass.\
**Acceptance:** commands are reproducible in clean environment.

### BE-003 --- Environment/config loader

**Priority:** P0\
**Status:** READY\
**Dependencies:** BE-002\
**Objective:** typed operational configuration with secret handling.\
**DB:** none.\
**Acceptance:** environment variables load; missing required operational
settings fail clearly; secrets are not logged.

### BE-004 --- Scientific configuration contract

**Priority:** P0\
**Status:** LOCKED\
**Dependencies:** BE-003\
**Objective:** create typed versioned scientific configuration interface
without final values.\
**DB:** prepares Migration 001.\
**Acceptance:** required unset values remain unset; execution can detect
incomplete scientific configuration.\
**Stop condition:** agent must stop if asked to invent a scientific
default.

### BE-005 --- Structured error taxonomy

**Priority:** P0\
**Status:** READY\
**Dependencies:** BE-003\
**Objective:** common typed error codes for validation, external
failure, configuration, job, and data states.\
**Acceptance:** errors are serializable and safe for API responses.

### BE-006 --- Structured logging

**Priority:** P1\
**Status:** READY\
**Dependencies:** BE-005\
**Objective:** request/job/pipeline-aware logs.\
**Acceptance:** IDs appear; secrets excluded.

------------------------------------------------------------------------

## Database

### DB-001 --- PostGIS Compose service

**Priority:** P0\
**Status:** LOCKED\
**Dependencies:** BE-001\
**Objective:** local Postgres/PostGIS service.\
**Tests:** connection and extension smoke test.\
**Acceptance:** clean environment can start DB.

### DB-002 --- Migration framework

**Priority:** P0\
**Status:** READY\
**Dependencies:** DB-001\
**Objective:** migration tooling and CI execution.\
**Acceptance:** up/down or approved migration lifecycle works.

### DB-003 --- Scientific contracts migration

**Priority:** P0\
**Status:** LOCKED\
**Dependencies:** DB-002, BE-004\
**Acceptance:** versioned contracts persist without requiring scientific
values.

### DB-004 --- Source registry migration

**Priority:** P0\
**Status:** LOCKED\
**Dependencies:** DB-003\
**Acceptance:** all source roles supported.

### DB-005 --- Source snapshots migration

**Priority:** P0\
**Status:** LOCKED\
**Dependencies:** DB-004\
**Acceptance:** version/hash/retrieval/error states persist.

### DB-006 --- Source records migration

**Priority:** P0\
**Status:** LOCKED\
**Dependencies:** DB-005\
**Acceptance:** raw record lineage is queryable.

### DB-007 --- Detection migration

**Priority:** P0\
**Status:** LOCKED\
**Dependencies:** DB-006\
**Acceptance:** canonical detection schema and spatial/time indexes
work.

### DB-008 --- Event migrations

**Priority:** P0\
**Status:** CONDITIONAL\
**Dependencies:** DB-007, BE-004\
**Acceptance:** event and detection association tables exist; no
clustering values hard-coded.

### DB-009 --- Persistent-source migrations

**Priority:** P1\
**Status:** CONDITIONAL\
**Dependencies:** DB-008\
**Acceptance:** candidate source state can be stored without
physical-source claims.

### DB-010 --- Context/facility migrations

**Priority:** P0\
**Status:** LOCKED\
**Dependencies:** DB-004\
**Acceptance:** facility provenance and event-context relationship
persist.

### DB-011 --- Reference-data migrations

**Priority:** P0\
**Status:** LOCKED\
**Dependencies:** DB-004, DB-005\
**Acceptance:** reference event/evidence/adjudication states support
unresolved labels.

### DB-012 --- Dataset/feature migrations

**Priority:** P1\
**Status:** LOCKED\
**Dependencies:** DB-011\
**Acceptance:** frozen datasets and feature definitions can be
versioned.

### DB-013 --- ML/evidence/result migrations

**Priority:** P1\
**Status:** CONDITIONAL\
**Dependencies:** DB-012\
**Acceptance:** prediction, calibration, evidence, intelligence tables
preserve lineage.

### DB-014 --- Pipeline/job migrations

**Priority:** P0\
**Status:** LOCKED\
**Dependencies:** DB-003\
**Acceptance:** run/job state is authoritative and queryable.

------------------------------------------------------------------------

## Source ingestion

### DATA-001 --- Study-area feasibility harness

**Priority:** P0\
**Status:** OPEN QUESTION\
**Dependencies:** DB-007\
**Objective:** measure candidate Indian geography data availability.\
**Inputs:** candidate geography options.\
**Outputs:** FIRMS volume, source coverage, candidate reference volume.\
**Acceptance:** evidence-based geography recommendation, no silent
selection.\
**Stop:** if insufficient data, return findings and request decision.

### DATA-002 --- FIRMS canonical parser

**Priority:** P0\
**Status:** READY\
**Dependencies:** DB-006, BE-004\
**Objective:** parse supplied FIRMS fixtures into canonical source
records.\
**Acceptance:** schema validation, provenance, deterministic parsing.

### DATA-003 --- FIRMS raw capture adapter

**Priority:** P0\
**Status:** READY after DATA-002\
**Dependencies:** DATA-002, source registry\
**Objective:** external FIRMS retrieval.\
**Tests:** success, empty, timeout, rate limit, malformed payload.\
**Acceptance:** failures explicit; no secret leakage.

### DATA-004 --- FIRMS deduplication

**Priority:** P0\
**Status:** READY\
**Dependencies:** DATA-003\
**Acceptance:** same source record cannot create duplicate canonical
detection.

### DATA-005 --- FIRMS replay fixture

**Priority:** P0\
**Status:** READY\
**Dependencies:** DATA-003\
**Objective:** freeze a small captured fixture for deterministic
development.\
**Acceptance:** replay produces same detection manifest.

### DATA-006 --- Source availability state

**Priority:** P0\
**Status:** LOCKED\
**Dependencies:** DB-005\
**Acceptance:** failure vs empty vs unavailable are distinct.

------------------------------------------------------------------------

## Geospatial/event

### GEO-001 --- CRS utility boundary

**Priority:** P0\
**Status:** LOCKED\
**Dependencies:** BE-002\
**Acceptance:** canonical API/storage CRS rules documented and tested.

### GEO-002 --- Safe distance service

**Priority:** P0\
**Status:** LOCKED\
**Dependencies:** GEO-001\
**Acceptance:** geodesic/projected calculations are tested; no
degree-Euclidean meters.

### GEO-003 --- Event formation interface

**Priority:** P0\
**Status:** PROVISIONAL\
**Dependencies:** DB-008, GEO-001\
**Acceptance:** algorithm interface accepts explicit configuration and
as-of time; no threshold defaults.

### GEO-004 --- Event formation implementation

**Priority:** P0\
**Status:** BLOCKED on scientific configuration\
**Dependencies:** GEO-003, DATA-005\
**Acceptance:** deterministic event membership once configuration is
frozen.

### GEO-005 --- Event provenance

**Priority:** P0\
**Status:** READY\
**Dependencies:** GEO-003, DB-008\
**Acceptance:** every event links to input run/config/version.

### GEO-006 --- Persistent-source abstraction

**Priority:** P1\
**Status:** PROVISIONAL\
**Dependencies:** GEO-004\
**Acceptance:** source identity separate from event identity.

### GEO-007 --- Persistence experiment harness

**Priority:** P1\
**Status:** OPEN QUESTION\
**Dependencies:** GEO-006, DATA-001\
**Acceptance:** candidate definitions can be compared without changing
production semantics.

------------------------------------------------------------------------

## Context

### CTX-001 --- Facility canonical schema

**Priority:** P0\
**Status:** READY\
**Dependencies:** DB-010\
**Acceptance:** facility geometry/source provenance is explicit.

### CTX-002 --- OSM/Geofabrik ingestion fixture

**Priority:** P0\
**Status:** READY\
**Dependencies:** CTX-001\
**Acceptance:** sample data normalizes into facilities.

### CTX-003 --- OSM bulk ingestion path

**Priority:** P1\
**Status:** CONDITIONAL\
**Dependencies:** CTX-002, DATA-001\
**Acceptance:** bounded study area can be loaded without per-event
Overpass dependency.

### CTX-004 --- Event-context spatial enrichment

**Priority:** P0\
**Status:** CONDITIONAL\
**Dependencies:** GEO-005, CTX-001, GEO-002\
**Acceptance:** distances and context relations persist; no attribution
claim.

### CTX-005 --- OSM missingness model

**Priority:** P0\
**Status:** LOCKED\
**Dependencies:** CTX-004\
**Acceptance:** not-found is not stored as absent.

### LC-001 --- WorldCover adapter

**Priority:** P1\
**Status:** READY as adapter\
**Dependencies:** DB-004, source registry\
**Acceptance:** version/acquisition/CRS/nodata/provenance stored.

### LC-002 --- WorldCover sampling

**Priority:** P1\
**Status:** CONDITIONAL\
**Dependencies:** LC-001, GEO-001\
**Acceptance:** reproducible sampling; no hard industrial/wildfire
routing.

### LC-003 --- Dynamic World adapter

**Priority:** P2\
**Status:** OPTIONAL\
**Dependencies:** LC-001\
**Acceptance:** temporal provenance and probability semantics preserved.

------------------------------------------------------------------------

## Satellite

### SAT-001 --- Satellite catalog interface

**Priority:** P1\
**Status:** READY\
**Dependencies:** DB-005\
**Acceptance:** asset discovery interface independent of provider.

### SAT-002 --- Satellite availability state machine

**Priority:** P1\
**Status:** LOCKED\
**Dependencies:** SAT-001\
**Acceptance:** all states represented; unavailable does not become
negative.

### SAT-003 --- Sentinel-2 catalog adapter

**Priority:** P1\
**Status:** CONDITIONAL\
**Dependencies:** SAT-002, DATA-001\
**Acceptance:** asset metadata and suitability state captured.

### SAT-004 --- Optional satellite retrieval

**Priority:** P2\
**Status:** BLOCKED on operational feasibility\
**Dependencies:** SAT-003\
**Acceptance:** retrieval is optional and failure-safe.

### SAT-005 --- Satellite availability bias audit

**Priority:** P1\
**Status:** REQUIRED before satellite features enter ML\
**Dependencies:** SAT-003, dataset framework\
**Acceptance:** availability is analyzed independently from class.

------------------------------------------------------------------------

## Reference data

### DATA-007 --- Reference source registry

**Priority:** P0\
**Status:** READY\
**Dependencies:** DB-011\
**Acceptance:** source roles distinguish
observation/reference/corroboration.

### DATA-008 --- Reference evidence ingestion

**Priority:** P0\
**Status:** READY framework\
**Dependencies:** DATA-007\
**Acceptance:** evidence timestamps/provenance persist.

### DATA-009 --- Annotation workflow

**Priority:** P0\
**Status:** CONDITIONAL\
**Dependencies:** DATA-008\
**Acceptance:** positive/negative/unresolved supported.

### DATA-010 --- Adjudication workflow

**Priority:** P1\
**Status:** CONDITIONAL\
**Dependencies:** DATA-009\
**Acceptance:** disagreements are preserved, not overwritten.

### DATA-011 --- Ground-truth feasibility analysis

**Priority:** P0\
**Status:** OPEN QUESTION\
**Dependencies:** DATA-009, DATA-001\
**Acceptance:** quantify usable reference events by supported class.

### DATA-012 --- Reference-source leakage audit

**Priority:** P0\
**Status:** REQUIRED\
**Dependencies:** DATA-011\
**Acceptance:** no reference source used as both label generator and
feature without explicit separation.

------------------------------------------------------------------------

## Dataset/feature

### DATASET-001 --- Dataset manifest builder

**Priority:** P0\
**Status:** READY\
**Dependencies:** DB-012\
**Acceptance:** deterministic membership manifest and hash.

### DATASET-002 --- Split assignment service

**Priority:** P0\
**Status:** BLOCKED on geography/ground truth\
**Dependencies:** DATASET-001\
**Acceptance:** grouped/spatial/temporal rules implemented after
decision freeze.

### DATASET-003 --- Showcase isolation

**Priority:** P0\
**Status:** READY\
**Dependencies:** DATASET-001\
**Acceptance:** showcase cases cannot silently enter benchmark.

### FEAT-001 --- Feature registry

**Priority:** P1\
**Status:** READY\
**Dependencies:** DB-012\
**Acceptance:** every feature has
definition/source/unit/as-of/missingness.

### FEAT-002 --- Feature availability validator

**Priority:** P1\
**Status:** READY\
**Dependencies:** FEAT-001\
**Acceptance:** feature incompatible with inference mode is rejected.

### FEAT-003 --- Leakage audit framework

**Priority:** P0\
**Status:** REQUIRED\
**Dependencies:** FEAT-002, DATASET-002\
**Acceptance:** future/reference leakage tests execute automatically.

### FEAT-004 --- Baseline feature set

**Priority:** P1\
**Status:** CONDITIONAL\
**Dependencies:** FEAT-003, frozen benchmark\
**Acceptance:** only approved features materialized.

------------------------------------------------------------------------

## ML/evaluation

### ML-001 --- Evaluation harness

**Priority:** P0\
**Status:** READY framework\
**Dependencies:** DATASET-002, FEAT-003\
**Acceptance:** frozen split and metric computation are recorded.

### ML-002 --- B0 prior baseline

**Priority:** P1\
**Status:** BLOCKED on labels only\
**Dependencies:** ML-001\
**Acceptance:** class-prior performance reported.

### ML-003 --- B1 detection-quality baseline

**Priority:** P1\
**Status:** BLOCKED on labels\
**Dependencies:** ML-002\
**Acceptance:** explicitly labeled diagnostic baseline.

### ML-004 --- B2 deterministic contextual baseline

**Priority:** P1\
**Status:** BLOCKED on scientific rules\
**Dependencies:** ML-003, GEO-007, CTX-004\
**Acceptance:** rule configuration versioned; no invented thresholds.

### ML-005 --- B3 simple statistical model

**Priority:** P1\
**Status:** BLOCKED on labels/features\
**Dependencies:** ML-004\
**Acceptance:** reproducible model artifact and grouped evaluation.

### ML-006 --- B4 tree model

**Priority:** P1\
**Status:** CONDITIONAL\
**Dependencies:** ML-005\
**Acceptance:** tree model is compared against frozen baselines.

### ML-007 --- Ablation matrix

**Priority:** P0\
**Status:** REQUIRED\
**Dependencies:** ML-006\
**Acceptance:** FIRMS-only, temporal, context, land-cover, satellite,
all comparisons are recorded where data exists.

### ML-008 --- Spatial/temporal/source holdout evaluation

**Priority:** P0\
**Status:** REQUIRED\
**Dependencies:** DATASET-002, ML-001\
**Acceptance:** final benchmark prevents repeated-event/source leakage.

### ML-009 --- Model artifact registry

**Priority:** P1\
**Status:** READY\
**Dependencies:** DB-020 equivalent\
**Acceptance:** model is fully reproducible from stored metadata.

------------------------------------------------------------------------

## Calibration/abstention

### CAL-001 --- Calibration interface

**Priority:** P1\
**Status:** READY framework\
**Dependencies:** ML-005\
**Acceptance:** fitting dataset is explicit.

### CAL-002 --- Calibration experiment

**Priority:** P1\
**Status:** BLOCKED on model/labels\
**Dependencies:** CAL-001\
**Acceptance:** chosen method justified by validation.

### ABS-001 --- Abstention interface

**Priority:** P1\
**Status:** READY\
**Dependencies:** CAL-001, evidence availability\
**Acceptance:** abstention reason is explicit.

### ABS-002 --- Abstention evaluation

**Priority:** P1\
**Status:** BLOCKED on calibration/labels\
**Dependencies:** ABS-001\
**Acceptance:** coverage/selective risk reported.

------------------------------------------------------------------------

## Evidence/intelligence

### EVID-001 --- Evidence schema

**Priority:** P0\
**Status:** READY\
**Dependencies:** DB-023\
**Acceptance:** source/derivation/version/provenance fields exist.

### EVID-002 --- Observation evidence builder

**Priority:** P0\
**Status:** READY\
**Dependencies:** DATA-005, EVID-001\
**Acceptance:** deterministic evidence from stored observations.

### EVID-003 --- Context evidence builder

**Priority:** P0\
**Status:** CONDITIONAL\
**Dependencies:** CTX-004, EVID-001\
**Acceptance:** proximity evidence never becomes attribution proof.

### EVID-004 --- Persistence evidence builder

**Priority:** P1\
**Status:** CONDITIONAL\
**Dependencies:** GEO-006\
**Acceptance:** observed persistence wording/semantics preserved.

### EVID-005 --- Satellite evidence builder

**Priority:** P1\
**Status:** CONDITIONAL\
**Dependencies:** SAT-002\
**Acceptance:** availability and quality state included.

### EVID-006 --- Evidence completeness calculator

**Priority:** P1\
**Status:** PROVISIONAL\
**Dependencies:** EVID-002--005\
**Acceptance:** missingness is explicit; no fabricated evidence.

### INT-001 --- Intelligence result assembler

**Priority:** P0\
**Status:** CONDITIONAL\
**Dependencies:** prediction/evidence contracts\
**Acceptance:** orthogonal output object produced.

------------------------------------------------------------------------

## API/GIS/jobs

### API-001 through API-015

Implement in the API order defined in Section 20. Each route must: -
validate; - authorize; - call service; - serialize typed result; -
enforce bounded work; - return predictable errors.

### WORK-001 --- Job abstraction

**Priority:** P1\
**Status:** READY\
**Dependencies:** DB-014\
**Acceptance:** job state machine works synchronously.

### WORK-002 --- Redis queue

**Priority:** P1\
**Status:** CONDITIONAL\
**Dependencies:** WORK-001\
**Acceptance:** queue is transient; DB remains authoritative.

### WORK-003 --- Worker runner

**Priority:** P1\
**Status:** CONDITIONAL\
**Dependencies:** WORK-002\
**Acceptance:** retry/idempotency behavior tested.

### GIS-001 --- GeoJSON serializer

**Priority:** P0\
**Status:** READY\
**Dependencies:** GEO-001, API\
**Acceptance:** no CRS/precision ambiguity.

### GIS-002 --- Event layer

**Priority:** P0\
**Status:** CONDITIONAL\
**Dependencies:** GIS-001, API-006\
**Acceptance:** bounded map queries render event geometry.

### GIS-003 --- Detection layer

**Priority:** P0\
**Status:** CONDITIONAL\
**Dependencies:** API-005\
**Acceptance:** raw observations can be visualized without overclaiming
precision.

### GIS-004 --- Context layers

**Priority:** P0\
**Status:** CONDITIONAL\
**Dependencies:** CTX/LC\
**Acceptance:** context layers are visually distinct from predictions.

### GIS-005 --- Intelligence layer

**Priority:** P0\
**Status:** CONDITIONAL\
**Dependencies:** INT-001\
**Acceptance:** result links to evidence and uncertainty.

------------------------------------------------------------------------

## Operations/demo

### OPS-001 --- Secret handling

**Priority:** P0\
**Status:** READY\
**Dependencies:** BE-003\
**Acceptance:** secrets never enter Git/browser/logs.

### OPS-002 --- Health/readiness

**Priority:** P1\
**Status:** READY\
**Dependencies:** API/DB\
**Acceptance:** dependency failures are distinguishable.

### OPS-003 --- Performance harness

**Priority:** P1\
**Status:** READY framework\
**Dependencies:** pipeline stages\
**Acceptance:** timing boundaries are measured separately.

### DEMO-001 --- Replay bundle

**Priority:** P0\
**Status:** READY framework\
**Dependencies:** DATA-005, context/reference fixtures\
**Acceptance:** no live API required.

### DEMO-002 --- Deterministic seed

**Priority:** P0\
**Status:** CONDITIONAL\
**Dependencies:** DEMO-001\
**Acceptance:** seed/reset is repeatable.

### DEMO-003 --- Full demo replay

**Priority:** P0\
**Status:** BLOCKED until intelligence path works\
**Dependencies:** INT-001, GIS-005\
**Acceptance:** complete judge-facing flow runs offline.

### HARD-001 --- Final leakage audit

**Priority:** P0\
**Status:** REQUIRED\
**Dependencies:** all dataset/features/ML\
**Acceptance:** no unresolved leakage finding.

### HARD-002 --- Final provenance audit

**Priority:** P0\
**Status:** REQUIRED\
**Dependencies:** all pipeline stages\
**Acceptance:** every result traces to source/config/code/model.

### HARD-003 --- Final performance audit

**Priority:** P1\
**Status:** REQUIRED before performance claims\
**Dependencies:** working pipeline\
**Acceptance:** measured numbers only.

------------------------------------------------------------------------

# 32. AI Coding Agent Execution Protocol

## 32.1 Before every task

Agent must:

1.  read the task;
2.  read relevant architecture/specification sections;
3.  inspect existing code;
4.  inspect current progress tracker;
5.  identify dependencies;
6.  identify protected/open decisions;
7.  confirm allowed files.

## 32.2 During implementation

Agent must: - make the smallest change; - add tests with the change; -
preserve provenance; - preserve uncertainty; - avoid unrelated
refactors; - avoid new dependencies unless justified.

## 32.3 After implementation

Run: 1. targeted tests; 2. integration tests relevant to unit; 3. Ruff;
4. type checker for affected critical modules; 5. acceptance checks; 6.
architecture-invariant check.

Then update progress tracker.

## 32.4 Agent must STOP when

-   a scientific threshold is missing;
-   taxonomy is ambiguous;
-   ground-truth label policy is unclear;
-   attribution semantics are unclear;
-   CRS behavior is unclear;
-   external API contract is unknown;
-   an existing architecture decision would need to change;
-   test and specification conflict;
-   an implementation requires inventing a fallback.

The agent must report:

``` text
BLOCKED
Reason
Relevant document
Decision required
Safe options
```

It must not guess.

------------------------------------------------------------------------

# 33. AI-Agent Forbidden Actions

The agent MUST NOT:

-   invent scientific thresholds;
-   invent ground-truth labels;
-   treat FIRMS as ground truth;
-   treat OSM as ground truth;
-   treat facility proximity as attribution;
-   treat satellite availability as a class signal without audit;
-   use future observations in a restricted inference mode;
-   use test data for calibration;
-   change benchmark splits after seeing results;
-   turn unresolved into negative;
-   turn missing into absent;
-   turn unavailable satellite into negative evidence;
-   add a source without source-role approval;
-   add Kafka;
-   introduce microservices;
-   add deep learning before baseline gate;
-   make an LLM generate factual evidence;
-   expose credentials;
-   rewrite architecture to fix one bug;
-   modify unrelated modules;
-   claim target metrics as achieved.

------------------------------------------------------------------------

# 34. Risk Register

  ----------------------------------------------------------------------------------------------------------------------------
  Risk             Probability   Impact     Detection       Mitigation               Fallback                   Owner
  ---------------- ------------- ---------- --------------- ------------------------ -------------------------- --------------
  Ground-truth     High          Critical   DATA-011        Narrow supported         Demo-only/reference-only   Data/ML
  scarcity                                                  taxonomy; tiered         mode                       
                                                            reference                                           

  FIRMS ambiguity  High          Critical   Error analysis  Event/context/evidence   Abstain                    ML
                                                            separation                                          

  Spatial          High          Critical   GEO tests       Separate geometries      Context-only output        Geo
  attribution                                                                                                   
  uncertainty                                                                                                   

  OSM              High          High       Coverage audit  Explicit missingness     No-context state           Data
  incompleteness                                                                                                

  Satellite        High          Medium     SAT audit       Optional branch          Continue without satellite Satellite
  unavailable                                                                                                   

  Class imbalance  Likely        High       Dataset profile Prior baseline,          Narrow claims              ML
                                                            appropriate metrics                                 

  Label leakage    High          Critical   Leakage suite   Dataset/source isolation Block benchmark            ML

  Temporal leakage High          Critical   as-of audit     Time-aware               Retrospective-only mode    ML
                                                            features/splits                                     

  Spatial leakage  High          Critical   group split     Geographic holdout       Narrow benchmark           ML
                                            audit                                                               

  Model            Medium        High       calibration     Calibration + abstention Unknown                    ML
  overconfidence                                                                                                

  Context shortcut High          High       ablations       Context removal tests    Reduce context features    ML
  learning                                                                                                      

  External API     High          High       source health   cache/replay/fallback    Offline replay             Platform
  outage                                                                                                        

  Processing       Medium        High       performance     batch/index/cache        offline batch              Platform
  latency                                   harness                                                             

  Large data       Medium        Medium     profiling       bounded                  reduced geography          Data
  volume                                                    ingestion/indexing                                  

  AI code defects  High          High       tests/review    atomic tasks             rollback task              All

  Scope creep      High          High       roadmap review  P0/P1/P2 gate            defer feature              Product

  Demo failure     Medium        Critical   DEMO-003        offline deterministic    replay-only demo           All
                                                            bundle                                              

  Reference source Medium        Critical   source-family   label/feature separation exclude source             ML
  correlation                               audit                                                               

  External version Medium        High       snapshot        capture version/hash     freeze replay              Data
  drift                                     metadata                                                            

  Evidence         Medium        Critical   evidence tests  prediction-independent   suppress evidence          Intelligence
  circularity                                               derivation                                          
  ----------------------------------------------------------------------------------------------------------------------------

------------------------------------------------------------------------

# 35. Definition of Done

## Unit-level

A unit is complete only if: - implementation matches contract; - tests
pass; - external failures are handled; - provenance is preserved; -
uncertainty/missingness is preserved; - docs/context are updated; -
progress tracker is updated; - lint/type checks pass; - no invariant is
violated; - no open question was silently resolved; - acceptance
criteria are demonstrated.

## System-level

The MVP is done only when: - FIRMS data can be ingested reproducibly; -
raw observations are traceable; - events are reproducibly formed under
frozen configuration; - candidate persistent sources are represented; -
industrial/context and land-cover evidence can be attached; - satellite
availability is explicit; - valid reference data is versioned; -
benchmark isolation is verified; - baselines are measured; - ML, if
included, beats a predeclared meaningful baseline; - calibration is
valid if probabilities are exposed; - abstention is evaluated; -
evidence is deterministic; - intelligence is uncertainty-aware; - REST
APIs work; - GIS layers work; - offline replay works; - external
failures are visible; - no unsupported claim is made.

------------------------------------------------------------------------

# 36. Exact First 10 Coding Tasks

These are deliberately safe: none requires inventing scientific values.

## 1. BE-001 --- Repository skeleton

**Why first:** everything else depends on clean boundaries.\
**Expected files:** repository directories, root config placeholders.\
**Expected output:** importable empty architecture.\
**Tests:** import smoke.\
**STOP:** if existing repository structure conflicts with the approved
architecture, report before rewriting.

## 2. BE-002 --- Python/tooling contract

**Why first:** establishes reproducible development.\
**Expected files:** `pyproject.toml`, test/lint/type configuration.\
**Output:** reproducible toolchain.\
**Tests:** lint/test/type checks.\
**STOP:** if dependency constraints require a different Python version.

## 3. DB-001 --- PostGIS Compose service

**Why first:** database is the system of record.\
**Expected files:** `docker-compose.yml` additions, DB config.\
**Output:** local PostGIS.\
**Tests:** connection + extension.\
**STOP:** if current infrastructure already contains a conflicting DB
service.

## 4. DB-002 --- Migration framework

**Why first:** all persistent contracts must be migration-controlled.\
**Expected files:** migration configuration and initial structure.\
**Output:** repeatable schema migration execution.\
**Tests:** migration smoke.\
**STOP:** if existing migration framework must be preserved.

## 5. BE-003 --- Environment/config loader

**Why first:** source credentials and operational configuration need a
safe boundary.\
**Expected files:** `packages/config/`.\
**Output:** typed config loading.\
**Tests:** valid/missing/secret cases.\
**STOP:** if an operational secret name is unknown; do not invent it.

## 6. BE-004 --- Scientific configuration contract

**Why first:** prevents agents from hard-coding scientific assumptions
later.\
**Expected files:** scientific config schema and registry interface.\
**Output:** versioned config object with explicit incomplete state.\
**Tests:** missing required scientific value fails.\
**STOP:** if asked to populate unresolved scientific values.

## 7. DB-003 --- Scientific contracts migration

**Why first:** scientific decisions must be versionable before pipeline
code.\
**Expected files:** migration 001.\
**Output:** authoritative scientific contract storage.\
**Tests:** create/read/version uniqueness.\
**STOP:** no default scientific values.

## 8. DB-004 --- Source registry migration

**Why first:** all external sources need explicit semantics before
adapters.\
**Expected files:** migration 002, source-role enum.\
**Output:** source registry.\
**Tests:** role validation and uniqueness.\
**STOP:** if a source role is ambiguous.

## 9. DATA-002 --- FIRMS canonical parser using fixture only

**Why first:** first real domain transformation without live API
dependence.\
**Expected files:** `packages/sources/firms/`, fixtures/tests.\
**Output:** validated canonical FIRMS observation records.\
**Tests:** valid/malformed/optional-field fixtures.\
**STOP:** if a source field's semantics cannot be established from
authoritative documentation.

## 10. DATA-005 --- FIRMS offline replay fixture

**Why first:** establishes deterministic development before live API
work.\
**Expected files:** replay fixture + manifest + replay test.\
**Output:** same input → same canonical output.\
**Tests:** hash/output determinism.\
**STOP:** if fixture provenance cannot be preserved.

------------------------------------------------------------------------

# 37. Immediate Execution Sequence

The actual execution order for the team/agents is:

### Phase 0 --- Foundation

`BE-001 → BE-002 → DB-001 → DB-002 → BE-003 → BE-005 → BE-006`

### Phase 1 --- Scientific/source contracts

`BE-004 → DB-003 → DB-004 → DB-005 → DB-006`

### Phase 2 --- FIRMS data spine

`DATA-002 → DATA-003 → DATA-004 → DATA-005 → DATA-006 → DB-007`

### Phase 3 --- Geospatial/event framework

`GEO-001 → GEO-002 → GEO-003 → GEO-005`

Run `DATA-001` in parallel as the first feasibility decision.

### Phase 4 --- Context/reference foundations

`CTX-001 → CTX-002 → DATA-007 → DATA-008 → DB-010 → DB-011`

### Phase 5 --- Scientific gates

`DATA-009 → DATA-010 → DATA-011 → DATA-012` and: `GEO-007`

### Phase 6 --- Dataset/feature framework

`DATASET-001 → DATASET-003 → FEAT-001 → FEAT-002 → FEAT-003`

### Phase 7 --- Baseline

Only after geography, labels, taxonomy and split are frozen:
`DATASET-002 → FEAT-004 → ML-001 → ML-002 → ML-003 → ML-004`

### Phase 8 --- ML

If justified: `ML-005 → ML-006 → ML-007 → ML-008 → ML-009`

### Phase 9 --- Calibration/abstention

`CAL-001 → CAL-002 → ABS-001 → ABS-002`

### Phase 10 --- Evidence/intelligence

`EVID-001 → EVID-002 → EVID-003 → EVID-004 → EVID-005 → EVID-006 → INT-001`

### Phase 11 --- API/jobs/GIS

`API-001 → API-002 → API-003 → API-004 → API-005 → API-006 → API-007 → API-008 → API-009 → API-010 → API-011 → GIS-001 → GIS-002 → GIS-003 → GIS-004 → GIS-005`

Then: `WORK-001 → WORK-002 → WORK-003`

### Phase 12 --- Offline demo/hardening

`DEMO-001 → DEMO-002 → DEMO-003 → HARD-001 → HARD-002 → HARD-003`

------------------------------------------------------------------------

# 38. Readiness Checklist

  ----------------------------------------------------------------------------------
  Area                    Status                  Reason
  ----------------------- ----------------------- ----------------------------------
  Architecture            PASS                    Core architecture is locked; no
                                                  Kafka/microservices

  Database                PASS                    Migration order and entity
                                                  contracts are defined

  Source registry         PASS                    Source roles and provenance are
                                                  operationalized

  FIRMS                   CONDITIONAL             Adapter can be built; live limits
                                                  must be verified, not invented

  Geospatial              CONDITIONAL             CRS rules are locked; final
                                                  attribution metric remains open

  Event semantics         CONDITIONAL             Interface is buildable; scientific
                                                  thresholds remain open

  Persistent-source       CONDITIONAL             Abstraction is buildable; final
  semantics                                       persistence rule remains open

  Ground truth            FAIL for ML             Reference registry must still be
                                                  constructed

  Dataset isolation       CONDITIONAL             Infrastructure can be built; final
                                                  split waits for geography/labels

  Feature contracts       PASS                    Registry/as-of/leakage framework
                                                  can be built now

  ML                      FAIL for final training Depends on valid labels, taxonomy,
                                                  split, features

  Calibration             CONDITIONAL             Interface now; final method after
                                                  model/data

  Abstention              CONDITIONAL             Interface now; threshold after
                                                  evaluation

  Evidence                PASS for framework      Deterministic evidence
                                                  architecture is defined

  API                     PASS for foundation     Intelligence endpoints depend on
                                                  pipeline outputs

  Jobs                    CONDITIONAL             Sync first; Redis worker after
                                                  domain path

  GIS                     CONDITIONAL             Backend map layers can begin;
                                                  final intelligence layer waits for
                                                  result contract

  Offline demo            CONDITIONAL             Replay framework can begin; full
                                                  demo waits for intelligence path

  Testing                 PASS                    Test pyramid and minimum coverage
                                                  are defined

  Reproducibility         PASS                    Run/config/dataset/feature/model
                                                  lineage is specified

  AI-agent safety         PASS                    Atomic tasks + stop rules are
                                                  defined

  Scope                   PASS                    P0/P1/P2 boundaries are explicit
  ----------------------------------------------------------------------------------

**Final readiness statement:**

> **Implementation-ready except for the scientific/data decisions
> explicitly marked OPEN/BLOCKED. Infrastructure and contract work can
> begin immediately. No agent may cross those scientific gates by
> guessing.**

------------------------------------------------------------------------

# 39. V2 Corrections Operationalized

  ----------------------------------------------------------------------------------------------------------------------------
  Previous       Execution design                   Reason              Review issue      Data-source      Implementation
  design                                                                addressed         issue addressed  impact
  -------------- ---------------------------------- ------------------- ----------------- ---------------- -------------------
  World Bank     Reference/corroboration role       Satellite-derived   Ground-truth      Source stack     Source registry +
  flare tracker                                     reference is not    weakness          overclaimed      reference evidence
  treated as                                        automatically                         ground truth     
  ground truth                                      independent truth                                      

  Known flare    Known persistent flare reference   Persistent flare is FIRMS/reference   World Bank       Label pipeline
  auto-tagged                                       not equivalent to   misuse            recommendation   change
  non-alert                                         negative                                               

  VNF called     Candidate feature/reference source Must be empirically Scientific        VNF              Ablation + leakage
  strongest                                         validated           assumption        recommendation   gate
  signal                                                                                                   

  MCD64A1        Burn corroboration with uncertain  No burn detection   Scientific        MCD64A1          Evidence-state enum
  confirms       state                              is not proof of no  overclaim         recommendation   
  wildfire                                          burn                                                   

  WorldCover     Land-cover feature only            Built-up is not     Shortcut risk     WorldCover       Feature semantics
  built-up =                                        industrial truth                      recommendation   
  industrial                                                                                               

  Hard           Soft/contextual feature            Avoid false hard    Geospatial/ML     WorldCover       No hard router
  land-cover                                        priors              risk              recommendation   
  routing                                                                                                  

  Earth Engine   Optional prototyping mechanism     Avoid hidden        Architecture      GEE              Adapter boundary
  as central                                        production          complexity        recommendation   
  processing                                        dependency                                             

  Generic        Separate                           Prevent semantic    Calibration risk  N/A              Prediction/result
  confidence     probability/evidence/uncertainty   collapse                                               schema

  Evidence       Prediction-independent evidence    Prevent circular    Evidence          N/A              Evidence engine
  selected after derivation                         explanations        vulnerability                      
  prediction                                                                                               

  No explicit    Pipeline runs                      Reproducibility     Missing backend   N/A              DB + pipeline
  run lineage                                                           component                          

  Feature        Feature definitions + feature      Leakage prevention  Feature leakage   Temporal source  ML/data layer
  version only   sets + as-of                                                             differences      

  OSM per-event  Bulk/local context                 Avoid external      Performance       OSM access       Context ingestion
  query                                             latency/rate                                           
                                                    bottleneck                                             

  Live APIs      Offline replay                     External outage     Demo failure      All external     Replay bundle
  required for                                      cannot kill demo                      sources          
  demo                                                                                                     

  Scientific     Required configuration; missing    Prevent AI-agent    AI implementation N/A              Config layer
  values as      values fail                        invention           risk                               
  configurable                                                                                             
  defaults                                                                                                 

  P0 broadly     P0 restricted to core path         Preserve execution  Scope creep       N/A              Roadmap
  assigned                                          focus                                                  

  Satellite      Optional availability state        Availability bias   Satellite risk    Sentinel         Satellite state
  feature                                           and outages                           availability     machine
  assumed                                                                                                  
  ----------------------------------------------------------------------------------------------------------------------------

------------------------------------------------------------------------

# 40. Absolute Invariants

1.  FIRMS detection is an observation, not ground truth.
2.  OSM is context, not ground truth.
3.  Satellite-derived reference data is not automatically independent
    ground truth.
4.  Facility proximity is not attribution.
5.  Detection, event, candidate persistent source, and facility
    geometries remain separate.
6.  Source semantics are never overwritten downstream.
7.  Raw observations remain immutable.
8.  Missing is not absent.
9.  Unavailable is not negative.
10. Unresolved is not negative.
11. Future information cannot enter an inference mode that disallows it.
12. Test data cannot fit calibration.
13. Benchmark splits cannot be changed to improve results.
14. Evidence is deterministic and traceable.
15. LLMs cannot create factual evidence.
16. Scientific configuration is versioned.
17. Dataset versions are frozen and hashed.
18. Feature sets are versioned.
19. Model versions are versioned.
20. Pipeline runs are versioned.
21. Redis is not authoritative.
22. Offline replay remains available.
23. No Kafka.
24. No premature microservices.
25. No advanced ML before baseline validation.
26. No unsupported performance claims.
27. The simplest model that wins the frozen benchmark is preferred.

------------------------------------------------------------------------

# 41. Source-of-Truth Files to Keep Synchronized

The coding agent must treat these as living context:

1.  `project-overview.md`
2.  `architecture.md`
3.  `code-standards.md`
4.  `ai-workflow-rules.md`
5.  `progress-tracker.md`
6.  `SIH26162_IMPLEMENTATION_PLAN_V2.md`
7.  `SIH26162_Data_Source_Stack.docx`
8.  `SIH26162_IMPLEMENTATION_EXECUTION_PLAN.md`

If implementation changes: - architecture; - storage; - API; -
scientific semantics; - feature behavior; - scope;

the corresponding source-of-truth document must be updated before the
change is considered complete.

------------------------------------------------------------------------

# 42. Final Operating Command for an AI Coding Agent

When handed this document, the agent should operate as follows:

``` text
EXECUTE TASK-<ID>

1. Read this execution plan.
2. Read the referenced canonical documents.
3. Inspect repository state.
4. Verify dependencies.
5. Identify scientific/open decisions.
6. If the task is fully specified:
      implement only that task.
7. Add required tests.
8. Run targeted tests.
9. Run lint/type checks.
10. Verify acceptance criteria.
11. Verify invariants.
12. Update progress tracker.
13. Report:
      - files changed
      - DB changes
      - tests
      - acceptance results
      - assumptions
      - remaining risks
14. STOP.
```

The agent is **not authorized to continue automatically into the next
task** unless explicitly instructed.

The agent is **not authorized to resolve OPEN QUESTION items**.

The agent is **not authorized to turn a recommendation into a fact**.

The agent is **not authorized to change the benchmark because the model
performs poorly**.

The agent is **not authorized to make the system appear more certain
than the evidence supports**.

------------------------------------------------------------------------

# 43. Final Objective

The implementation is successful when the repository can demonstrate:

``` text
FIRMS observation
      ↓
canonical detection
      ↓
reproducible event
      ↓
observed persistence
      ↓
industrial/land context
      ↓
versioned features
      ↓
defensible baseline
      ↓
validated ML if justified
      ↓
calibrated probability
      ↓
abstention when evidence is insufficient
      ↓
deterministic evidence
      ↓
uncertainty-aware intelligence
      ↓
PostGIS/GIS visualization
      ↓
offline reproducible replay
```

The system should answer:

``` text
WHAT happened?
WHERE?
WHEN?
WHAT is it likely to represent?
WHAT contextual evidence exists?
HOW persistent is the observed pattern?
WHAT evidence supports the result?
WHAT is unknown?
HOW reproducible is the result?
```

The implementation must never pretend to answer a stronger question than
the data, reference evidence, and evaluation protocol support.

**The winning architecture is not the largest one. It is the smallest
system that produces a hard-to-fake intelligence claim, proves it with
traceable evidence, exposes uncertainty, and directly satisfies
SIH26162.**
