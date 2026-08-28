# SIH26162 --- AI / Development Workflow Rules

## 1. Operating Philosophy

Build this project using a **spec-driven, evidence-first workflow**.

The context files define:

-   what the product is;
-   what the architecture is;
-   what engineering quality means;
-   what is currently decided;
-   what remains unresolved.

Do not invent product behavior merely because it sounds useful.

When a requirement is unclear:

1.  identify the ambiguity;
2.  record it in `progress-tracker.md`;
3.  choose the smallest defensible assumption only when implementation
    cannot wait;
4.  isolate the assumption behind a replaceable boundary;
5.  never silently convert the assumption into a fact.

------------------------------------------------------------------------

# 2. Decision Status Vocabulary

Every major decision must be one of:

-   **FACT** --- directly supported by an authoritative source or
    measured result.
-   **VERIFIED** --- independently confirmed through reliable research.
-   **ASSUMPTION** --- currently accepted but not yet validated.
-   **PROVISIONAL** --- implementation choice intentionally left
    replaceable.
-   **RECOMMENDATION** --- strategic choice made by the team.
-   **OPEN QUESTION** --- must be resolved before a dependent decision
    is frozen.

Never present an assumption as a fact.

------------------------------------------------------------------------

# 3. Six Thinking Hats Development Gate

Every major product, data or architecture decision should be reviewed
through all six hats.

## White Hat --- Evidence

Ask:

-   What do we actually know?
-   What is official?
-   What is measured?
-   What is missing?
-   What source supports the claim?

## Red Hat --- Human trust

Ask:

-   Would an analyst trust this?
-   What would feel misleading?
-   What would make the system look overconfident?

## Black Hat --- Failure

Ask:

-   What can fail?
-   What false positive is dangerous?
-   Where can data leakage occur?
-   What happens when external data disappears?

## Yellow Hat --- Value

Ask:

-   What creates actual operational value?
-   What directly satisfies SIH?
-   What makes the demo memorable?

## Green Hat --- Alternatives

Ask:

-   Is there a simpler solution?
-   Is there a better representation?
-   Can we expose stronger intelligence without more infrastructure?

## Blue Hat --- Control

Ask:

-   What is the smallest next experiment?
-   What metric determines success?
-   What should explicitly not be built?
-   What decision must be frozen before implementation?

------------------------------------------------------------------------

# 4. Research Rules

## Tier 1 --- Primary

Prefer:

-   official SIH portal;
-   NASA FIRMS/Earthdata;
-   ESA;
-   USGS;
-   OGC;
-   official OpenStreetMap documentation;
-   official dataset documentation.

## Tier 2 --- Scientific

Use:

-   peer-reviewed papers;
-   established remote-sensing research;
-   validation studies.

## Tier 3 --- Secondary

Use:

-   GitHub;
-   technical blogs;
-   tutorials.

Secondary sources may help implementation but should not be used as
authoritative evidence when primary sources exist.

------------------------------------------------------------------------

# 5. Source Register

## SIH

Official portal:

``` text
https://sih.gov.in/sih2026PS
```

SIH26162:

``` text
AI-Based Detection and Classification of Industrial Fires and Persistent Thermal Sources Using NASA FIRMS, OSM & Satellite Data
```

Official deliverables:

1.  industrial-fire classification/segregation from forest/natural
    fires;
2.  GIS storage and visualization as a map overlay.

The project metadata must use:

``` text
Organization: NTRO
Category: Software
Theme: Miscellaneous
```

## NASA FIRMS

``` text
https://firms.modaps.eosdis.nasa.gov/active_fire/
```

``` text
https://firms.modaps.eosdis.nasa.gov/content/active_fire/
```

NASA documentation must be treated as authoritative for FIRMS behavior.

Important principle:

``` text
FIRMS detection ≠ confirmed industrial fire
```

NASA notes that active-fire/thermal-anomaly detections may represent
fire, hot smoke, agriculture or other sources and that spatial
resolution/view geometry/confidence matter.

## Sentinel-2

``` text
https://www.esa.int/Applications/Observing_the_Earth/Copernicus/Sentinel-2
```

## Landsat

``` text
https://www.usgs.gov/landsat-missions/landsat-collection-2
```

## HLS

``` text
https://hls.gsfc.nasa.gov/
```

## ESA WorldCover

``` text
https://esa-worldcover.org/en
```

WorldCover provides global 10 m land-cover products for 2020 and 2021.

## OpenStreetMap

``` text
https://www.openstreetmap.org/
```

## Overpass

``` text
https://wiki.openstreetmap.org/wiki/Overpass_API
```

## OGC STAC

``` text
https://www.ogc.org/standards/stac/
```

STAC standardizes metadata/cataloguing for spatiotemporal geospatial
assets.

------------------------------------------------------------------------

# 6. Ground-Truth Strategy

Ground truth is a first-class engineering dependency.

Build a **reference event registry**.

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

## Label hierarchy

### Tier A --- authoritative

-   government/official incident reports;
-   credible regulatory records;
-   company incident disclosures where appropriate.

### Tier B --- strong independent evidence

-   reputable reporting with time/location;
-   multiple independent sources;
-   validated reference databases.

### Tier C --- weak/proxy

-   OSM proximity;
-   inferred context;
-   unsourced reports.

Tier C may support exploration or weak supervision but must not be
treated as equivalent to hard ground truth.

------------------------------------------------------------------------

# 7. Ground-Truth Feasibility Gate

Before committing to a complex ML model, determine:

-   selected geography;
-   historical period;
-   number of candidate events;
-   number of high-confidence labelled events;
-   class distribution;
-   spatial coverage;
-   temporal coverage;
-   label provenance distribution.

If sufficient labels do not exist:

