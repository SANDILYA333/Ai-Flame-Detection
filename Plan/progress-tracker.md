# SIH26162 --- Progress Tracker

## Current Phase

-   **Phase:** Specification refinement → scientific/data feasibility
-   **Status:** In progress
-   **Implementation status:** In progress (DB-003 completed; DB-004 next)
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
