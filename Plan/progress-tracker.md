# SIH26162 --- Progress Tracker

## Current Phase

-   **Phase:** Phase 3 — Scientific Derivation (EVENT → SOURCE → CONTEXT → INTELLIGENCE)
-   **Status:** Complete
-   **Implementation status:** Complete (Geospatial Core, Component 1 EVENT, Component 2 SOURCE, Component 3 CONTEXT, and Component 4 INTELLIGENCE completed and verified across 203 automated tests)
-   **UI:** Intentionally deferred

------------------------------------------------------------------------

# Current Goal

Finish the scientific and engineering contract before substantial
implementation.

The immediate objective is to lock:

1.  official requirements;
2.  product ontology;
3.  event/source semantics;
4.  demonstration geography;
5.  ground-truth strategy;
6.  evaluation protocol;
7.  geospatial error definition;
8.  data acquisition path;
9.  baseline implementation sequence.

------------------------------------------------------------------------

# Completed

## Strategic understanding

-   [x] Official SIH26162 problem reviewed.
-   [x] Official deliverables identified.
-   [x] Theme corrected to **Miscellaneous**.
-   [x] Team conceptual architecture reviewed.
-   [x] Team must-do/must-not-do list reviewed.
-   [x] Team target metrics reviewed.
-   [x] Team bottlenecks reviewed.
-   [x] Six Thinking Hats applied.
-   [x] External resource strategy established.

## Product

-   [x] Core product thesis defined.
-   [x] Primary user / beneficiary / decision-maker distinction defined.
-   [x] Evidence-first output defined.
-   [x] Detection → Event → Persistent Source hierarchy defined.
-   [x] Abstention defined as a valid outcome.
-   [x] Product scope defined.
-   [x] Official MUST requirements separated from strategic
    enhancements.
-   [x] Flat taxonomy replaced by orthogonal ontology.

## Architecture

-   [x] Recommended stack selected.
-   [x] System boundaries defined.
-   [x] Storage model defined.
-   [x] Canonical data contracts defined.
-   [x] API boundary defined.
-   [x] ML sequence defined.
-   [x] Evidence engine defined.
-   [x] Deployment strategy defined.
-   [x] Architecture invariants defined.
-   [x] Context-ablation requirement added.
-   [x] Satellite availability treated as per-event evidence, not
    universal prerequisite.

## Engineering

