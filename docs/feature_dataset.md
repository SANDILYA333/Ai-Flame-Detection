# SIH26162 Phase 4 — Feature Dataset Construction & Leakage-Safe Feature Engineering (ML-002)

## 1. Overview & Objectives

Milestone **ML-002** operationalizes the ML-readiness foundations established in **ML-001** by transforming upstream evidence (`Detection`, `Event`, `PersistentSource`, `ContextEvidence`) into a versioned, content-addressable, and scientifically defensible **Feature Dataset**.

### Core Guarantees:
1. **Prediction Unit**: `Event` — the physical unit of prediction aggregating member detections knowable as of prediction timestamp $T_{prediction}$.
2. **Strict Temporal Cutoff**: For every observation $obs$, $\text{availability\_time}(obs) \le T_{prediction}$. Detections or events after $T_{prediction}$ are strictly excluded.
3. **Identifier Separation**: Identifiers (`event_id`, `source_id`, `detection_id`, `facility_id`) are preserved strictly in metadata and group keys; they are **never** present in the model `features` dictionary.
4. **Missingness Preservation ($missing \neq zero$)**: Missing features are preserved as `None` in the feature dictionary, accompanied by explicit boolean missingness flags (`f"{feature_name}_is_missing"`).
5. **Showcase Isolation (`DATASET-003`)**: Permanent benchmark isolation of showcase events (e.g. Jamnagar complex) to prevent data snooping.
6. **Ablation Grouping**: Features are organized into logical groups (`THERMAL_CORE`, `TEMPORAL_HISTORY`, `PERSISTENCE_SOURCE`, `SPATIAL_CONTEXT`, `LAND_COVER`) enabling ablation studies.

---

## 2. Feature Architecture

```text
       ┌───────────────────────┐
       │   NASA FIRMS NRT      │
       └───────────┬───────────┘
                   │
                   ▼
       ┌───────────────────────┐
       │  Canonical Detection  │ (lat, lon, FRP, brightness, acquired_at, sat, inst, day/night)
       └───────────┬───────────┘
                   │
                   ▼
       ┌───────────────────────┐
       │    Canonical Event    │ (spatiotemporal cluster, duration, FRP aggregates, centroid)
       └───────────┬───────────┘
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
┌─────────────────┐ ┌─────────────────┐
│Persistent Source│ │ Context Evidence│ (OSM, WRI, WDPA, ESA WorldCover)
└────────┬────────┘ └────────┬────────┘
         │                   │
         └─────────┬─────────┘
                   │
                   ▼
       ┌───────────────────────┐
       │   FeatureExtractor    │ (Enforces T_prediction cutoff, missingness, purity)
       └───────────┬───────────┘
                   │
                   ▼
       ┌───────────────────────┐
       │ FeatureDatasetBuilder │ (Audits duplicates, isolates showcase, computes SHA-256)
       └───────────┬───────────┘
                   │
                   ▼
       ┌───────────────────────┐
       │    FeatureDataset     │ (Manifest, FeatureRecords, Ablation Groups, Diagnostics)
       └───────────────────────┘
```

---

## 3. Approved Standard Feature Catalog (`feat_v1.0.0`)

| Feature Name | Feature Group | Source Entity | Physical Unit | Lag (s) | Missingness Semantics | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `detection_count` | `THERMAL_CORE` | Event | count | 0.0 | PRESERVE_NONE | **APPROVED** |
| `frp_mean_mw` | `THERMAL_CORE` | Event | MW | 0.0 | PRESERVE_NONE | **APPROVED** |
| `frp_max_mw` | `THERMAL_CORE` | Event | MW | 0.0 | PRESERVE_NONE | **APPROVED** |
| `frp_min_mw` | `THERMAL_CORE` | Event | MW | 0.0 | PRESERVE_NONE | **APPROVED** |
| `frp_sum_mw` | `THERMAL_CORE` | Event | MW | 0.0 | PRESERVE_NONE | **APPROVED** |
| `frp_std_mw` | `THERMAL_CORE` | Event | MW | 0.0 | PRESERVE_NONE | **APPROVED** |
| `duration_hours` | `THERMAL_CORE` | Event | hours | 0.0 | PRESERVE_NONE | **APPROVED** |
| `temporal_density` | `THERMAL_CORE` | Event | detections/hour | 0.0 | PRESERVE_NONE | **APPROVED** |
| `brightness_mean_kelvin` | `THERMAL_CORE` | Detection | Kelvin | 0.0 | PRESERVE_NONE | **APPROVED** |
| `brightness_max_kelvin` | `THERMAL_CORE` | Detection | Kelvin | 0.0 | PRESERVE_NONE | **APPROVED** |
| `spatial_extent_radius_meters` | `THERMAL_CORE` | Event | meters | 0.0 | PRESERVE_NONE | **APPROVED** |
| `daynight_ratio` | `THERMAL_CORE` | Detection | ratio | 0.0 | PRESERVE_NONE | **APPROVED** |
| `satellite_platform_diversity` | `THERMAL_CORE` | Detection | count | 0.0 | PRESERVE_NONE | **APPROVED** |
| `sensor_instrument` | `THERMAL_CORE` | Detection | — | 0.0 | PRESERVE_NONE | **APPROVED** |
| `prior_event_count_24h` | `TEMPORAL_HISTORY` | Event | count | 0.0 | PRESERVE_NONE | **APPROVED** |
| `prior_event_count_7d` | `TEMPORAL_HISTORY` | Event | count | 0.0 | PRESERVE_NONE | **APPROVED** |
| `prior_event_count_30d` | `TEMPORAL_HISTORY` | Event | count | 0.0 | PRESERVE_NONE | **APPROVED** |
| `time_since_previous_event_hours` | `TEMPORAL_HISTORY` | Event | hours | 0.0 | EXPLICIT_INDICATOR | **APPROVED** |
| `persistence_active_days` | `PERSISTENCE_SOURCE` | Source | days | 0.0 | PRESERVE_NONE | **APPROVED** |
| `persistence_total_events` | `PERSISTENCE_SOURCE` | Source | events | 0.0 | PRESERVE_NONE | **APPROVED** |
| `persistence_recurrence_ratio` | `PERSISTENCE_SOURCE` | Source | ratio | 0.0 | EXPLICIT_INDICATOR | **APPROVED** |
| `is_persistent_source` | `PERSISTENCE_SOURCE` | Source | — | 0.0 | PRESERVE_NONE | **APPROVED** |
| `persistence_state` | `PERSISTENCE_SOURCE` | Source | — | 0.0 | PRESERVE_NONE | **APPROVED** |
| `facility_distance_meters` | `SPATIAL_CONTEXT` | Context | meters | 0.0 | EXPLICIT_INDICATOR | **APPROVED** |
| `facility_context_type` | `SPATIAL_CONTEXT` | Context | — | 0.0 | EXPLICIT_INDICATOR | **APPROVED** |
| `is_near_industrial_facility` | `SPATIAL_CONTEXT` | Context | — | 0.0 | PRESERVE_NONE | **APPROVED** |
| `power_plant_distance_meters` | `SPATIAL_CONTEXT` | Context | meters | 0.0 | EXPLICIT_INDICATOR | **APPROVED** |
| `landcover_class` | `LAND_COVER` | Context | — | 0.0 | EXPLICIT_INDICATOR | **APPROVED** |
| `is_protected_area` | `LAND_COVER` | Context | — | 0.0 | PRESERVE_NONE | **APPROVED** |
| `water_distance_meters` | `SPATIAL_CONTEXT` | Context | meters | 0.0 | EXPLICIT_INDICATOR | **APPROVED** |

