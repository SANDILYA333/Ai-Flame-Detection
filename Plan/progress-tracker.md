# SIH26162 — Progress Tracker

## Current Phase

- **Phase:** Specification and architecture planning
- **Status:** In progress
- **Implementation status:** Not yet started
- **UI:** Intentionally deferred

---

# Current Goal

Build the technical and product specification for SIH26162 before implementation.

The immediate objective is to establish:

1. a precise product definition;
2. a defensible data strategy;
3. an event/persistent-source model;
4. a geospatial architecture;
5. a measurable ML evaluation protocol;
6. an evidence-first intelligence pipeline;
7. a development sequence that avoids overengineering.

---

# Completed

## Strategic understanding

- [x] Official SIH26162 problem statement reviewed.
- [x] Core requirement identified:
  - classify/segregate industrial fires from natural/forest fires;
  - GIS-based storage and visualization.
- [x] Team-provided conceptual architecture reviewed.
- [x] Team-provided must-do / must-not-do list reviewed.
- [x] Team-provided target metrics reviewed.
- [x] Team-provided bottlenecks reviewed.
- [x] Six Thinking Hats applied to the product strategy.
- [x] Initial external resource research completed.

## Product

- [x] Core product thesis defined.
- [x] Primary user/beneficiary/decision-maker distinctions defined.
- [x] Proposed classification taxonomy defined.
- [x] Detection → event → source hierarchy defined.
- [x] Evidence-first output defined.
- [x] Persistent-source intelligence defined.
- [x] Abstention/uncertainty defined as a first-class outcome.

## Architecture

- [x] Recommended stack selected.
- [x] System boundaries defined.
- [x] Storage model defined.
- [x] Core database entities defined.
- [x] API boundary defined.
- [x] ML architecture sequence defined.
- [x] Deployment strategy defined.
- [x] Architecture invariants defined.

## Engineering

- [x] Python/TypeScript standards defined.
- [x] Geospatial precision rules defined.
- [x] Data provenance rules defined.
- [x] ML leakage prevention rules defined.
- [x] Testing standards defined.
- [x] AI/LLM usage policy defined.

---

# In Progress

- [ ] Final geographic demonstration scope.
- [ ] Ground-truth/reference event registry.
- [ ] Final class taxonomy.
- [ ] FIRMS historical data acquisition.
- [ ] Industrial infrastructure reference dataset.
- [ ] Satellite context access strategy.
- [ ] Evaluation benchmark construction.
- [ ] Baseline classifier.
- [ ] Persistence algorithm.
- [ ] GIS API.
- [ ] Frontend/UI — intentionally deferred.

---

# Next Up

## 1. Lock the demonstration geography

Choose a bounded Indian study area containing multiple thermal-source types.

Selection criteria:

- industrial facilities;
- oil/gas or petrochemical activity;
- thermal power;
- mining where possible;
- agricultural land;
- forest/fire-prone areas;
- sufficient historical FIRMS detections.

---

## 2. Build FIRMS data spine

Implement:

```text
FIRMS API
→ raw capture
→ validation
→ canonical schema
→ deduplication
→ PostGIS
```

Acceptance:

- reproducible ingestion;
- source/version retained;
- API failures visible;
- historical data query works.

---

## 3. Build event engine

Implement:

```text
detections
→ spatial-temporal clustering
→ thermal event
```

Acceptance:

- repeated detections can be grouped;
- event centroid and time span generated;
- clustering parameters are configurable.

---

## 4. Build persistent-source engine

Implement:

```text
events
→ source association
→ persistence statistics
→ persistent source
```

Acceptance:

- known persistent hotspots form stable tracks;
- transient events do not become persistent by default.

---

## 5. Build OSM enrichment

Implement:

```text
event
→ nearby OSM objects
→ distance/type features
```

Acceptance:

- industrial context can be attached;
- OSM provenance stored;
- missing OSM data does not break processing.

---

## 6. Build baseline

Before ML:

```text
FIRMS confidence
+ industrial proximity
+ persistence
```

Create a transparent rule baseline.

---

## 7. Build labelled benchmark

This is the highest-priority research task.

Create an event registry with:

- label;
- source;
- evidence;
- timestamp;
- geography;
- confidence.

No benchmark should be used for model claims until label quality is understood.

---

# Open Questions

## Critical

