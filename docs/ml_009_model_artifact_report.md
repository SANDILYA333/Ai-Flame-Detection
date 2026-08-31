# ML-009 — Final Model Artifacts, Reproducibility, Inference Contract & Phase-4 Freeze

**Milestone:** `ML-009`  
**Status:** `COMPLETE & SCIENTIFICALLY FROZEN`  
**Verification Date:** `2026-08-30`  
**Test Suite Coverage:** `399 passed, 39 subtests passed (100% pass rate)`  
**Source Type Safety & Lint:** `0 errors across 176 source files`  

---

## 1. Objective

The objective of **ML-009** is to harden, formalize, and freeze the end-to-end Machine Learning artifact lifecycle for the SIH26162 Phase-4 Machine Learning foundation:
```
Dataset (ds_supervised_v1.0.0)
   ↓
Feature Contract (feat_v1.0.0, 30 point-in-time features)
   ↓
Label Contract (label_v1.0.0, Tier A authoritative seeds)
   ↓
Split Contract (GROUPED_EVENT_HOLDOUT & Holdouts)
   ↓
Leakage-Safe Preprocessor (Fitted strictly on TRAIN)
   ↓
Trained Model (B0, B2, B3, B4-DT, B4-RF)
   ↓
Model Artifact Container (ModelArtifact with SHA-256 content hashing)
   ↓
Artifact Integrity & Secret Audit
   ↓
Filesystem Persistence & Reload
   ↓
Inference Runtime Engine (MLInferenceEngine)
   ↓
Deterministic & Invariant Prediction
```

---

## 2. Existing Artifact Architecture Audit

Prior to ML-009, the repository contained foundational serialization logic in `services/ml/models/registry.py` and model evaluation reporting in `services/ml/evaluation/`. However:
- `services/ml/inference/` was an empty stub lacking a structured inference runtime.
- Model artifacts lacked deterministic content-addressable SHA-256 hashes to detect parameter corruption and tampering.
- Training provenance lacked an immutable `TrainingRunManifest` schema tying hyperparameter configurations, dataset versions, and evaluation metrics into a single auditable record.
- Secret scanning did not explicitly reject bearer tokens and private keys within serialized JSON string values.

---

## 3. Changes Made in ML-009

1. **Pydantic Schemas (`packages/schemas/ml.py` & `packages/schemas/__init__.py`):**
   - Enhanced `ModelMetadata` with `model_family`, `dataset_id`, `dataset_hash`, `target_version`, `feature_dimensionality`, and `artifact_hash`.
   - Enhanced `ModelArtifact` with `compute_content_hash()` computing deterministic SHA-256 digests over model parameters and preprocessor state.
   - Introduced `TrainingRunManifest` capturing immutable training run execution provenance.
   - Introduced `InferencePredictionResult` formalizing point-in-time prediction outputs with probability distributions, highest confidence, and abstention auditing.
2. **Model Registry Hardening (`services/ml/models/registry.py`):**
   - Added content-addressable SHA-256 integrity verification (`verify_artifact_integrity`).
   - Hardened recursive secret scanning (`_audit_no_secrets`) rejecting keys (`map_key`, `token`, `secret`, `password`, `api_key`, `credential`, `private_key`, `authorization`) and bearer/map-key string patterns.
   - Added structural validation rejecting empty vocabularies, unsupported architectures, and corrupt JSON.
3. **Inference Runtime Engine (`services/ml/inference/engine.py`):**
   - Implemented `MLInferenceEngine` supporting single-sample, batch, and event-level inference (`predict_features`, `predict_record`, `predict_event`, `predict_batch`).
   - Implemented strict feature schema validation rejecting missing features and empty payloads.
   - Wired in `AbstentionDecisionEngine` to evaluate confidence cutoffs and evidence thresholds.
4. **End-to-End Demonstration Script (`scripts/run_ml_009_artifact_demo.py`):**
   - Programmatically trains a Random Forest model on the benchmark dataset, saves the artifact to disk, reloads the artifact, validates the SHA-256 hash, and verifies numerical prediction invariance.
