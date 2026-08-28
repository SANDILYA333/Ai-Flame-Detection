# SIH26162 — Code Standards

## 1. Core Engineering Principles

1. Prefer correctness over cleverness.
2. Keep modules small and single-purpose.
3. Fix root causes instead of layering workarounds.
4. Do not mix API, data access, ML and geospatial transformation logic in one module.
5. Every important data transformation must be testable independently.
6. Preserve provenance.
7. Make uncertainty explicit.
8. Never hide external API failures.
9. Prefer deterministic processing where possible.
10. Avoid introducing infrastructure without a measured need.

---

# 2. Python

## Required

- Python 3.11+ unless dependency constraints require otherwise.
- Type hints for public functions.
- `ruff` for linting/formatting.
- `pytest` for tests.
- Pydantic for external data validation.
- `mypy` or an equivalent static checker for critical modules.

## Avoid

- untyped dictionaries across system boundaries;
- global mutable state;
- hidden network calls;
- giant utility modules;
- `except Exception: pass`;
- silently coercing malformed data.

---

# 3. TypeScript

## Required

- strict TypeScript;
- no unnecessary `any`;
- typed API responses;
- shared schemas where practical;
- runtime validation for unknown external payloads.

## Frontend rule

Map state, server state and UI state should be separated.

Do not put the entire application state into one global store.

---

# 4. Data Contracts

Every external data source gets a canonical internal schema.

Example:

```python
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

Never allow vendor-specific field names to leak throughout the application.

---

# 5. Geospatial Standards

## Coordinate reference system

Use:

- `EPSG:4326` for API interchange where appropriate.
- Projected CRS for distance/area calculations.

Never calculate precise meter distances directly from latitude/longitude using naïve Euclidean distance.

Use:

- PostGIS geography;
- geodesic calculations;
- appropriate projected CRS.

---

# 6. Spatial Precision Rules

Never write:

```text
event.location = facility.location
```

unless the system has actual evidence for that relationship.

Instead store:

```text
detection_point
event_centroid
facility_geometry
distance_to_facility
attribution_confidence
```

This prevents false precision.

---

# 7. FIRMS Data Handling

Every ingestion record must preserve:

- source;
- satellite;
- acquisition timestamp;
- version;
- original identifier/hash;
- ingestion timestamp.

Do not mix:

- NRT;
- RT;
- URT;
- standard products

without recording the processing version.

---

# 8. External API Rules

Every external integration must have:

- timeout;
- retry policy;
- rate-limit handling;
- structured error;
- provenance metadata;
- test fixture;
- fallback behavior.

Never make an external API call from a request handler if the operation can be asynchronous.

---

# 9. NASA FIRMS Rules

1. Store the MAP_KEY only in server-side secrets.
2. Never expose it to the browser.
3. Respect NASA transaction limits.
4. Avoid repeated downloads of unchanged data.
5. Cache immutable historical results.
6. Record the source/version.
7. Distinguish data latency from processing latency.
8. Treat FIRMS as an observation source, not ground truth.

---

# 10. OSM Rules

OSM is contextual.

Do not interpret:

```text
OSM says industrial
```

as:

```text
there is definitely an active industrial fire.
```

Store:

- OSM object ID;
- tags;
- geometry;
- retrieval time;
- query parameters.

OSM data may be incomplete or outdated.

---

# 11. Satellite Data Rules

For every satellite asset record:

```text
source
collection
acquisition_time
processing_level
cloud metadata
geometry
asset URL
retrieval_time
```

Never silently substitute one satellite product for another.

If a requested image is unavailable:

```text
satellite_evidence.status = unavailable
```

not:

```text
satellite_evidence = inferred
```

---

# 12. ML Code Standards

## Separation

Keep:

```text
features/
training/
evaluation/
inference/
calibration/
explainability/
```

separate.

## Reproducibility

Record:

- dataset version;
- feature version;
- model version;
- random seed;
- training date;
- evaluation split;
- hyperparameters.

---

# 13. Data Leakage Rules

This is one of the highest-risk areas.

Never perform:

```text
random row split
```

when repeated detections from the same source exist.

Prefer grouped/spatial/temporal splits.

Every evaluation report must state:

```text
split strategy
grouping key
train period
test period
geographic separation
```

---

# 14. Model Output Contract

Every prediction must contain:

```text
model_version
predicted_class
probabilities
confidence
abstained
top_evidence
uncertainty
timestamp
```

A model that returns only a class label is not acceptable.

---

# 15. Explainability Rules

The explanation must be generated from actual features.

Allowed:

- SHAP feature contribution;
- feature thresholds;
- temporal statistics;
- spatial relationships;
- evidence records.

Not allowed:

- an LLM inventing a reason;
- text claims not traceable to source data.

---

# 16. Confidence Rules

Confidence is not the same as correctness.

The project must distinguish:

- model probability;
- calibrated confidence;
- data quality;
- evidence completeness.

Example:

```text
Model confidence: 0.93
Evidence completeness: 0.61
Final analyst confidence: moderate
```

This is preferable to a single misleading 93% number.

---

# 17. Evidence Completeness

Define evidence completeness as:

```text
available expected evidence / expected evidence
```

Possible evidence slots:

- FIRMS
- temporal
- spatial
- infrastructure
- land cover
- satellite

A missing satellite image should reduce evidence completeness but should not automatically invalidate the event.

---

# 18. Testing

## Unit tests

Test:

- coordinate validation;
- event clustering;
- persistence calculation;
- feature construction;
- confidence logic;
- evidence generation.

## Integration tests

Test:

- FIRMS fixture → database;
- OSM fixture → enrichment;
- event → prediction;
- prediction → evidence;
- API → PostGIS.

## End-to-end test

Use a fixed historical event fixture.

```text
input FIRMS
→ event
→ enrichment
→ model
→ evidence
→ API response
```

---

# 19. Data Tests

Validate:

- null rates;
- coordinate bounds;
- timestamp validity;
- duplicate rate;
- impossible FRP values;
- invalid confidence values;
- geometry validity.

---

# 20. Model Tests

Every model release must have:

- confusion matrix;
- precision/recall/F1;
- PR-AUC;
- calibration;
- per-class metrics;
- error analysis;
- spatial holdout;
- temporal holdout.

---

# 21. API Standards

Every route:

1. validates inputs;
2. authenticates where required;
3. authorizes access;
4. calls service layer;
5. returns typed response.

Do not put business logic directly in route handlers.

---

# 22. Error Handling

Use predictable errors:

```json
{
  "error": {
    "code": "SATELLITE_DATA_UNAVAILABLE",
    "message": "No valid contextual imagery was available for this event.",
    "retryable": false
  }
}
```

Never expose internal stack traces.

---

# 23. Logging

Structured logs should include:

```text
timestamp
service
event_id
request_id
operation
duration_ms
status
error_code
```

Do not log:

- API keys;
- credentials;
- unnecessary personal information;
- full large payloads.

---

# 24. Database Rules

- migrations only;
- no manual production schema edits;
- indexes for spatial/time queries;
- foreign keys where meaningful;
- geometry constraints;
- timestamps in UTC;
- soft deletion only when justified.

---

# 25. Spatial Indexing

Use PostGIS spatial indexes for:

- FIRMS detections;
- event geometry;
- industrial assets;
- persistent sources.

Common query pattern:

```text
find industrial assets within radius of event
```

must use a spatial index.

---

# 26. Performance

Do not optimize prematurely.

Measure first.

Optimize in this order:

1. repeated external downloads;
2. database queries;
3. raster processing;
4. Python loops;
5. serialization;
6. model inference.

Prefer vectorized geospatial operations.

---

# 27. File Organization

```text
services/api/
  routes/
  schemas/
  services/
  repositories/