---

## 4. Disqualified Candidate Features Audit

| Candidate Feature | Eligibility Status | Leakage Risk | Scientific Rationale |
| :--- | :--- | :--- | :--- |
| `reference_class` | `LABEL_REFERENCE` | `DIRECT_LEAKAGE` | Target label; direct leakage into model input. |
| `label_confidence` | `LABEL_REFERENCE` | `DIRECT_LEAKAGE` | Target metadata; directly correlates with reference class. |
| `mcd64a1_burned_area` | `VALIDATION_ONLY` | `TEMPORAL_LEAKAGE` | Post-event outcome product; unavailable at inference time. |
| `future_event_duration` | `REJECTED` | `TEMPORAL_LEAKAGE` | Requires future event detections after $T_{prediction}$. |
| `final_detection_count` | `REJECTED` | `TEMPORAL_LEAKAGE` | Requires future event detections after $T_{prediction}$. |
| `raw_event_id` | `REJECTED` | `SAFE` | Memorization shortcut; entity IDs must not be features. |
| `raw_source_id` | `REJECTED` | `SAFE` | Memorization shortcut; source IDs must be group keys only. |
| `raw_facility_id` | `REJECTED` | `SAFE` | Memorization shortcut; external IDs prevent generalization. |
| `raw_latitude` | `BLOCKED` | `SPATIAL_LEAKAGE` | Spatial shortcut memorization without physics. |
| `raw_longitude` | `BLOCKED` | `SPATIAL_LEAKAGE` | Spatial shortcut memorization without physics. |

---

## 5. Ablation Studies Configuration

The `FeatureDataset` automatically segments features into ablation groups to facilitate controlled experiments in downstream milestones:

1. **Ablation Baseline: FIRMS Only (`THERMAL_CORE`)**:
   - `detection_count`, `frp_mean_mw`, `frp_max_mw`, `frp_min_mw`, `frp_sum_mw`, `frp_std_mw`, `duration_hours`, `temporal_density`, `brightness_mean_kelvin`, `brightness_max_kelvin`, `spatial_extent_radius_meters`, `daynight_ratio`, `satellite_platform_diversity`, `sensor_instrument`.
2. **Ablation Slice: FIRMS + Temporal History (`THERMAL_CORE` + `TEMPORAL_HISTORY`)**:
   - Adds `prior_event_count_24h`, `prior_event_count_7d`, `prior_event_count_30d`, `time_since_previous_event_hours`.
3. **Ablation Slice: FIRMS + Persistence (`THERMAL_CORE` + `PERSISTENCE_SOURCE`)**:
   - Adds `persistence_active_days`, `persistence_total_events`, `persistence_recurrence_ratio`, `is_persistent_source`, `persistence_state`.
4. **Ablation Slice: Full Multimodal (`ALL_GROUPS`)**:
   - Incorporates `SPATIAL_CONTEXT` and `LAND_COVER`.

---

## 6. Verification & Test Suite

All feature extraction, missingness handling, showcase isolation, and leakage safety guarantees are validated in continuous integration:
- `tests/test_ml_features_dataset.py`: 7 comprehensive test suites covering thermal core derivation, context integration, persistence features, missingness indicator preservation, dataset hashing determinism, showcase isolation (`DATASET-003`), duplicate rejection, and markdown/JSON reporting.
- `tests/test_ml_leakage_safety.py`: 5 adversarial test suites verifying future detection rejection, future preceding event rejection, identifier exclusion, candidate feature rejection by `LeakageAuditor`, and 100% clean audit on `APPROVED_FEATURES`.