5. **Comprehensive Test Suite (`tests/test_ml_009_model_artifacts.py`):**
   - 10 rigorous tests validating schema integrity, preprocessor state invariance, reload invariance across all 5 baseline models, missing feature rejection, tamper detection, secret scanning, and full inference execution.

---

## 4. Model Artifact Schema

The canonical `ModelArtifact` container encapsulates:
```python
class ModelArtifact(BaseDomainModel):
    metadata: ModelMetadata
    preprocessor_state: dict[str, Any]
    model_parameters: dict[str, Any]
    class_vocabulary: list[str]
    sha256_hash: str | None = None
```

---

## 5. Dataset Provenance

- **Dataset ID:** `ds_supervised_v1.0.0`
- **Dataset Semantic Version:** `v1.0.0`
- **Dataset SHA-256 Hash:** Embedded in dataset manifest
- **Sample Population:** $N = 100$ events (Train = 53, Validation = 26, Test = 21)
- **Geographic Scope:** `IND_MULTI_REGION`
- **Temporal Window:** Multi-day baseline interval ($t_0 \to t_0 + 10\text{d}$)

---

## 6. Feature Provenance

- **Feature Set ID:** `standard_30_features`
- **Feature Set Version:** `feat_v1.0.0`
- **Input Dimension:** 30 point-in-time geospatial features across 6 groups:
  - Thermal Core ($N=8$): `frp_mean`, `frp_max`, `frp_std`, `frp_snr`, `ti4_mean`, `ti4_max`, `ti5_mean`, `ti4_ti5_diff`
  - Spatial Clustering ($N=5$): `detection_count`, `spatial_span_m`, `spatial_dispersion_m`, `aspect_ratio`, `cluster_density`
  - Temporal Trajectory ($N=5$): `duration_hours`, `detection_rate_per_hour`, `frp_rate_of_change`, `observation_count`, `day_night_ratio`
  - Contextual Proximity ($N=4$): `facility_distance_m`, `facility_bearing_deg`, `source_distance_m`, `infrastructure_proximity_score`
  - Environmental Baseline ($N=4$): `land_cover_code`, `ambient_temperature_k`, `wind_speed_ms`, `relative_humidity_pct`
  - Multi-Sensor Consistency ($N=4$): `sensor_count`, `viirs_detection_count`, `modis_detection_count`, `cross_sensor_frp_ratio`
- **Transformed Feature Dimension:** 31 numeric inputs (one-hot encoded categorical features).

---

## 7. Label Provenance

- **Target ID:** `target_industrial_segregation`
- **Target Semantic Version:** `target_v1.0.0`
- **Label Set Version:** `label_v1.0.0`
- **Class Vocabulary:** `["industrial", "non_industrial"]`
- **Quality Tiers:** Tier A Authoritative Reference Seeds (Gas flaring surveys, heavy industrial facility registries) and Tier B Secondary Proxies.

---

## 8. Preprocessing Provenance

- **Preprocessor Architecture:** `FeaturePreprocessor`
- **Anti-Leakage Rule:** Fitted **strictly on TRAIN partition only**.
- **Imputation Statistics:** Median imputation parameters computed strictly from training partition.
- **Normalization Statistics:** Mean and standard deviation computed strictly from training partition.
- **Categorical Encodings:** Discrete categories mapped strictly from training partition.

---

## 9. Split Provenance

- **Split Strategy:** `GROUPED_EVENT_HOLDOUT` (and audited under `PERSISTENT_SOURCE_HOLDOUT`, `FACILITY_HOLDOUT`, `SPATIAL_GEOGRAPHIC_HOLDOUT`, `TEMPORAL_HOLDOUT`, `SOURCE_SENSOR_HOLDOUT`).
- **Split Ratios:** Train = 60%, Validation = 20%, Test = 20%.
- **Showcase Isolation (`DATASET-003`):** Showcase entities permanently quarantined in `SplitPartition.SHOWCASE_ISOLATION`.

---

## 10. Model Provenance & Parameter Specifications

