# SIH26162 — AI / Development Workflow Rules

## 1. Operating Philosophy

Build this project using a **spec-driven, evidence-first workflow**.

The context files define:

- what the product is;
- what the architecture is;
- what code quality means;
- what the current state is.

Do not invent product behavior simply because it sounds useful.

When a requirement is unclear:

1. identify the ambiguity;
2. record it in `progress-tracker.md`;
3. choose the smallest defensible assumption;
4. implement behind a replaceable boundary.

---

# 2. Six Thinking Hats as a Development Gate

Every major architecture or product decision should be reviewed using:

## White Hat — Evidence

Ask:

- What do we actually know?
- What is official?
- What is measured?
- What is missing?
- What source supports the claim?

## Red Hat — Human trust

Ask:

- Would an analyst trust this?
- What would feel misleading?
- What would cause a user to ignore the system?

## Black Hat — Failure

Ask:

- What can go wrong?
- What false positive is dangerous?
- What data dependency can fail?
- Where can the model leak information?

## Yellow Hat — Value

Ask:

- What creates actual operational value?
- What makes this worth deploying?
- What is the strongest judge-visible outcome?

## Green Hat — Innovation

Ask:

- Is there a better way?
- Can we expose a new type of intelligence?
- Can we reduce manual work?

## Blue Hat — Control

Ask:

- What is the next smallest verifiable step?
- What metric determines success?
- What should we explicitly not build?

---

# 3. Research Rules

Research must be source-first.

## Tier 1 — Primary

Prefer:

- official SIH portal;
- NASA FIRMS/Earthdata;
- ESA;
- USGS;
- OGC;
- OpenStreetMap documentation;
- official dataset documentation.

## Tier 2 — Scientific

Use:

- peer-reviewed papers;
- established remote-sensing research;
- validation studies.

## Tier 3 — Community/secondary

Use:

- GitHub;
- technical blogs;
- tutorials.

Use these for implementation ideas, not as authoritative scientific claims when primary sources exist.

---

# 4. Source Register

The following resources should anchor implementation.

## SIH

Official SIH 2026 portal:

```text
https://sih.gov.in/sih2026PS
```

SIH26162 is explicitly listed as:

> AI-Based Detection and Classification of Industrial Fires and Persistent Thermal Sources Using NASA FIRMS, OSM & Satellite Data

The official deliverables explicitly require industrial-fire segregation and GIS visualization.

## NASA FIRMS

Active fire data:

```text
https://firms.modaps.eosdis.nasa.gov/active_fire/
```

FIRMS API:

```text
https://firms.modaps.eosdis.nasa.gov/api/area/
```

VIIRS fire hotspot documentation:

```text
https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_VIIRS_Firehotspots.html
```

NASA's documentation identifies:

- brightness temperatures;
- scan/track;
- acquisition time;
- confidence;
- FRP;
- day/night;
- satellite;
- processing version.

## Sentinel-2

ESA Sentinel-2:

```text
https://www.esa.int/Applications/Observing_the_Earth/Copernicus/Sentinel-2
```

## Landsat

USGS Landsat Collection 2:

```text
https://www.usgs.gov/landsat-missions/landsat-collection-2
```

## HLS

NASA Harmonized Landsat Sentinel-2:

```text
https://hls.gsfc.nasa.gov/
```

## ESA WorldCover

```text
https://esa-worldcover.org/en
```

## OpenStreetMap

```text
https://www.openstreetmap.org/
```

Overpass API:

```text
https://wiki.openstreetmap.org/wiki/Overpass_API
```

## OGC STAC

```text
https://www.ogc.org/standards/stac/
```

## OGC API Features

```text
https://ogcapi.ogc.org/features/
```

---

# 5. Critical Research Findings

## FIRMS is not ground truth

NASA itself warns that satellite-derived active-fire/thermal-anomaly detections have limited accuracy and can represent fire, hot smoke, agriculture or other sources.

Therefore:

```text
FIRMS detection ≠ confirmed industrial fire
```

This is a foundational rule.

---

# 6. Ground Truth Strategy

Ground truth is the hardest part of the project.

Build a **reference event registry**.

Each labelled event should contain:

```text
event_id
label
label_source
source_url
source_date
geographic_evidence
temporal_evidence
confidence
annotator
annotation_notes
```

## Label hierarchy

### Tier A — authoritative

- official incident reports;
- government releases;
- company incident disclosures;
- credible regulatory reports.

### Tier B — strong independent evidence

- reputable news reports with location/time;
- multiple independent sources;
- validated event databases.

