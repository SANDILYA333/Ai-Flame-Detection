# SIH26162 --- Project Overview & Strategic Product Specification

## 0. Document Status

-   **Problem Statement:** SIH26162
-   **Official title:** AI-Based Detection and Classification of
    Industrial Fires and Persistent Thermal Sources Using NASA FIRMS,
    OSM & Satellite Data
-   **Organization:** National Technical Research Organisation (NTRO)
-   **Category:** Software
-   **Theme:** Miscellaneous
-   **Planning status:** Specification / architecture planning
-   **UI design:** Intentionally deferred and maintained separately
-   **Primary authority:** Official SIH 2026 problem statement
-   **Status:** Refined after cross-file consistency audit

> **Source discipline:** Official SIH requirements, verified external
> facts, assumptions, and strategic recommendations are explicitly
> separated.

------------------------------------------------------------------------

# 1. Executive Definition

## What are we building?

An **evidence-driven geospatial intelligence system** that converts
satellite-observed thermal anomalies into contextualized,
uncertainty-aware intelligence.

The system ingests NASA FIRMS observations, groups detections into
thermal events and longer-lived sources, enriches them with industrial
infrastructure and land-cover context, optionally incorporates satellite
imagery when available, computes interpretable features, classifies the
event/source, estimates confidence, exposes evidence and uncertainty,
and stores the result for GIS visualization and analyst investigation.

The system is **not primarily a wildfire detector** and it must not
claim that a FIRMS point is an exact facility location.

### Core product

> **Turn an ambiguous satellite thermal anomaly into explainable thermal
> intelligence: what it likely represents, what context supports that
> interpretation, how persistent it is, and how certain the system is.**

------------------------------------------------------------------------

# 2. Official Problem Requirements

The official problem asks for a system that integrates thermal anomaly
data, land-cover information, industrial infrastructure databases and
satellite imagery to distinguish industrial fires/persistent thermal
sources from forest/natural and other thermal activity.

The explicit deliverables are:

1.  **Classification and segregation of industrial fires from
    forest/natural fires.**
2.  **A GIS-based solution for storing and visualizing the resulting
    output as a map overlay.**

These are **MUST-HAVE product requirements**, not optional enhancements.

### Important distinction

The following are proposed implementation mechanisms rather than
independent official requirements:

-   FIRMS ingestion
-   OSM/industrial-context enrichment
-   land-cover enrichment
-   satellite-context retrieval
-   event clustering
-   persistence analysis
-   explainability
-   uncertainty handling

They are required only insofar as they enable a defensible
implementation of the official problem.

------------------------------------------------------------------------

# 3. Product Thesis

A FIRMS detection is an **observation**, not an explanation.

NASA explicitly describes active-fire/thermal-anomaly detections as
potentially representing fire, hot smoke, agriculture or other sources
and warns that spatial resolution, view geometry and detection
confidence matter.

Therefore:

``` text
FIRMS detection ≠ confirmed industrial fire
```

The product principle is:

``` text
Observation
    ↓
Event formation
    ↓
Context
    ↓
Temporal reasoning
    ↓
Classification / attribution
    ↓
Calibration / uncertainty
    ↓
Evidence
    ↓
GIS intelligence
```

------------------------------------------------------------------------

# 4. Canonical Thermal Intelligence Ontology

Do **not** use one flat class list that mixes phenomenon, infrastructure
type and persistence.

Every thermal event/source is represented using separate dimensions.

## 4.1 Phenomenon

Proposed v1 values:

-   `fire`
-   `flare`
-   `industrial_thermal_source`
-   `agricultural_burn`
-   `vegetation_wildfire`
-   `other_thermal_anomaly`
-   `unknown`

## 4.2 Context

Proposed values:

-   `industrial`
-   `oil_gas`
-   `power`
-   `mining`
-   `agricultural`
-   `forest_vegetation`
-   `urban`
-   `other`
-   `unknown`