-   [x] Python/TypeScript standards defined.
-   [x] Geospatial precision rules defined.
-   [x] Provenance rules defined.
-   [x] Leakage prevention rules defined.
-   [x] Testing requirements defined.
-   [x] AI/LLM usage policy defined.
-   [x] Ground-truth provenance rules defined.
-   [x] BE-001 Repository skeleton established (modular monolith boundaries, smoke test).
-   [x] BE-002 Python/tooling contract established (Python 3.11+, Ruff, Pytest, Mypy, uv).
-   [x] SCHEMAS Canonical domain schema package established (Detection, Event, Source, Context, Intelligence in Pydantic).
-   [x] DB-001 PostGIS Compose service established (PostGIS 16-3.4, persistent volume, healthcheck, smoke tests).
-   [x] DB-002 Migration framework established (Alembic 1.14+, dynamic DB URL, baseline migration, test suite, CI).
-   [x] BE-003 Environment/config loader established (packages/config/, Pydantic Settings, secret protection, safe DB URL helpers).
-   [x] BE-005 Error handling & exceptions taxonomy established (packages/errors/, AppError base, ErrorCode enum, cause-preserving chaining).
-   [x] BE-006 Structured logging system established (packages/logging/, StructuredJsonFormatter, secret sanitization, AppError integration).
-   [x] BE-004 Scientific configuration contract established (packages/config/scientific.py, ScientificConfig, explicit incomplete state, SHA-256 fingerprinting).
-   [x] DB-003 Scientific contracts migration established (alembic/versions/0002_scientific_contracts.py, scientific_contracts table, mathematical check constraints).
-   [x] DB-004 Source registry migration established (alembic/versions/0003_source_registry.py, source_registry table, SourceRole enum, relational metadata, integrity constraints).
-   [x] DB-005 Source snapshots migration established (alembic/versions/0004_source_snapshots.py, source_snapshots table, SnapshotAvailabilityState enum, integrity hashes, RESTRICT FK).
-   [x] DB-006 Source records migration established (alembic/versions/0005_source_records.py, source_records table, PostGIS geometry EPSG:4326, composite unique constraint, GiST spatial index, RESTRICT FK).
-   [x] DB-007 Canonical detections migration established (alembic/versions/0006_detections.py, detections table, PostGIS Point geometry EPSG:4326, FRP in MW, temperatures in Kelvin, pixel dimensions in km, RESTRICT FKs).
-   [x] Phase 3 Thermal events persistence migration established (alembic/versions/0007_thermal_events.py, thermal_events and event_detections tables, PostGIS Point centroid & observation footprint, FRP stats in MW, RESTRICT FKs).
-   [x] Phase 3 Geospatial Core established (packages/geospatial/, WGS84 coordinates validation, WKT POINT format/parse, Haversine geodesic physical distance in meters, 3D spherical centroid averaging, bounding envelope).
-   [x] Phase 3 Component 1 EVENT established (packages/events/, deterministic spatiotemporal graph clustering, Event builder, content-addressable event_id, derive_thermal_events service, uncalibrated config enforcement).
-   [x] Phase 3 Component 2 SOURCE established (packages/sources/, longitudinal spatial event association, persistence state classification [PERSISTENT, RECURRING, TRANSIENT, INSUFFICIENT_HISTORY], active calendar days & recurrence ratio metrics, deterministic content-addressable source_id, derive_persistent_sources service).
-   [x] Phase 3 Component 3 CONTEXT established (packages/context/, normalized ContextFeature domain representation, geodesic proximity & containment matching rules, temporal validity evaluation preventing hindsight leakage, ContextProvider abstraction, deterministic content-addressable context_id, ContextEvidence synthesis, derive/enrich service).
-   [x] Phase 3 Component 4 INTELLIGENCE established (packages/intelligence/, orthogonal ontology reasoning engine [phenomenon, context, persistence, attribution], evidence completeness auditing, calibrated confidence, explicit abstention recommendation, deterministic content-addressable intelligence_id, derive_intelligence service).
-   [x] DATA-001 Study-Area Feasibility Harness established (packages/feasibility/, candidate Indian study area definitions [Jamnagar, Singrauli, Angul-Talcher, Punjab], FIRMS feasibility analyzer, Phase 3 derivation analyzer, context & reference feasibility analyzers, multi-region comparative evaluation harness, deterministic ranking, machine-readable JSON & markdown report generator, CLI runner scripts/run_study_area_feasibility.py, 13 comprehensive unit/determinism tests).
-   [x] DATA-002 FIRMS Canonical Parser established (packages/data/firms/, RawFirmsCsvRow validation, VIIRS/MODIS column alias normalization, strict UTC timestamp parsing, coordinate validation in WGS-84, missingness preservation, deterministic raw_hash & detection_id generation, strict and reporting parser APIs, realistic fixture suite, 24 unit/determinism/adversarial tests).
-   [x] DATA-003 FIRMS Raw Capture Adapter established (packages/data/firms/client.py, capture.py, errors.py, schemas.py, authenticated Area & Country APIs, bounded exponential backoff retries with zero test sleep, zero secret leakage, SnapshotAvailabilityState [AVAILABLE, EMPTY_RESULT, FAILED, etc.], cryptographic content_hash & request_fingerprint, 23 unit/adversarial/leakage tests).
-   [x] DATA-004 External Context Data Ingestion established (packages/data/context/, GeoJSON & CSV parser APIs, OpenStreetMap tag classification [POWER, OIL_GAS, MINING, INDUSTRIAL, AGRICULTURAL, etc.], WRI power plants normalizer, polygon bounding box & 3D spherical centroid calculation, explicit missingness preservation, deterministic content-addressable feature_id & raw_hash, 19 unit/determinism/integration tests).
-   [x] DATA-005 Data Quality, Validation & Ingestion Integrity Layer established (packages/data/quality/, duplicate observation detection & partitioning, conflicting space-time observation auditing, temporal span & timezone verification, spatial envelope & Null Island anomaly detection, provenance completeness audit, explainable deterministic quality scoring & tier classification [HIGH_QUALITY, ACCEPTABLE, DEGRADED, REJECTED], CleanedDetectionManifest, 12 unit/determinism/integration tests).
-   [x] ML-001 Machine Learning Readiness / Evaluation Foundation established (packages/schemas/ml.py, packages/config/ml.py, services/ml/features/ [FeatureRegistry, LeakageAuditor], services/ml/training/ [DatasetBuilder, SplitAssignmentService, SplitIntegrityValidator], services/ml/evaluation/ [EvaluationHarness], services/ml/calibration/ [CalibrationManager, AbstentionDecisionEngine], services/ml/readiness.py [MLReadinessAuditor 8-pillar assessment], 323 passing repository tests, zero fabricated labels, zero premature models).

------------------------------------------------------------------------

# In Progress

## 1. Demonstration geography

Choose a bounded Indian study area containing multiple thermal-source
types.

Selection criteria:

-   industrial facilities;
-   oil/gas or petrochemical activity where available;
-   thermal power;
-   mining where available;
-   agricultural land;
-   forest/fire-prone areas;
-   sufficient historical FIRMS detections;
-   feasible reference-event coverage.

**Acceptance:** geography is selected with a written evidence-based
rationale.

------------------------------------------------------------------------

## 2. Ground-truth/reference registry

Build the first reference-event table.

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

**Acceptance:**

-   every label has provenance;
-   Tier A/B/C hierarchy is applied;
-   no proxy label is silently treated as ground truth.

------------------------------------------------------------------------

## 3. FIRMS data spine

Implement:

