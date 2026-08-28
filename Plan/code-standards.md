# SIH26162 --- Code Standards

## 1. Core Engineering Principles

1.  Prefer correctness over cleverness.
2.  Keep modules small and single-purpose.
3.  Fix root causes instead of layering workarounds.
4.  Separate API, data access, geospatial transformation, feature
    engineering and ML logic.
5.  Every important transformation must be independently testable.
6.  Preserve source provenance.
7.  Make uncertainty explicit.
8.  Never hide external API failures.
9.  Prefer deterministic processing where possible.
10. Avoid infrastructure without a measured need.
11. Never optimize a benchmark by changing the evaluation protocol.
12. Never encode a contextual shortcut as a factual label.
13. Do not silently turn observations into ground truth.
14. Do not claim geographic precision beyond the source data.

------------------------------------------------------------------------

# 2. Python

Required:

-   Python 3.11+ unless dependency constraints require otherwise.
-   Type hints for public functions.
-   Ruff for linting/formatting.
-   Pytest for tests.
-   Pydantic for external data validation.
-   Mypy or equivalent for critical modules.

Avoid:

-   untyped dictionaries across boundaries;
-   global mutable state;
-   hidden network calls;
-   giant utility modules;
-   `except Exception: pass`;
-   silent coercion of malformed data;
-   model code that reads directly from production tables without an
    explicit feature/data-access boundary.

------------------------------------------------------------------------

# 3. TypeScript

Required:

-   strict TypeScript;
-   no unnecessary `any`;
-   typed API responses;
-   runtime validation for unknown external payloads;
-   shared schemas where practical.

Frontend state must distinguish:

-   server state;
-   map state;
-   UI state.

Do not put the entire application state into one global store.

------------------------------------------------------------------------

# 4. Data Contracts

Every external source receives a canonical internal schema.

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

Vendor-specific field names must not leak through the application.

------------------------------------------------------------------------

# 5. Domain Model Rules

The following are different entities:

``` text
Detection
Event
Persistent Source
Context
Intelligence Result
```

Do not collapse them into one record.

A detection belongs to an event only through the event-formation
process.

A source is a longer-lived entity linked to multiple events.

Context does not automatically become a label.

------------------------------------------------------------------------

# 6. Ontology Rules

Never use one field such as:

``` text
class = "persistent_gas_flare"
```

as the only representation.

Use orthogonal fields:

``` text
phenomenon = flare
context = oil_gas
persistence_state = persistent
attribution_strength = strong
```

This prevents mixing fundamentally different concepts.

------------------------------------------------------------------------

# 7. Geospatial Standards

Use:

-   `EPSG:4326` for API interchange where appropriate.
-   PostGIS geography/geodesic calculations or suitable projected CRS
    for distance/area.

Never calculate precise meter distances using naïve latitude/longitude
Euclidean arithmetic.

Never assign:

``` text
event.location = facility.location
```

unless an independently defensible relationship exists.

Store:

``` text
detection_geometry
event_geometry
source_geometry
facility_geometry
distance
attribution_confidence
```

------------------------------------------------------------------------

# 8. FIRMS Data Rules

Every ingestion record must preserve:

-   source
-   satellite
-   instrument
-   acquisition timestamp
-   product type/version
-   original identifier/hash
-   ingestion timestamp
-   raw provenance

Rules:

1.  FIRMS is an observation source, not ground truth.
2.  Preserve NRT/RT/URT/standard identity.
3.  Do not silently overwrite raw observations.
4.  Cache immutable historical data where appropriate.
5.  Keep API credentials server-side.
6.  Respect rate/transaction limits.
7.  Distinguish acquisition time from processing/ingestion time.
8.  Never interpret a pixel centroid as an exact incident coordinate.

------------------------------------------------------------------------

# 9. External API Rules

Every integration must have:

-   timeout;
-   retry policy;
-   rate-limit handling;
-   structured error;
-   provenance metadata;
-   test fixture;
-   fallback behavior where meaningful.

Never hide external failure.

If satellite imagery is unavailable, the system must represent:

``` text
satellite_evidence_status = unavailable
```

rather than silently pretending imagery was analyzed.

------------------------------------------------------------------------

# 10. OSM / Context Rules

OSM is contextual evidence.

Allowed:

``` text
distance_to_industrial_facility
facility_type
nearby_infrastructure_count
```

Not allowed:

``` text
OSM facility nearby → confirmed industrial fire
```

Context features must be tested for shortcut learning.

Required experiment:

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

------------------------------------------------------------------------

# 11. ML Rules

