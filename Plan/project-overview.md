# SIH26162 — Project Overview & Strategic Product Specification

## 0. Document Status

- **Problem Statement:** SIH26162
- **Official title:** AI-Based Detection and Classification of Industrial Fires and Persistent Thermal Sources Using NASA FIRMS, OSM & Satellite Data
- **Organization:** National Technical Research Organisation (NTRO)
- **Category:** Software
- **Theme:** Disaster Management
- **Planning status:** Specification / architecture planning
- **UI design:** Deliberately excluded from this document set for now
- **Primary source:** Official SIH 2026 problem portal

> **Source discipline:** Official requirements are kept separate from proposed architecture, assumptions, and stretch features. No target metric below should be treated as an official SIH requirement unless explicitly labelled as such.

---

# 1. Executive Definition

## What are we building?

An **AI-assisted geospatial intelligence system** that ingests NASA FIRMS thermal-anomaly detections, enriches each event with industrial infrastructure and land-context data, uses temporal/spatial/spectral/contextual evidence to classify the anomaly, tracks persistent thermal sources, and exposes the resulting intelligence through a GIS-oriented analyst workflow.

The system is **not** primarily a wildfire detector.

The core product is:

> **“A thermal-anomaly intelligence and attribution layer that answers what a satellite hotspot is likely to represent, why the system believes that, whether it is persistent, and what infrastructure/context is nearby.”**

---

# 2. Official Problem — What SIH Actually Says

The official SIH 2026 portal states that industrial facilities produce thermal signatures observable from space, while systems such as NASA FIRMS provide thermal-anomaly detections without distinguishing among industrial fires, gas flares, agricultural burning, mining activity, and wildfires. SIH26162 asks for an AI-enabled geospatial system integrating thermal data, land-cover information, industrial infrastructure databases, and satellite imagery. The explicit deliverables are:

1. Classification and segregation of industrial fires from forest/natural fires.
2. A GIS-based solution for storing and visualizing the output as a map overlay.

**Official source:** SIH 2026 portal, SIH26162.

---

# 3. Product Thesis

## The real problem

A satellite hotspot is an **observation**, not an explanation.

FIRMS can tell us:

> “A thermal anomaly was detected around here at this time.”

The operational question is:

> “What is this anomaly likely to be, how persistent is it, what infrastructure or land-use context surrounds it, and how much evidence supports the classification?”

That distinction is the central product opportunity.

## Product principle

**Detection → Context → Temporal reasoning → Classification → Evidence → Analyst action**

Do not stop at:

`hotspot → class label`

Build:

`hotspot → event cluster → contextual evidence → classification → confidence → explanation → monitoring state`

---

# 4. Core Users and Beneficiaries

| Stakeholder | Role | Pain | Desired outcome |
|---|---|---|---|
| Geospatial/intelligence analyst | Primary user | Raw hotspots require manual interpretation | Prioritized, explainable thermal intelligence |
| Disaster-management / monitoring official | Beneficiary | Difficult to distinguish industrial events from natural fires | Faster situational awareness |
| Infrastructure/security analyst | Secondary user | Persistent abnormal sources are hard to track | Persistent-source watchlists |
| Government decision maker | Decision maker | Dashboards can show data without actionable interpretation | Reliable, auditable intelligence |
| Data/remote-sensing engineer | System operator | Multiple geospatial datasets have different schemas/resolutions | Reproducible ingestion and enrichment |
| Public-safety/environmental stakeholder | Secondary beneficiary | Industrial incidents can have downstream effects | Earlier identification and triage |

### Important distinction

- **User:** operates the system.
- **Beneficiary:** receives the operational value.
- **Decision maker:** can authorize deployment or act on the intelligence.

---

# 5. Six Thinking Hats — Strategic Product Review

## White Hat — Facts and evidence

Known from official SIH:

- FIRMS detects thermal anomalies.
- Industrial and natural sources can be confused.
- Required context includes thermal data, land-cover information, industrial databases and satellite imagery.
- Required output includes industrial-fire segregation and GIS visualization.