``` text
FIRMS
→ raw capture
→ validation
→ canonical schema
→ deduplication
→ PostGIS
```

Acceptance:

-   reproducible ingestion;
-   source/product/version retained;
-   acquisition and ingestion timestamps separated;
-   API failures visible;
-   historical query works.

------------------------------------------------------------------------

## 4. Event engine

Implement:

``` text
detections
→ spatio-temporal clustering
→ thermal events
```

Acceptance:

-   detections are traceable to events;
-   clustering parameters are configurable/versioned;
-   event geometry and temporal span are generated.

------------------------------------------------------------------------

## 5. Persistent-source engine

Implement:

``` text
events
→ source association
→ persistence statistics
→ persistent/recurring/transient state
```

Acceptance:

-   persistence is independently measurable;
-   source identity is not confused with event identity.

------------------------------------------------------------------------

## 6. Context pipeline

Implement:

-   OSM/industrial enrichment;
-   land-cover enrichment;
-   satellite catalog/context lookup.

Acceptance:

-   provenance retained;
-   missing context represented explicitly;
-   context never becomes automatic ground truth.

------------------------------------------------------------------------

## 7. Baseline benchmark

Implement:

``` text
FIRMS confidence
→ industrial proximity
→ persistence
→ combined rules
```

Then evaluate against the reference registry.

Acceptance:

-   benchmark split is frozen;
-   event/source leakage is prevented;
-   baseline metrics are recorded.

------------------------------------------------------------------------

## 8. ML benchmark

Only after baseline and labels are sufficient:

``` text
features
→ XGBoost/LightGBM
→ grouped evaluation
→ calibration
→ abstention
```

Acceptance:

-   ML materially improves over baseline;
-   calibration measured;
-   ablation completed;
-   no leakage detected.

------------------------------------------------------------------------

# Next Up

### Gate 1 --- Scientific contract

Before model training, freeze:

-   [ ] final phenomenon ontology;
-   [ ] context ontology;
-   [ ] persistence definition;
-   [ ] attribution definition;
-   [ ] event clustering semantics;
-   [ ] ground-truth label policy;
-   [ ] geographic/temporal benchmark split;
-   [ ] geospatial error metric.

### Gate 2 --- Data feasibility

-   [ ] sample FIRMS data for selected geography;
-   [ ] quantify candidate event volume;
-   [ ] quantify label volume;
-   [ ] quantify class balance;
-   [ ] inspect OSM completeness;
-   [ ] inspect satellite availability/cloud limitations.

### Gate 3 --- Baseline

-   [ ] deterministic baseline;
-   [ ] evaluation;
-   [ ] error analysis.

Only then decide whether advanced ML is justified.

------------------------------------------------------------------------

# Open Questions

These are the only decisions that should block the final ML
specification:

1.  What exact Indian demonstration geography provides sufficient
    diversity and reference evidence?
2.  What minimum number of Tier A/B events is sufficient for the chosen
    taxonomy?
3.  Which phenomenon classes can be supported by real labels rather than
    proxies?
4.  What exact rule defines `persistent` versus `recurring`?
5.  What spatial distance rule is used for contextual proximity?
6.  What exact reference geometry is used for geospatial attribution
    error?
7.  What satellite product is the preferred contextual source for the
    selected geography?
8.  What is the final benchmark time window?
9.  What minimum precision/recall constraints define acceptable
    selective classification?
10. What is the exact demo scenario?

------------------------------------------------------------------------

# Architecture Decisions

## AD-001 --- Official requirement priority

Industrial-fire segregation and GIS storage/visualization are MUST
requirements.

## AD-002 --- Orthogonal ontology

Phenomenon, context, persistence and attribution are separate
dimensions.

## AD-003 --- Evidence-first

Every prediction exposes evidence, uncertainty and provenance.

## AD-004 --- Abstention

Low-evidence cases may return `unknown/uncertain`.

## AD-005 --- Baseline-first

No advanced model before deterministic baselines and a valid benchmark.

## AD-006 --- Context ablation

The contribution of OSM/industrial context must be measured.

## AD-007 --- Satellite availability

Satellite integration is supported, but missing imagery does not
automatically invalidate an event.

## AD-008 --- PostGIS

PostGIS is the primary geospatial store.

## AD-009 --- Redis over Kafka for MVP

Use Redis-backed jobs unless measured workload proves a stronger
requirement.

## AD-010 --- No UI-led development

The intelligence pipeline must be validated before UI optimization.

------------------------------------------------------------------------

# Session Notes

The major specification audit identified four critical conceptual
corrections:

1.  **Theme:** Miscellaneous, not Disaster Management.
2.  **Official requirements:** industrial-fire segregation + GIS
    storage/visualization are MUST.
3.  **Ontology:** phenomenon/context/persistence/attribution must be
    separated.
4.  **Evaluation:** ground truth, leakage prevention, calibration,
    abstention and geospatial-error definitions must be established
    before headline metrics are claimed.

The current architecture is intentionally preserved because the core
design is sound.

The next engineering effort should reduce uncertainty rather than add
features.