Context is **evidence**, not automatically the target label.

Example:

> A thermal anomaly near a power plant does not prove that the anomaly
> is a fire caused by the plant.

## 4.3 Persistence state

-   `transient`
-   `recurring`
-   `persistent`
-   `insufficient_history`

Persistence is a temporal attribute, not a class.

## 4.4 Attribution strength

-   `strong`
-   `moderate`
-   `weak`
-   `unknown`

## 4.5 Final intelligence example

``` text
Phenomenon: flare
Context: oil_gas
Persistence: persistent
Attribution: strong
Confidence: 0.91
```

This ontology prevents the previous error of mixing concepts such as
"gas flare", "mining", "industrial fire" and "persistent" into a single
mutually-exclusive classifier.

------------------------------------------------------------------------

# 5. Core Users

  ----------------------------------------------------------------------------------------
  Stakeholder               Role              Pain                  Desired outcome
  ------------------------- ----------------- --------------------- ----------------------
  Geospatial/intelligence   Primary user      Raw hotspots require  Prioritized,
  analyst                                     manual interpretation explainable thermal
                                                                    intelligence

  Monitoring/disaster       Beneficiary       Difficult to          Faster situational
  official                                    distinguish           awareness
                                              industrial and        
                                              natural activity      

  Infrastructure/security   Secondary user    Persistent sources    Persistent-source
  analyst                                     are difficult to      intelligence
                                              track                 

  Government decision maker Decision maker    Raw dashboards do not Auditable decision
                                              provide defensible    support
                                              interpretation        

  Data/remote-sensing       System operator   Multiple datasets     Reproducible
  engineer                                    have different        ingestion/enrichment
                                              schemas/resolutions   
  ----------------------------------------------------------------------------------------

------------------------------------------------------------------------

# 6. Product Scope

## In Scope

-   NASA FIRMS thermal observations
-   canonical observation storage
-   spatio-temporal event formation
-   persistent-source analysis
-   industrial/context enrichment
-   land-cover enrichment
-   satellite-context retrieval where available
-   feature generation
-   deterministic baselines
-   tabular ML classification where justified
-   confidence calibration
-   abstention
-   evidence generation
-   provenance
-   GIS-ready intelligence storage and APIs
-   historical replay/evaluation

## Out of Scope for the MVP

-   autonomous emergency response
-   guaranteed facility-level fire localization
-   universal global classification of every thermal phenomenon
-   LLM as the primary classifier
-   custom satellite hardware
-   enterprise-scale streaming infrastructure without measured need
-   a separate mobile application
-   fully automated model retraining
-   UI polish before intelligence validation

------------------------------------------------------------------------

# 7. MUST / SHOULD / WOW

## MUST --- Required for SIH compliance

1.  Industrial-fire classification/segregation from forest/natural
    fires.
2.  GIS storage of resulting intelligence.
3.  GIS map-overlay visualization.
4.  Required source-data integration needed to support the
    classification.
5.  A defensible classification/evaluation workflow.

## SHOULD --- High-value capabilities

-   FIRMS event clustering
-   persistent-source tracking
-   OSM/industrial-context enrichment
-   land-cover enrichment
-   satellite context
-   confidence calibration
-   abstention
-   evidence cards
-   historical event replay

## WOW --- Differentiators

-   evidence graph connecting observation → event → source → context →
    prediction
-   temporal persistence replay
-   "why this classification" evidence breakdown
-   explicit uncertainty/limitations
-   source-level monitoring/watchlists
-   ablation-driven proof that context improves over FIRMS-only
    baselines

------------------------------------------------------------------------

# 8. Core User Journey