services/worker/
  jobs/
  ingestion/
  enrichment/
  persistence/

services/ml/
  features/
  training/
  evaluation/
  inference/
  calibration/

packages/geospatial/
packages/evidence/
```

---

# 28. Git Standards

Commit units should be meaningful:

```text
feat: add FIRMS ingestion schema
feat: add event clustering
feat: add OSM enrichment
feat: add persistence scoring
feat: add baseline classifier
test: add spatial holdout evaluation
```

Avoid commits such as:

```text
stuff
changes
final
final2
```

---

# 29. Protected Boundaries

Do not:

- rewrite the entire architecture to solve one bug;
- modify unrelated modules during feature work;
- replace working dependencies without justification;
- change model evaluation rules to improve a benchmark number.

---

# 30. Definition of Done

A feature is complete only when:

- code works;
- tests exist;
- external failures are handled;
- provenance is preserved;
- documentation is updated;
- progress tracker is updated;
- build passes;
- no architecture invariant is violated.

---

# 31. Anti-Patterns

### Bad

```text
FIRMS → LLM → "Industrial Fire"
```

### Good

```text
FIRMS
→ temporal/spatial features
→ infrastructure/land context
→ ML/rules
→ calibration
→ evidence
→ analyst
```

### Bad

```text
Random train/test split
```

### Good

```text
Spatial + temporal + source-grouped evaluation
```

### Bad

```text
375 m pixel = exact facility
```

### Good

```text
pixel/detection + contextual relationship + uncertainty
```