1.  Establish a deterministic baseline first.
2.  Establish a simple feature baseline before complex models.
3.  Use grouped/spatial/temporal evaluation.
4.  Prevent source/event leakage.
5.  Calibrate probabilities where probabilities are exposed.
6.  Permit abstention.
7.  Track model version.
8.  Store feature/pipeline version.
9.  Preserve evaluation dataset version.
10. Never optimize for accuracy alone.
11. Do not force every event into a class.
12. Do not introduce deep vision without benchmark evidence.
13. Do not use an LLM as the primary classifier.
14. Do not train against weak labels and report them as
    hard-ground-truth performance.

------------------------------------------------------------------------

# 12. Ground-Truth Rules

Ground truth must have provenance.

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

Label tiers:

-   Tier A: authoritative
-   Tier B: strong independent evidence
-   Tier C: proxy/weak

Tier C must not be treated as equivalent to Tier A.

------------------------------------------------------------------------

# 13. Evaluation Rules

Random point-level splits are prohibited for the final benchmark.

Where possible:

-   hold out geography;
-   hold out time;
-   hold out persistent sources.

All test sets must be versioned.

Report:

-   precision;
-   recall;
-   macro F1;
-   PR-AUC where relevant;
-   calibration;
-   coverage/risk;
-   false-positive rate;
-   persistence-source performance;
-   latency.

Never change the split or label policy merely to improve a number.

------------------------------------------------------------------------

# 14. Evidence Rules

Evidence must be derived from verified system state.

Allowed:

``` text
"19 active days"
"facility within configured distance"
"stable spatial footprint"
"optical imagery unavailable"
```

Not allowed:

``` text
LLM-generated reason not supported by stored data
```

An LLM may summarize existing evidence only if the underlying facts are
already present and validated.

------------------------------------------------------------------------

# 15. Security

-   Secrets only in environment/secret storage.
-   Never expose FIRMS MAP_KEY or equivalent credentials to the browser.
-   Validate all external input.
-   Enforce authorization before mutations.
-   Log security-relevant failures.
-   Do not log credentials or sensitive tokens.
-   Keep audit/provenance metadata separate from user-facing prose.

------------------------------------------------------------------------

# 16. Testing

Every major pipeline stage needs tests.

Minimum:

-   schema validation tests;
-   FIRMS parsing fixtures;
-   deduplication tests;
-   CRS/distance tests;
-   event clustering tests;
-   persistence tests;
-   feature-generation tests;
-   API contract tests;
-   external API failure tests;
-   model inference tests;
-   calibration tests;
-   evidence correctness tests;
-   leakage tests.

Include synthetic fixtures for edge cases.

------------------------------------------------------------------------

# 17. File Organization

``` text
apps/
  web/

services/
  api/
    routes/
    schemas/
    services/
    repositories/

  worker/
    jobs/
    ingestion/
    enrichment/
    persistence/

  ml/
    features/
    training/
    evaluation/
    inference/
    calibration/

packages/
  schemas/
  geospatial/
  evidence/
```

The exact repository structure may evolve, but domain boundaries must
remain intact.

------------------------------------------------------------------------

# 18. Git Standards

Meaningful commits:

``` text
feat: add FIRMS ingestion schema
feat: add event clustering
feat: add OSM enrichment
feat: add persistence scoring
feat: add baseline classifier
test: add spatial holdout evaluation
```

Avoid:

``` text
stuff
changes
final
final2
```

------------------------------------------------------------------------

# 19. Protected Boundaries

Do not:

-   rewrite the architecture to solve one bug;
-   modify unrelated modules during feature work;
-   replace dependencies without justification;
-   change evaluation rules to improve benchmark numbers;
-   bypass validation to make a demo work;
-   hard-code a contextual assumption as a label.

------------------------------------------------------------------------

# 20. Definition of Done

A feature is complete only when:

-   code works end-to-end within its defined scope;
-   tests exist;
-   external failures are handled;
-   provenance is preserved;
-   uncertainty is preserved;
-   documentation is updated;
-   progress tracker is updated;
-   build passes;
-   no architecture invariant is violated.

------------------------------------------------------------------------

# 21. Anti-Patterns

### Bad

``` text
FIRMS → LLM → "Industrial Fire"
```

### Good

``` text
FIRMS
→ event formation
→ temporal/spatial features
→ context
→ deterministic baseline
→ ML
→ calibration
→ abstention
→ evidence
→ analyst
```

### Bad

``` text
Random train/test split
```

### Good

``` text
Spatial + temporal + source-grouped evaluation
```

### Bad

``` text
375 m pixel = exact facility
```

### Good

``` text
Observation + contextual relationship + uncertainty
```

### Bad

``` text
Industrial facility nearby = industrial fire
```

### Good

``` text
Industrial proximity = contextual evidence
```