1. **Geography:** Which Indian region will be the primary demo area?
2. **Taxonomy:** Do we use 5 broad classes or 7 classes?
3. **Ground truth:** What sources will be accepted as authoritative labels?
4. **Industrial fire definition:** What exactly qualifies as an industrial fire?
5. **Persistent source definition:** What threshold defines persistence?
6. **Attribution radius:** What spatial relationship qualifies as industrial context?
7. **Satellite:** Which satellite product should be the primary contextual source?
8. **Deployment:** Is near-real-time operation required for the demo, or is historical replay acceptable?
9. **Team:** Who owns data engineering, geospatial processing, ML, backend and frontend?

---

# Architecture Decisions

## ADR-001 — PostGIS

**Decision:** PostgreSQL + PostGIS.

**Why:** The system is fundamentally spatial and relational.

---

## ADR-002 — Redis for MVP orchestration

**Decision:** Redis-backed workers instead of Kafka.

**Why:** Lower operational complexity. Scale should be introduced only when measured requirements justify it.

---

## ADR-003 — Event/source hierarchy

**Decision:**

```text
Detection → Event → Persistent Source
```

**Why:** A raw satellite detection is not necessarily an incident, and persistent sources should not generate thousands of unrelated alerts.

---

## ADR-004 — Evidence-first classification

**Decision:** Every prediction must expose supporting evidence and uncertainty.

**Why:** This is the strongest product differentiation and supports analyst trust.

---

## ADR-005 — Abstention

**Decision:** The classifier may output `uncertain`.

**Why:** Thermal anomaly classification is an open-world problem.

---

## ADR-006 — Tabular model first

**Decision:** Begin with engineered features and gradient boosting.

**Why:** Ground truth is the dominant bottleneck. Deep vision should be added only if measurable gains justify it.

---

# Target Metrics

The team-provided image proposes:

| Metric | Internal target | Status |
|---|---:|---|
| Overall accuracy | ≥95% | Unvalidated |
| Macro F1 | ≥0.92 | Unvalidated |
| Industrial-fire precision | ≥95% | Unvalidated |
| Industrial-fire recall | ≥95% | Unvalidated |
| High-confidence false-positive rate | <3% | Unvalidated |
| Event-to-intelligence latency | <2 min | Engineering target |
| Classification coverage | ≥95% | Unvalidated |
| Persistent-source F1 | ≥0.85 | Unvalidated |
| Median geospatial error | <500 m | Definition required |
| Batch scalability | 10,000 events <5 min | Engineering target |
| Evidence completeness | ≥90% | Definition required |

These are **team targets**, not official SIH requirements.

Before using them in judging material, define:

- dataset;
- test split;
- metric formula;
- confidence threshold;
- spatial tolerance;
- latency measurement boundary.

---

# Known Bottlenecks

1. Ground-truth data.
2. FIRMS spatial ambiguity.
3. Thermal anomaly classification.
4. Temporal/persistent-source analysis.
5. Satellite availability and fusion.

---

# Session Notes

## Current strategic insight

The project should not be positioned as a generic wildfire detector.

The strongest positioning is:

> **Evidence-driven geospatial intelligence for classifying and monitoring ambiguous satellite thermal anomalies.**

The core differentiator should be the ability to explain:

```text
WHAT happened?
WHERE?
WHEN?
WHAT is it likely to be?
WHY?
HOW persistent is it?
WHAT evidence supports the conclusion?
HOW certain are we?
```

---

# Research Notes

Key external findings incorporated into the specification:

- NASA FIRMS provides active-fire/thermal-anomaly observations and explicitly warns about accuracy and interpretation limitations.
- VIIRS 375 m data includes brightness temperature, FRP, confidence, acquisition time, scan/track and day/night information.
- VIIRS can support identification of persistent hotspots such as gas flares.
- OSM industrial tags provide useful contextual information but are not authoritative incident labels.
- Sentinel-2 provides high-resolution optical context but is constrained by revisit and cloud conditions.
- Landsat/HLS can provide complementary historical/contextual imagery.
- STAC and OGC API Features are suitable interoperability patterns for geospatial assets and APIs.

---

# Immediate Next Decision

Before model development, lock:

```text
Geography
+
Taxonomy
+
Ground-truth protocol
+
Persistence definition
+
Evaluation split
```

These five decisions determine whether later ML metrics are meaningful.