### Tier C — weak/proxy

- inferred from spatial context;
- OSM tags;
- unsourced reports.

Tier C should not be treated as hard ground truth.

---

# 7. Weak Supervision

Where true labels are unavailable, use weak labels only for:

- model pretraining;
- exploratory analysis;
- feature engineering.

Do not report weak-label performance as real-world performance.

Example:

```text
OSM industrial polygon + persistent FIRMS
```

can create a **candidate industrial source**.

It cannot automatically create:

```text
confirmed industrial fire
```

---

# 8. Data Acquisition Strategy

## Stage A

Build a bounded Indian demonstration region.

Choose regions containing:

- industrial complexes;
- oil/gas infrastructure;
- thermal plants;
- mining;
- agricultural areas;
- forest regions.

This provides class diversity.

## Stage B

Expand to multiple regions.

## Stage C

Test on geographically unseen regions.

---

# 9. Dataset Construction

## Positive industrial events

Candidates:

- documented industrial incidents;
- persistent flare sites;
- thermal power facilities;
- mining areas with validated thermal activity.

## Natural fires

Candidates:

- wildfire/fire-event reference sources;
- FIRMS events spatially associated with forest/vegetation burn areas;
- documented wildfire events.

## Agricultural burning

Candidates:

- agricultural land;
- seasonal burn patterns;
- documented agricultural fires.

## Other

Include:

- volcanoes;
- false detections;
- uncertain events;
- non-fire hot surfaces.

The “other” set is essential for testing false positives.

---

# 10. Event-Level Labels

Never train directly on raw FIRMS points if the task is event classification.

Preferred:

```text
detections
→ events
→ labels
```

The same event can contain multiple FIRMS detections.

---

# 11. Baseline Before AI

Before training ML, implement:

```text
Baseline 1:
FIRMS confidence threshold

Baseline 2:
Industrial proximity rule

Baseline 3:
Persistence threshold

Baseline 4:
Rule combination
```

Then compare ML against them.

If ML cannot beat the baseline meaningfully, do not add complexity.

---

# 12. Model Development Sequence

## Model 0

Rules only.

## Model 1

Logistic Regression.

## Model 2

Random Forest.

## Model 3

Gradient boosting.

## Model 4

Gradient boosting + calibrated probabilities.

## Model 5

Multimodal model with satellite imagery.

Only proceed when the previous stage's failure justifies the next stage.

---

# 13. Model Evaluation Protocol

Every experiment must record:

```text
experiment_id
dataset_version
feature_version
model
hyperparameters
train/test split
metrics
confusion matrix
calibration
errors
```

## Required splits

### Temporal split

Train on earlier dates, test on later dates.

### Spatial split

Train on some regions, test on unseen regions.

### Source split

Persistent source/facility does not appear in both train and test.

---

# 14. Error Analysis

After every model:

1. inspect false industrial positives;
2. inspect false industrial negatives;
3. inspect persistent-source errors;
4. inspect uncertain events;
5. inspect region-specific performance;
6. inspect day/night differences;
7. inspect cloud-affected cases.

Do not immediately tune hyperparameters.

First understand the error.

---

# 15. Feature Ablation

Run:

```text
FIRMS only
FIRMS + temporal
FIRMS + temporal + OSM
FIRMS + temporal + land cover
FIRMS + temporal + satellite
All features
```

This proves whether each data source actually adds value.

This is extremely important for the SIH presentation.

---

# 16. Evidence Ablation

Also test:

```text
No context
OSM only
Temporal only
OSM + temporal
OSM + satellite
All evidence
```

The goal is to demonstrate that data fusion improves attribution.

---

# 17. Confidence Calibration

Raw model probabilities are not automatically trustworthy.

Use:

- Platt scaling;
- isotonic regression;
- calibration curves.

The final system should expose calibrated confidence.

---

# 18. Abstention

Implement:

```text
if confidence < threshold:
    class = "uncertain"
```

Optimize threshold using validation data.

Report:

```text
coverage
precision
recall
```

as a curve.

A judge should see that the system understands its own limits.

---

# 19. Persistence Detection

Start simple.

### Candidate algorithm

1. Normalize detections.
2. Cluster by spatial proximity.
3. Build time series.
4. Calculate active days.
5. Calculate spatial stability.
6. Calculate FRP stability.
7. Assign persistence score.
8. Track source.

Then compare against more advanced methods.

---

# 20. Satellite Strategy

Do not make satellite imagery mandatory for every inference.

Use a tiered strategy:

### Tier 1