Known from NASA documentation:

- VIIRS 375 m FIRMS detections contain location, acquisition time, brightness temperatures, confidence, FRP, scan/track and day/night fields.
- VIIRS can observe persistent hotspots such as gas flares and volcanoes.
- FIRMS explicitly warns that detections may represent fire, hot smoke, agriculture or other sources and that spatial resolution/view geometry matter.

Known limitation:

- A nominal 375 m VIIRS pixel is not equivalent to a 375 m precise incident location.
- A FIRMS detection does not prove that the entire pixel is burning.

## Red Hat — Human/operator reality

An analyst is unlikely to trust:

- a mysterious “AI score”;
- a black-box class;
- a false sense of geographic precision;
- a system that cannot show evidence.

An analyst is more likely to trust:

- the original FIRMS observation;
- nearby infrastructure;
- persistence history;
- satellite/context layers;
- confidence;
- a concise reason code;
- access to the underlying evidence.

## Black Hat — What can kill the project

1. **Ground-truth scarcity.**
2. Treating FIRMS labels as ground truth.
3. Overclaiming facility-level attribution from 375 m data.
4. Cloud-obscured optical imagery.
5. OSM incompleteness.
6. Temporal association errors.
7. Class imbalance.
8. Leakage caused by random train/test splits over the same persistent source.
9. Building a beautiful GIS dashboard with weak intelligence.
10. Trying to classify every possible thermal phenomenon.
11. Using an LLM as the classifier.
12. Chasing 95% accuracy on a poorly labelled dataset.

## Yellow Hat — Upside

The project has unusually strong hackathon characteristics:

- real satellite data;
- government problem owner;
- GIS;
- temporal intelligence;
- explainable AI;
- visible map-based demo;
- clear operational story;
- meaningful technical depth without requiring custom hardware.

## Green Hat — Innovation opportunities

Potential differentiators:

- persistence-aware event clustering;
- facility-context graph;
- evidence cards rather than bare labels;
- temporal signatures;
- “expected vs anomalous” reasoning;
- confidence calibration;
- uncertainty-aware spatial attribution;
- persistent-source watchlists;
- counterfactual explanation: “classification would change if industrial context were removed”;
- multi-sensor evidence fusion;
- event replay for historical validation.

## Blue Hat — Strategic control

The project should be governed by five questions:

1. Did we ingest the correct observation?
2. Did we enrich it with the right context?
3. Did we classify it using defensible evidence?
4. Can an analyst understand why?
5. Can we measure whether the system is actually better than baseline?

---

# 6. Proposed Product

## Working product name

**THERMALINTEL**

### Tagline

**From satellite hotspot to explainable thermal intelligence.**

### One-line pitch

> THERMALINTEL converts raw NASA FIRMS thermal anomalies into explainable, context-aware intelligence by combining satellite observations, temporal persistence, industrial infrastructure and land-cover evidence.

---

# 7. Classification Taxonomy

## Proposed v1 taxonomy

This taxonomy is a **strategic proposal**, not an official SIH requirement.

1. Industrial accidental fire
2. Gas flare / persistent industrial thermal source
3. Thermal power / industrial heat source
4. Mining / extraction thermal activity
5. Agricultural burning
6. Wildfire / forest fire
7. Other / unknown thermal anomaly

### Why “Other / Unknown” is mandatory

A classifier without an abstention class will force uncertain events into incorrect categories.

The production-minded behavior is:

`classified` **or** `insufficient evidence`

not:

`AI always knows`.

### V1 simplification

For the first working prototype, collapse to:

- Industrial
- Persistent industrial / flare
- Natural / vegetation fire
- Agricultural / land burning
- Other / uncertain

Then demonstrate finer subclassification only when evidence supports it.

---

# 8. Core Intelligence Pipeline