| Architecture | Model Family | Hyperparameters Frozen | State Parameter Representation |
| :--- | :--- | :--- | :--- |
| **`MajorityClassClassifier` (B0)** | `HeuristicBaseline` | `random_seed=42` | `{"majority_class": "industrial", "prior_prob": 0.5094}` |
| **`DeterministicContextualClassifier` (B2)** | `HeuristicBaseline` | `proximity_threshold_m=1000.0` | `{"proximity_threshold_m": 1000.0}` |
| **`LogisticRegressionClassifier` (B3)** | `StatisticalLinear` | `lr=0.05, max_epochs=150, l2_lambda=0.01` | `{"weights": [...], "bias": [...]}` |
| **`DecisionTreeClassifier` (B4-DT)** | `TreeEnsemble` | `max_depth=5, min_samples_split=2` | `{"tree_structure": {...}}` |
| **`RandomForestClassifier` (B4-RF)** | `TreeEnsemble` | `n_estimators=10, max_depth=5` | `{"trees": [{...}], "n_estimators": 10}` |

---

## 11. Inference Contract

The canonical inference flow is executed via `MLInferenceEngine`:
```
Input: Event + Member Detections (or FeatureRecord, or Feature Dict)
  ↓
Feature Schema Contract Validation (checks 30 required keys)
  ↓
Vector Transformation via Reconstructed Preprocessor
  ↓
Frozen Model Prediction & Class Probability Generation
  ↓
Confidence Calculation & Abstention Evaluation
  ↓
Output: InferencePredictionResult
```

### Structured Output Schema:
```json
{
  "entity_id": "demo_evt_jamnagar",
  "target_id": "target_industrial_segregation",
  "target_version": "target_v1.0.0",
  "model_id": "model_randomforestclassifier_target_industrial_segregation_v1.0.0",
  "model_version": "v1.0.0",
  "model_type": "RandomForestClassifier",
  "feature_set_version": "feat_v1.0.0",
  "predicted_class": "industrial",
  "class_probabilities": {
    "industrial": 0.8028,
    "non_industrial": 0.1972
  },
  "confidence": 0.8028,
  "is_abstained": false,
  "abstention_reason": null,
  "feature_count": 30,
  "inference_timestamp": "2026-01-20T14:45:00Z",
  "latency_ms": 0.031
}
```

---

## 12. Artifact Hashing & Content Integrity

Every serialized model artifact embeds a deterministic content hash computed over model parameters and preprocessor state:
```python
def compute_content_hash(self) -> str:
    state = {
        "model_type": self.metadata.model_type,
        "target_id": self.metadata.target_id,
        "feature_set_version": self.metadata.feature_set_version,
        "preprocessor_state": self.preprocessor_state,
        "model_parameters": self.model_parameters,
        "class_vocabulary": self.class_vocabulary,
    }
    json_bytes = json.dumps(state, sort_keys=True, ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(json_bytes).hexdigest()
```
If an artifact is tampered with or corrupted on disk, `ModelRegistry.load_from_file()` detects the hash mismatch and immediately raises `ValueError`.

---

## 13. Serialization Specifications

- **Format:** Canonical JSON (`ensure_ascii=True`, `sort_keys=True`, `indent=2`).
- **Encoding:** `UTF-8`.
- **Determinism:** Independent of platform endianness, dictionary ordering, or Python runtime hash randomization.

---

## 14. Reload Invariance Verification

Tested across 100% of supported model architectures:
$$\text{Prediction}_{\text{before\_save}}(\mathbf{x}) \equiv \text{Prediction}_{\text{after\_reload}}(\mathbf{x})$$
$$\text{Probabilities}_{\text{before\_save}}(\mathbf{x}) \equiv \text{Probabilities}_{\text{after\_reload}}(\mathbf{x})$$
All 5 model classes passed reload invariance tests with zero numerical drift ($\Delta p = 0.0000$).

---

## 15. Secret Audit & Security Posture

`ModelRegistry._audit_no_secrets()` recursively scans all metadata fields, dictionary keys, and string values for sensitive tokens:
- **Prohibited Key Patterns:** `map_key`, `token`, `secret`, `password`, `api_key`, `credential`, `private_key`, `authorization`.
- **Prohibited Value Patterns:** `bearer `, `firms_map_key`.
- **Audit Result:** `PASSED`. No API keys, credentials, or secrets exist within any model artifact.