FIRMS + temporal + spatial + OSM.

### Tier 2

Add land cover.

### Tier 3

Add optical satellite imagery when available.

### Tier 4

Add advanced image model only if it improves evaluation.

This makes the system resilient to cloud/revisit limitations.

---

# 21. LLM Policy

LLMs are **not** the primary classifier.

They may be used for:

- natural-language report generation;
- evidence summarization;
- analyst query interpretation;
- converting structured evidence into readable briefings.

They must not invent:

- locations;
- events;
- causes;
- evidence;
- confidence.

The source of truth is structured data.

---

# 22. Implementation Workflow

For every feature:

### Step 1 — Define

Write:

```text
goal
inputs
outputs
acceptance criteria
failure modes
```

### Step 2 — Implement smallest slice

Do not build the whole pipeline.

### Step 3 — Test

Unit + integration.

### Step 4 — Measure

Latency, correctness, data quality.

### Step 5 — Update documentation

Update:

- architecture;
- standards;
- progress.

### Step 6 — Move on

Only after the feature is end-to-end verifiable.

---

# 23. Feature Order

## Sprint 1

### Unit 1

FIRMS ingestion.

Acceptance:

- records fetched;
- schema validated;
- stored in PostGIS;
- duplicates handled.

### Unit 2

Event clustering.

Acceptance:

- raw detections become events;
- event statistics generated.

### Unit 3

Persistence.

Acceptance:

- repeated sources tracked;
- timeline generated.

---

## Sprint 2

### Unit 4

OSM enrichment.

Acceptance:

- nearby assets retrieved;
- distances calculated;
- provenance stored.

### Unit 5

Land-cover enrichment.

Acceptance:

- land-cover context attached.

### Unit 6

Feature builder.

Acceptance:

- deterministic feature vector produced.

---

## Sprint 3

### Unit 7

Rule baseline.

Acceptance:

- baseline metrics generated.

### Unit 8

ML baseline.

Acceptance:

- grouped/spatial/temporal evaluation completed.

### Unit 9

Calibration.

Acceptance:

- calibrated confidence;
- abstention threshold.

---

## Sprint 4

### Unit 10

Evidence engine.

### Unit 11

Satellite context.

### Unit 12

GIS API.

---

## Sprint 5

### Unit 13

Analyst workflow.

### Unit 14

Historical replay.

### Unit 15

Demo hardening.

---

# 24. Definition of Done for ML

ML is not “done” when accuracy looks good.

It is done when:

- dataset is documented;
- labels are traceable;
- split avoids leakage;
- baseline exists;
- model beats baseline;
- per-class metrics exist;
- calibration exists;
- errors are understood;
- confidence threshold is selected;
- evidence is generated;
- model is versioned.

---

# 25. Definition of Done for Data

Data is done when:

- source is documented;
- license/usage is checked;
- schema is stable;
- provenance is preserved;
- validation tests exist;
- missingness is measured;
- duplicates are handled;
- update cadence is known.

---

# 26. Definition of Done for Demo

The demo is done when:

- one known industrial event is correctly handled;
- one persistent flare is tracked;
- one natural fire is distinguished;
- evidence is visible;
- uncertainty is visible;
- raw FIRMS can be compared with enriched output;
- system can replay a historical event;
- no internet dependency can unexpectedly destroy the entire demo.

Maintain a local demo dataset as a fallback.

---

# 27. Do Not Build Yet

Do not build:

- custom deep-learning architecture;
- Kafka;
- Kubernetes;
- mobile app;
- public user accounts;
- social features;
- LLM agent;
- autonomous emergency dispatch;
- global-scale ingestion;
- real-time satellite image generation;
- complex microservice mesh.

These are distractions until the core intelligence works.

---

# 28. Research Questions to Resolve

1. What reference dataset gives the strongest industrial incident labels in India?
2. How should flare/persistent sources be labelled separately from accidental industrial fires?
3. Which land-cover product is most useful for the selected geography?
4. What satellite imagery is accessible with acceptable latency?
5. How much does OSM improve classification?
6. How much does temporal persistence improve classification?
7. How much does satellite imagery improve classification?
8. What is the practical spatial attribution error?
9. Which classes are fundamentally inseparable at FIRMS resolution?
10. What confidence threshold gives the best precision/coverage trade-off?

---

# 29. Strategic Rule

Whenever someone proposes a feature, ask:

> **Does this improve detection, attribution, persistence analysis, explainability, or analyst decision-making?**

If not, it probably does not belong in the hackathon MVP.