``` text
Analyst selects geography/time window
        ↓
System retrieves/loads FIRMS observations
        ↓
Validate + normalize + preserve provenance
        ↓
Group detections into thermal events
        ↓
Track recurring/persistent sources
        ↓
Enrich with industrial/context + land cover
        ↓
Retrieve satellite context if available
        ↓
Build features
        ↓
Run deterministic baseline
        ↓
Run ML model if justified
        ↓
Calibrate confidence
        ↓
Allow abstention when evidence is insufficient
        ↓
Generate evidence + uncertainty
        ↓
Store GIS-ready intelligence
        ↓
Analyst investigates / prioritizes / monitors
```

------------------------------------------------------------------------

# 9. Evidence-First Output

Every prediction must expose:

-   predicted phenomenon
-   context
-   persistence
-   attribution strength
-   calibrated confidence
-   supporting evidence
-   missing evidence
-   known limitations
-   source provenance
-   model/version information

Example:

``` json
{
  "phenomenon": "flare",
  "context": "oil_gas",
  "persistence": "persistent",
  "attribution": "strong",
  "confidence": 0.91,
  "evidence": [
    "repeated detections across 19 active days",
    "stable spatial footprint",
    "industrial facility within configured proximity threshold"
  ],
  "limitations": [
    "optical imagery unavailable for the relevant period"
  ]
}
```

The exact API schema belongs in `architecture.md`.

------------------------------------------------------------------------

# 10. Evaluation Philosophy

Do not optimize for one headline accuracy number.

Primary evaluation should include:

-   industrial-fire precision
-   industrial-fire recall
-   macro F1
-   PR-AUC for industrial-vs-nonindustrial classification where
    appropriate
-   calibration error
-   selective risk/coverage
-   event-level false-positive rate
-   persistence-source F1
-   spatial attribution error, only when a valid reference geometry
    exists
-   latency
-   evidence completeness

### Coverage rule

Do **not** make "95% classification coverage" a hard product objective
if it forces the system to classify low-evidence cases.

The correct trade-off is:

> maximize useful coverage subject to minimum reliability constraints.

------------------------------------------------------------------------

# 11. Geospatial Precision Rule

A FIRMS detection coordinate is not automatically a facility coordinate.

Never claim:

``` text
FIRMS point = exact facility
```

Instead maintain:

``` text
detection geometry
event geometry
source geometry
facility geometry
distance
attribution confidence
```

A geospatial error metric must be explicitly defined before reporting
it.

------------------------------------------------------------------------

# 12. Internal Engineering Targets

These are **team targets, not official SIH requirements** and must be
validated empirically:

-   bounded FIRMS ingestion: target \<30 s
-   event enrichment: target \<30 s/event in batch mode
-   classification: target \<1 s/event excluding external downloads
-   end-to-end demo event: target \<2 min when required external data is
    available
-   10,000-event offline batch: target \<5 min

External data latency must be reported separately from internal
processing latency.

------------------------------------------------------------------------

# 13. Strategic USP

> **Evidence-backed thermal attribution: every classification is
> accompanied by temporal, spatial, infrastructure, land-cover and/or
> satellite evidence, with uncertainty made explicit.**

The system should never sell "AI-powered" as the USP.

The USP is **defensible intelligence from ambiguous observations**.

------------------------------------------------------------------------

# 14. Six Thinking Hats --- Product Gate

## White Hat

Only verified facts, measurements and source-backed claims.

## Red Hat

Would an analyst trust the result? What would feel misleading?

## Black Hat

Attack ground truth, spatial ambiguity, leakage, cloud cover, OSM
incompleteness, class imbalance and overclaiming.

## Yellow Hat

Identify measurable operational value and judge-visible strengths.

## Green Hat

Search for better representations, evidence mechanisms and simpler
alternatives.

## Blue Hat

Freeze scope, define the next verifiable experiment and prevent feature
creep.

------------------------------------------------------------------------

# 15. Strategic Rule

The winning project is not the largest system.

It is:

> **The smallest technically sophisticated system that makes a
> hard-to-fake claim, proves it with evidence, and maps directly to the
> official problem.**
