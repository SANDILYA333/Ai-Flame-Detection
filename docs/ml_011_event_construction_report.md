# ML-011 — Real Event Construction, Spatiotemporal Clustering & Persistent Thermal Source Tracking Report

**Milestone:** `ML-011`  
**Status:** `COMPLETE & SCIENTIFICALLY AUDITED`  
**Verification Date:** `2026-08-30`  
**Test Suite Coverage:** `413 passed, 39 subtests passed (100% pass rate in 16.83s)`  
**Source Type Safety & Lint:** `0 errors across 182 source files`  

---

## 1. Objective

The objective of **ML-011** is to construct physically coherent, point-in-time consistent **Thermal Events** and **Persistent Thermal Sources** from canonical remote-sensing satellite detections (`ds_real_firms_v1.0.0` from `ML-010`), establishing strict anti-leakage guarantees and full observational provenance:
```
Real NASA FIRMS Canonical Detections (ds_real_firms_v1.0.0)
                        │
                        ▼
      ┌───────────────────────────────────┐
      │ Spatiotemporal Event Clustering   │
      │ (Geodesic Radius + Temporal Gap)  │
      └─────────────────┬─────────────────┘
                        │
                        ▼
                 Thermal Events
                        │
                        ▼
      ┌───────────────────────────────────┐
      │ Persistent Source Tracking        │
      │ (Geodesic Association + Calendar) │
      └─────────────────┬─────────────────┘
                        │
                        ▼
           Persistent Thermal Sources
                        │
                        ▼
      ┌───────────────────────────────────┐
      │ Point-in-Time History Engine      │
      │ (Zero Future Leakage at T_pred)   │
      └─────────────────┬─────────────────┘
                        │
                        ▼
  Real Thermal Event Dataset (ds_real_events_v1.0.0)
```

---

## 2. Existing Architecture Reused & Extended

Rather than duplicating abstractions, ML-011 leveraged and unified the existing domain and scientific pipeline modules:
1. **`packages/events/clustering.py`**: `cluster_detections_spatiotemporal()` executing deterministic BFS graph connected components over time-sorted detections using geodesic distance.
2. **`packages/events/builder.py`**: `build_event_from_cluster()` and `generate_deterministic_event_id()`.
3. **`packages/sources/tracking.py`**: `group_events_into_sources()` grouping events within longitudinal spatial association radii.
4. **`packages/sources/classification.py`**: `classify_persistence_state()`, `calculate_active_calendar_days()`, and `calculate_recurrence_ratio()`.
5. **`packages/schemas/event.py`**: Canonical `Event` and `RealThermalEventDataset` domain containers.
6. **`packages/schemas/source.py`**: Canonical `PersistentSource` domain model.
7. **`packages/config/scientific.py`**: `ScientificConfig` containing authoritative clustering and persistence parameters.

---

## 3. Core Domain Models

| Domain Concept | Definition | Key Attributes | Provenance & Anti-Leakage Rules |
| :--- | :--- | :--- | :--- |
| **Detection** | A single remote-sensing satellite thermal observation at a point in time. | `detection_id`, `acquired_at`, `geometry`, `satellite`, `instrument`, `frp_mw`, `brightness_ti4_k` | Immutable source observation. |
| **Thermal Event** | A spatiotemporally coherent cluster of detections representing one observable heating episode. | `event_id`, `detection_ids`, `started_at`, `ended_at`, `duration_seconds`, `centroid_geometry`, `mean_frp_mw` | `event_id` is a deterministic SHA-256 fingerprint over sorted `detection_ids` + config fingerprint. Zero reliance on facility or label IDs. |
| **Persistent Source** | A recurring spatial entity associated with multiple events over longitudinal time. | `source_id`, `linked_event_ids`, `first_seen_at`, `last_seen_at`, `active_days_count`, `recurrence_ratio`, `persistence_state` | `source_id` is a deterministic SHA-256 fingerprint over sorted `event_ids`. Decoupled from physical facility identity. |

---

## 4. Spatiotemporal Event Clustering Algorithm

1. **Deterministic Sorting:** Input detections are sorted by `(acquired_at.timestamp(), latitude, longitude, detection_id)`.
2. **Geodesic Adjacency Evaluation:** Pairs of detections within `temporal_window_hours` are evaluated for geodesic proximity using Haversine distance in meters.
3. **Connected Components:** Deterministic Breadth-First Search (BFS) groups transitively connected detections into event clusters.
4. **Deterministic Ordering:** Formed clusters are sorted by earliest acquisition timestamp and centroid coordinates.