```text
NASA FIRMS
   |
   v
Ingestion + validation
   |
   v
Event normalization
   |
   v
Spatio-temporal clustering
   |
   +--------------------+
   |                    |
   v                    v
OSM / infrastructure    Satellite/context
   |                    |
   +---------+----------+
             |
             v
       Feature builder
             |
             v
   Rules + ML classifier
             |
             v
   Calibration / abstention
             |
             v
 Evidence generator
             |
             v
 Persistent-source tracker
             |
             v
 GIS intelligence API
             |
             v
 Analyst interface
```

---

# 9. Core Intelligence Model

For each event, construct an evidence vector:

```text
E = {
  FIRMS observation,
  temporal behavior,
  spatial behavior,
  FRP / brightness,
  confidence,
  land-cover context,
  industrial proximity,
  infrastructure type,
  satellite context,
  neighboring hotspot density,
  persistence statistics,
  uncertainty
}
```

The classifier should answer:

```text
P(class | E)
```

but the product should also expose:

```text
Why?
Evidence?
Uncertainty?
What could make this wrong?
```

---

# 10. Persistent Thermal Source Intelligence

Persistence is one of the highest-value signals.

For each spatially associated cluster:

- number of detections;
- number of distinct observation dates;
- active days / observation days;
- temporal span;
- mean/median FRP;
- FRP variance;
- centroid drift;
- spatial footprint;
- night/day distribution;
- proximity to industrial assets;
- seasonal behavior.

### Example interpretation

```text
High persistence
+ tight spatial footprint
+ oil/gas infrastructure nearby
+ repeated nighttime detections
= strong flare candidate
```

This is an inference, not proof.

---

# 11. Event Model

A raw FIRMS detection is not necessarily an “incident”.

Use three layers:

### Detection

One satellite-observed hotspot.

### Event

A spatio-temporal grouping of detections believed to represent the same episode.

### Source

A longer-lived spatial entity that generates repeated events.

This hierarchy prevents a persistent flare from becoming thousands of unrelated “fires”.

---

# 12. Evidence-First Output

Every classification should produce:

```json
{
  "event_id": "...",
  "class": "persistent_industrial_source",
  "confidence": 0.91,
  "location": {
    "lat": 0,
    "lon": 0
  },
  "evidence": [
    "Repeated detections over 18 days",
    "Industrial facility within 220 m",
    "High temporal persistence",
    "Consistent spatial footprint"
  ],
  "uncertainty": [
    "Optical satellite evidence unavailable because of cloud cover"
  ]
}
```

The exact schema will be finalized in `architecture.md`.

---

# 13. What We MUST Build

1. NASA FIRMS as the core thermal input.
2. OSM/industrial infrastructure enrichment.
3. Satellite imagery/context enrichment.
4. Classification.
5. Persistent-source handling.
6. GIS-based output.
7. Explainable classification.
8. Uncertainty tracking.

## What We SHOULD NOT Build

1. Generic wildfire application.
2. Generic FIRMS visualization dashboard.
3. Pure image classifier.
4. LLM-based classification core.
5. “Perfect detection” claims.
6. Massive enterprise infrastructure.
7. Unnecessary mobile application.
8. Custom satellite-data processing stack when existing analysis-ready products suffice.

---

# 14. Differentiation

## The one USP

> **Evidence-backed thermal attribution: every classification is accompanied by temporal, spatial, infrastructure and satellite evidence rather than a black-box label.**

This is stronger than:

- “AI powered”
- “real time”
- “cloud based”
- “GIS enabled”

because it directly addresses analyst trust.

---

# 15. Demo Strategy

The demo should tell one story.

### Scenario

1. Select a historical region containing mixed thermal anomalies.
2. Show raw FIRMS detections.
3. Show that raw hotspots are ambiguous.
4. Run enrichment.
5. Display event clusters.
6. Show industrial context.
7. Show temporal persistence.
8. Produce classification.
9. Open the evidence panel.
10. Compare with ground/reference evidence.
11. Show persistent-source timeline.
12. Replay a known industrial event versus a vegetation-fire event.

### Judge takeaway

> “The system did not merely find a hotspot. It explained what the hotspot most likely represents.”