``` text
reduce taxonomy
→ use deterministic baselines
→ use weak supervision for exploration only
→ keep uncertainty explicit
```

Never manufacture labels to satisfy a target metric.

------------------------------------------------------------------------

# 8. Ontology Freeze Gate

Before training:

Freeze:

``` text
phenomenon
context
persistence
attribution
```

Do not mix them into one flat label.

Example:

``` text
phenomenon = flare
context = oil_gas
persistence = persistent
attribution = strong
```

------------------------------------------------------------------------

# 9. Event and Source Semantics

Do not train directly on raw FIRMS points when the operational task is
event/source intelligence.

Use:

``` text
detections
→ events
→ persistent sources
```

All split logic must operate at the correct entity level.

------------------------------------------------------------------------

# 10. Baseline-First Rule

Before ML:

``` text
Baseline 1: FIRMS confidence
Baseline 2: industrial proximity
Baseline 3: persistence
Baseline 4: combined deterministic rules
```

Then:

``` text
simple feature model
→ XGBoost/LightGBM
```

Only introduce deep vision if error analysis shows the baseline/tabular
model is insufficient and enough labelled data exists.

------------------------------------------------------------------------

# 11. Leakage Prevention

Never use a random point-level split for the final benchmark.

Prevent:

-   spatial leakage;
-   temporal leakage;
-   event leakage;
-   persistent-source leakage;
-   duplicated observation leakage.

Preferred:

``` text
geographic holdout
+
temporal holdout
+
source/event grouping
```

------------------------------------------------------------------------

# 12. Mandatory Ablation Study

Run:

``` text
A: FIRMS only
B: FIRMS + temporal
C: FIRMS + temporal + industrial context
D: FIRMS + temporal + land cover
E: FIRMS + satellite
F: all evidence
```

Purpose:

-   determine which evidence adds value;
-   detect shortcut learning;
-   quantify context contribution;
-   justify complexity.

------------------------------------------------------------------------

# 13. Context Shortcut Test

Specifically test:

> Can the model classify industrial events almost entirely from
> proximity to an industrial facility?

If yes, investigate whether it is learning:

``` text
facility proximity
```

instead of:

``` text
thermal phenomenon
```

The system must remain useful when context is incomplete.

------------------------------------------------------------------------

# 14. Model Evaluation

Report:

-   precision;
-   recall;
-   macro F1;
-   PR-AUC where appropriate;
-   calibration;
-   selective risk/coverage;
-   false-positive rate;
-   persistence-source F1;
-   spatial attribution error where valid;
-   latency.

Accuracy is supplementary, not the sole metric.

------------------------------------------------------------------------

# 15. Coverage and Abstention

Abstention is valid.

The model may output:

``` text
unknown / uncertain
```

when evidence is insufficient.

Do not force coverage toward 95% if it materially degrades reliability.

Use:

``` text
risk vs coverage
```

to show the trade-off.

------------------------------------------------------------------------

# 16. Satellite Strategy

Satellite imagery is a required integration capability but not a
mandatory evidence source for every event.

Use:

``` text
Tier 1: FIRMS + temporal + spatial
Tier 2: land cover + industrial context
Tier 3: satellite imagery when available
Tier 4: advanced vision only if justified
```

Missing satellite imagery must be represented explicitly.

------------------------------------------------------------------------

# 17. Evidence Strategy

Evidence is generated from verified data.

The evidence engine must be deterministic.

Example:

``` text
Evidence:
+ 19 active days
+ stable spatial footprint
+ industrial facility within configured threshold
- optical imagery unavailable
```

Never allow an LLM to invent evidence.

If an LLM is later used, it may summarize already-validated evidence but
cannot create facts.

------------------------------------------------------------------------

# 18. Performance Target Discipline

Team targets from the conceptual benchmark sheet are treated as
**stretch engineering targets**, not official SIH requirements.

Do not claim:

-   95% accuracy;
-   95% precision;
-   95% recall;
-   \<500 m attribution error;
-   \<2 min latency

until a valid benchmark demonstrates them.

Define the metric before measuring it.

------------------------------------------------------------------------

# 19. Development Sequence

### Phase 0 --- Scientific contract

-   ontology
-   event semantics
-   ground truth schema
-   benchmark protocol
-   geospatial error definition

### Phase 1 --- Data spine

-   FIRMS ingestion
-   raw storage
-   validation
-   deduplication
-   PostGIS

### Phase 2 --- Event intelligence

-   clustering
-   persistence

### Phase 3 --- Context

-   OSM
-   land cover
-   satellite catalog/context

### Phase 4 --- Baseline ML

-   deterministic baselines
-   feature model
-   XGBoost/LightGBM
-   calibration
-   ablation

### Phase 5 --- Evidence

-   evidence engine
-   uncertainty
-   provenance

### Phase 6 --- GIS

-   map APIs
-   event details
-   timelines
-   source monitoring

### Phase 7 --- Advanced model

Only if justified by measured error.

------------------------------------------------------------------------

# 20. Definition of Done for Every Unit

Before moving to the next unit:

1.  current unit works end-to-end within scope;
2.  tests exist;
3.  architecture invariants hold;
4.  provenance is preserved;
5.  uncertainty is preserved;
6.  documentation is updated;
7.  progress tracker is updated;
8.  build passes;
9.  no unverified assumption has silently become a requirement.

------------------------------------------------------------------------

# 21. Protected Decisions

Do not weaken these rules for a faster demo:

-   FIRMS is not ground truth.
-   OSM is context, not ground truth.
-   raw observations remain immutable.
-   spatial/temporal/source leakage is prohibited.
-   abstention is valid.
-   evidence must be data-backed.
-   geospatial precision must be honest.
-   ML must beat a meaningful baseline before adding complexity.