### Configuration Defaults (`ScientificConfig`):
- **`spatial_cluster_radius_meters`**: $1000.0\,\text{m}$ ($1.0\,\text{km}$)
- **`temporal_window_hours`**: $2.0\,\text{hours}$
- **`persistence_threshold_days`**: $30.0\,\text{days}$
- **`persistence_min_observations`**: $5\,\text{active days / events}$

---

## 5. Point-in-Time Temporal Anti-Leakage Engine

When evaluating or generating features for an event at prediction timestamp $T_{\text{prediction}}$:
1. **`construct_point_in_time_events()`**: Strictly filters input detections by $t_{\text{detection}} \le T_{\text{prediction}}$. Future satellite overpasses ($t > T_{\text{prediction}}$) cannot alter member detection count, event duration, spatial centroid, or FRP statistics.
2. **`get_point_in_time_source_history()`**: Strictly filters events by $\text{event.ended\_at} \le T_{\text{prediction}}$. Future events cannot inflate historical `active_days_count`, `total_event_count`, or change `persistence_state`.

---

## 6. End-to-End Real Fixture Demonstration Results

Using the canonical NASA FIRMS Jamnagar pilot dataset (`fixtures/firms/firms_real_sample_jamnagar.csv`):
- **Input Detections:** $6$ canonical remote-sensing detections.
- **Derived Thermal Events:** $4$ events.
- **Derived Persistent Sources:** $3$ sources.
- **Earliest Event Start:** `2026-08-01T08:30:00Z`
- **Latest Event End:** `2026-08-03T20:00:00Z`
- **Canonical Dataset Hash:** `7949c45ae948c91ce26558ccdc1610fd4e49da68d63f939a8a1543b399af4b4a`

---

## 7. Sample Derived Event & Persistent Source Records

### Sample Thermal Event:
```json
{
  "event_id": "evt_855e5115b33c35ed3493a6ba",
  "detection_ids": ["det_2e0d46370eeda1ca", "det_30c051878cd779cd"],
  "detection_count": 2,
  "started_at": "2026-08-01T08:30:00Z",
  "ended_at": "2026-08-01T08:30:00Z",
  "duration_seconds": 0.0,
  "centroid_geometry": {
    "latitude": 22.4506,
    "longitude": 70.0516
  },
  "mean_frp_mw": 35.3,
  "max_frp_mw": 42.1,
  "formation_configuration_id": "pilot_jamnagar_flaring",
  "formation_configuration_version": "v1.0.0-pilot"
}
```

### Sample Persistent Source:
```json
{
  "source_id": "src_7afc428b4bdc49955da6cac6",
  "linked_event_ids": ["evt_855e5115b33c35ed3493a6ba", "evt_9b05bcc617e6f6f25af9c649"],
  "total_event_count": 2,
  "centroid_geometry": {
    "latitude": 22.4506,
    "longitude": 70.0516
  },
  "first_seen_at": "2026-08-01T08:30:00Z",
  "last_seen_at": "2026-08-01T20:15:00Z",
  "active_days_count": 1,
  "persistence_state": "transient",
  "recurrence_ratio": 1.0,
  "persistence_configuration_id": "pilot_jamnagar_flaring",
  "persistence_configuration_version": "v1.0.0-pilot"
}
```

---

## 8. Complete Verification Results

- **`ruff format --check .`**: 206 files formatted cleanly.
- **`ruff check .`**: All checks passed (0 lint errors).
- **`mypy .`**: Success: no issues found in 182 source files.
- **`pytest`**: 413 passed, 39 subtests passed in 16.83s (100% pass rate).
- **`scripts/run_ml_011_event_construction.py`**: Clean execution with verified reload integrity.

---

## 9. Invariants & Scientific Constraints

> **CRITICAL SCIENTIFIC INVARIANTS:**
> 1. **Persistence $\neq$ Industrial Causation:** A persistent thermal source is an observed temporal pattern (e.g. repeated heat detections at a stationary location). It does NOT constitute physical proof of an industrial refinery flare or furnace.
> 2. **Observational Events $\neq$ Ground-Truth Labels:** `RealThermalEventDataset` contains physical observation clusters; it does NOT contain ground-truth class labels.
> 3. **No Model Accuracy Claim:** ML-011 does NOT measure or claim operational classification accuracy on real-world events.

---

## 10. Readiness for ML-012

The canonical real thermal event dataset (`ds_real_events_v1.0.0`) and point-in-time history engine are fully verified. The repository is ready for **ML-012: Real-Data Contextual Enrichment & Reference Label Adjudication** to attach multi-source external evidence (OSM, GEM, WRI) to these physical event clusters.