---

# 16. Success Criteria

## Product-level

- A user can retrieve FIRMS events.
- Events are normalized and spatially clustered.
- Each event can be enriched with contextual data.
- The system produces a class and confidence/uncertainty.
- The system can identify persistent sources.
- Every classification has evidence.
- Results are exposed geographically.

## Model-level

Do not use accuracy alone.

Primary metrics:

- Industrial-class precision
- Industrial-class recall
- Macro F1
- PR-AUC for industrial-vs-nonindustrial detection
- Calibration error
- Abstention/coverage curve
- Event-level false-positive rate
- Spatial attribution error
- Persistence-source F1

---

# 17. Target Metrics — Internal Stretch Targets

The image supplied by the team proposes:

- ≥95% overall accuracy
- ≥0.92 macro F1
- ≥95% industrial-fire precision
- ≥95% industrial-fire recall
- <3% high-confidence false-positive rate
- <2 minutes event-to-intelligence latency
- ≥95% classification coverage
- ≥0.85 persistent-source F1
- <500 m median geospatial error
- 10,000 events in <5 minutes batch processing
- ≥90% evidence completeness

### Strategic correction

These are **internal target-sheet numbers, not official SIH requirements and not yet validated as achievable**.

Do not optimize the project around them until the dataset and evaluation protocol exist.

In particular:

- 95% industrial precision may be realistic under a curated evaluation set and difficult on open-world data.
- 95% recall may conflict with high precision.
- <500 m “geospatial error” must be carefully defined because FIRMS itself has non-trivial pixel/geolocation limitations.
- 95% coverage can be dangerous if the system should abstain on uncertain cases.

---

# 18. Primary Bottlenecks

The supplied image identifies:

1. Ground-truth data
2. FIRMS spatial ambiguity
3. Thermal anomaly classification
4. Temporal/persistent-source analysis
5. Satellite availability and data fusion

These are correct and should dominate engineering effort.

---

# 19. Development Priorities

### P0

- FIRMS ingestion
- event schema
- event clustering
- OSM enrichment
- persistence engine
- baseline classifier
- evidence generation
- GIS API

### P1

- satellite contextual features
- calibrated ML model
- persistent-source watchlist
- historical replay
- model evaluation pipeline

### P2

- multi-sensor fusion
- anomaly detection against source baseline
- advanced geospatial reasoning
- uncertainty visualization
- active-learning feedback loop

### P3

- production-scale streaming
- automated retraining
- advanced foundation models
- additional satellite sources
- agency integrations

---

# 20. Key Assumptions

1. FIRMS access can be obtained for development.
2. OSM coverage is sufficient in selected demonstration areas.
3. Historical FIRMS data can support event clustering.
4. Reference events can be assembled from authoritative/public sources.
5. Satellite contextual imagery can be retrieved for selected events.
6. The first version can operate as a decision-support system rather than an autonomous emergency system.

Every assumption must be tested before it becomes a system dependency.

---

# 21. Open Questions

These do not block the architecture, but must be resolved before model freeze:

1. What geographic scope will be used for the final demonstration?
2. Should the first classifier use the five broad classes or the seven-class taxonomy?
3. Which reference/ground-truth sources will be accepted as evaluation truth?
4. What exact definition will we use for “industrial fire”?
5. What constitutes a persistent source: number of detections, active days, or both?
6. What maximum spatial distance qualifies as “near an industrial facility”?
7. Which satellite product will be the primary contextual imagery source?
8. Will the final deployment require near-real-time global ingestion or only a bounded region?
9. What is the team's acceptable infrastructure budget?
10. Which team members own geospatial engineering, ML, backend and frontend?

---

# 22. Strategic Bottom Line

The winning version is not:

> “We built an AI wildfire classifier.”

It is:

> **“We built an evidence-driven geospatial intelligence system that turns ambiguous satellite thermal anomalies into explainable industrial-fire and persistent-source intelligence.”**

That is the product we should engineer around.
