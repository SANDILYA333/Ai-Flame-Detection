# SIH26162 Phase 4 — Dataset Card: Supervised Thermal Intelligence Dataset

## 1. Dataset Summary

- **Dataset Identifier**: `ds_sih26162_supervised_v1.0.0`
- **Target Specification Version**: `target_v1.0.0`
- **Feature Set Version**: `feat_v1.0.0`
- **Unit of Prediction**: `Event` (Physical thermal anomaly cluster knowable as of prediction timestamp $T_{prediction}$).
- **Leakage Safeguards**: Strict temporal cutoff, identifier exclusion, group holdouts (`GROUPED_EVENT_HOLDOUT`, `PERSISTENT_SOURCE_HOLDOUT`), showcase isolation (`DATASET-003`).
- **Missingness Invariant**: Enforces $Missing \neq Negative$ and $Unknown \neq Negative$. Absence of reference evidence is preserved as `unknown`, never imputed or fabricated as negative ground truth.

---

## 2. Approved Prediction Targets

| Target ID | Name | Target Type | Prediction Unit | Class Vocabulary | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `target_thermal_phenomenon` | Thermal Phenomenon Classification | Multiclass | `Event` | `["flare", "industrial_thermal_source", "vegetation_wildfire", "agricultural_burn", "other_thermal_anomaly", "unknown"]` | **Approved** |
| `target_industrial_segregation` | Industrial vs Non-Industrial Segregation | Binary | `Event` | `["industrial", "non_industrial", "unknown"]` | **Approved** (SIH MUST) |
| `target_persistent_combustion` | Persistent Combustion Source | Binary | `Event` | `["persistent_source", "transient_event", "unknown"]` | **Approved** |

### Scientific Target Definitions:
1. **`target_industrial_segregation` (Official SIH26162 MUST Requirement)**:
   - **Positive (`industrial`)**: Confirmed or high-confidence physical industrial facility origin (refinery flare stack, petrochemical plant, furnace, power plant, smelter, kiln).
   - **Negative (`non_industrial`)**: Confirmed or high-confidence landscape origin (forest wildfire, brush fire, crop stubble burn, open bonfire).
   - **Unknown (`unknown`)**: Ambiguous contextual proximity, uncorroborated evidence, or conflicting reference reports.
2. **`target_thermal_phenomenon`**:
   - Classifies physical manifestation: flare combustion vs industrial process heat vs landscape wildfire vs agricultural burn.
3. **`target_persistent_combustion`**:
   - Classifies multi-day stationary physical recurrence vs transient single-day event.

---

## 3. Reference Evidence & Quality Tiers

Ground truth is ingested through auditable `ReferenceEvidence` records with explicit quality tiers:

| Tier | Name | Reliability Description | Example Sources | Treatment in Benchmark |
| :--- | :--- | :--- | :--- | :--- |
| **Tier A** | `TIER_A_AUTHORITATIVE` | High-confidence, validated ground truth | Official incident registries, field survey inspections, confirmed disaster management reports | Approved for Clean Evaluation Benchmark & Training |
| **Tier B** | `TIER_B_STRONG_EVIDENCE` | Multi-source consensus matching external registries | Global Energy Monitor (GEM), WRI Power Plants, VIIRS Nightfire (VNF) | Approved for Training & Proxy Evaluation |
| **Tier C** | `TIER_C_PROXY_WEAK` | Weak contextual proxy or heuristic inference | OSM distance bounds, single-threshold rules, Phase-3 deterministic rules | Weak supervision only; disqualified from clean evaluation |
| **Tier D** | `UNVERIFIED_HEURISTIC` | Provisional unverified heuristic | Experimental rule flags | Excluded from training and evaluation |
| **Tier U** | `UNKNOWN` | Absence of corroborating evidence | Entities with 0 matched reference records | Preserved as `UNKNOWN` ($Missing \neq Negative$) |

### Conflict Resolution Policy (`LabelConflictPolicy.TIER_PRECEDENCE`):
- Higher tiers strictly supersede lower tiers (e.g. Tier A overrides Tier C).
- Contradictory evidence at the same quality tier resolves to `UNKNOWN` with `has_conflicting_evidence = True` and exclusion from clean training sets (`ExclusionReason.CONFLICTING_LABEL_EVIDENCE`).

---

## 4. Evaluation Partitioning & Leakage Protections

The dataset provides 4 leakage-safe partition strategies evaluated by `SplitIntegrityValidator`:

1. **`GROUPED_EVENT_HOLDOUT`**:
   - Partitions data at the `event_id` level.
   - Zero member detections or duplicate views of the same physical event cross train/val/test partitions ($Train \cap Val = \emptyset$, $Train \cap Test = \emptyset$, $Val \cap Test = \emptyset$).
2. **`PERSISTENT_SOURCE_HOLDOUT`**:
   - Partitions data at the `source_id` level.
   - Ensures that longitudinal observations of a recurring physical facility (e.g. Jamnagar refinery complex) never appear in both train and test partitions.
3. **`TEMPORAL_HOLDOUT`**:
   - Enforces strict chronological splitting: $T_{train} < T_{val} < T_{test}$.
   - Audits against temporal inversion.
4. **Showcase Isolation (`DATASET-003`)**:
   - Demonstration assets (e.g. Jamnagar showcase complex) are permanently isolated in `SHOWCASE_ISOLATION` (`DatasetRowStatus.SHOWCASE_ISOLATED`).
   - Showcase records are excluded from benchmark train/val/test evaluation scores.

---

## 5. Dataset Provenance & Reproducibility

- **Content Addressability**: Deterministic canonical SHA-256 content hashing across sorted records.
- **Deduplication Audit**: Pre-split auditing for duplicate entity IDs and space-time collision duplicates.
- **Dataset Manifest**: Versioned `DatasetManifest` with `split_strategy`, `feature_set_version`, `label_set_version`, bounding box scope, and git commit provenance.

---

## 6. Real Observational Dataset Specification (ML-010)

In addition to the controlled benchmark fixture (`ds_supervised_v1.0.0`), the system provides the real observational data activation layer:

| Dataset Identifier | Nature of Dataset | Originating Sources | Status & Scope |
| :--- | :--- | :--- | :--- |
| **`ds_supervised_v1.0.0`** | Controlled / Programmatic Benchmark Fixture | Programmatically synthesized multi-region event corpus ($N=100$) | Frozen baseline benchmark for ML-004 through ML-009 |
| **`ds_real_firms_v1.0.0`** | Real Observational Satellite Dataset | NASA FIRMS (VIIRS 375m / MODIS 1km active fire detections) | Activated in ML-010; input for ML-011 event construction |
| **`ds_real_events_v1.0.0`** | Real Thermal Event & Source Dataset | Spatiotemporally clustered events and persistent sources derived from `ds_real_firms_v1.0.0` | Activated in ML-011; input for ML-012 contextual enrichment |

### Invariant:
> `ds_real_firms_v1.0.0` and `ds_real_events_v1.0.0` represent observational remote-sensing entities and spatiotemporal clusters. They do **NOT** constitute ground-truth fire classifications or facility labels. Reference label adjudication (ML-012) must be performed before training supervised models on real-world observations.