---

## 16. Independent Reproducibility Procedure

To reproduce any model artifact from source:
```bash
# 1. Run the deterministic artifact demonstration script
uv run python scripts/run_ml_009_artifact_demo.py

# 2. Run the complete ML-009 test suite
uv run pytest tests/test_ml_009_model_artifacts.py -v

# 3. Run full verification across the repository
uv run ruff format --check . && uv run ruff check . && uv run mypy . && uv run pytest
```

---

## 17. Failure Modes & Defensive Handling

| Failure Mode | Detection Mechanism | System Behavior |
| :--- | :--- | :--- |
| **Missing Feature in Inference Input** | `validate_feature_schema()` | Raises `ValueError` with exact missing feature list |
| **Tampered Artifact Weights** | SHA-256 Content Hash Verification | Raises `ValueError: Artifact content hash mismatch` |
| **Secret in Metadata** | `_audit_no_secrets()` | Raises `ValueError: Prohibited sensitive key` |
| **Incompatible Model Type** | `SUPPORTED_MODEL_TYPES` check | Raises `ValueError: Unsupported model type` |
| **High Uncertainty Prediction** | `AbstentionDecisionEngine` | Sets `is_abstained=True`, `abstention_reason="LOW_CONFIDENCE"` |

---

## 18. Scientific Limitations

1. **Operational Proxy Labels $\neq$ Field Ground Truth:** Training labels are derived from operational proxy heuristics and authoritative industrial seeds. They do not constitute exhaustive ground-truth physical annotations.
2. **Controlled Benchmark Fixture $\neq$ Live NASA FIRMS Archive:** The benchmark dataset consists of $N=100$ programmatic/controlled events.
3. **Sensor Generalization Infeasible:** As audited in ML-008, single-sensor (`VIIRS`) data cannot validate cross-sensor transferability (`SOURCE_SENSOR_HOLDOUT`).

---

## 19. Controlled Benchmark Status

The models (**B0**, **B2**, **B3**, **B4-DT**, **B4-RF**) are fully trained and benchmarked on the controlled fixture (`ds_supervised_v1.0.0`). The high benchmark scores reflect the strong radiative signal separation in the controlled dataset and must not be misinterpreted as real-world operational accuracy.

---

## 20. Production-Readiness Limitations

```
Engineering Artifact Readiness ≠ Scientific Validation ≠ Production Deployment Readiness
```
While the code artifacts, serialization pipeline, and inference runtime are hardened and verified to production engineering standards, **the model cannot be deployed for unrestricted operational use without extensive field-validation against real-world satellite observations and multi-sensor ground truth.**

---

## 21. Complete Verification Results

- **`ruff format --check .`**: 198 files formatted cleanly.
- **`ruff check .`**: All checks passed (0 lint errors).
- **`mypy .`**: Success: no issues found in 176 source files.
- **`pytest`**: 399 passed, 39 subtests passed in 16.79s (100% pass rate).
- **`scripts/run_ml_009_artifact_demo.py`**: Successfully executed end-to-end inference and reload invariance demonstration.

---

## 22. Final Verdict & Phase-4 Freeze

**ML-009 is COMPLETE and Phase 4 is officially FROZEN.**

### Phase-4 Baseline Freeze Manifest:
- **Target Specification:** `target_industrial_segregation` (`target_v1.0.0`)
- **Feature Set:** `standard_30_features` (`feat_v1.0.0`, 30 point-in-time features)
- **Label Set:** `label_v1.0.0` (Tier A / Tier B operational proxy labels)
- **Dataset Contract:** `ds_supervised_v1.0.0`
- **Supported Baseline Ladder:**
  - `B0`: `MajorityClassClassifier`
  - `B2`: `DeterministicContextualClassifier`
  - `B3`: `LogisticRegressionClassifier`
  - `B4-DT`: `DecisionTreeClassifier`
  - `B4-RF`: `RandomForestClassifier`
- **Inference Runtime:** `MLInferenceEngine` (`services/ml/inference/engine.py`)
- **Model Registry & Persistence:** `ModelRegistry` (`services/ml/models/registry.py`)
