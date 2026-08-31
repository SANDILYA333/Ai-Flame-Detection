# Machine Learning Readiness & Evaluation Foundation (ML-001)

This document establishes the scientific machine-learning infrastructure, domain schemas, validation contracts, leakage auditing, dataset splitting protocols, and evaluation harnesses for Phase 4 of the SIH26162 platform.

---

## 1. Architectural Scope & Core Principles

ML-001 provides a strictly validated foundation for Phase 4 machine learning without prematurely training models, fabricating synthetic labels, or resolving uncalibrated scientific parameters.

```text
External Raw Data / Catalogues
      ↓
Canonical Observations
      ↓
Scientific Derivation (Phase 3)
      ↓
Feature Registry & Leakage Audit (ML-001)
      ↓
Dataset Manifests & Group-Holdout Splits (ML-001)
      ↓
Model Baselines & Probabilistic Evaluation Harness (ML-001)
      ↓
Scientific ML Readiness Auditor (ML-001)
```

### Core Invariants
1. **No Model Training in ML-001**: Model training (Random Forests, XGBoost, Neural Nets) is strictly reserved for downstream milestones (ML-004+).
2. **No Fabricated Labels**: Machine learning labels must originate from documented, authoritative reference catalogues with provenance metadata.
3. **No Silent Resolution of Scientific Open Questions**: Open questions regarding taxonomy, benchmark boundaries, and study areas are surfaced as explicit blockers in `MLReadinessReport`.
4. **Missing $\neq$ Zero**: Missing feature values cannot be imputed as zeros or silent absences without an explicit domain contract (`FeatureMissingnessHandling`).

---

## 2. Typed ML Configuration (`packages/config/ml.py`)

`MLConfig` provides a frozen, immutable Pydantic configuration model with explicit incomplete state handling:

```python
from packages.config import MLConfig
from packages.schemas import SplitStrategy, TargetType, TargetUnit

config = MLConfig(
    version="v1.0.0",
    name="jamnagar_baseline_profile",
    target_name="thermal_phenomenon",
    target_type=TargetType.MULTICLASS_CLASSIFICATION,
    target_unit=TargetUnit.EVENT,
    class_vocabulary=("flare", "fire", "industrial_thermal_source", "unknown"),
    feature_set_version="feat_v1.0.0",
    allowed_feature_names=(
        "frp_mean_mw",
        "duration_hours",
        "facility_distance_m",
    ),
    split_strategy=SplitStrategy.GROUPED_EVENT_HOLDOUT,
    train_ratio=0.70,
    validation_ratio=0.15,
    test_ratio=0.15,
    random_seed=42,
    required_metrics=("macro_f1", "balanced_accuracy", "brier_score"),
    primary_metric="macro_f1",
)

# Validates completeness before any downstream execution
config.validate_completeness()

# Computes deterministic SHA-256 fingerprint
fingerprint = config.compute_fingerprint()
```

---

## 3. Reference Label Provenance & Tier Hierarchy

Reference annotations are classified into strict evidentiary tiers (`packages/schemas/ml.py`):

| Tier | Enum | Description | Ground-Truth Eligibility |
| :--- | :--- | :--- | :--- |
| **Tier A** | `TIER_A_AUTHORITATIVE` | High-resolution optical/SAR confirmation, validated operator reports, official registry | **Eligible** as authoritative ground truth |
| **Tier B** | `TIER_B_STRONG_EVIDENCE` | Multi-sensor agreement, persistent spatio-temporal cluster verification | **Eligible** with explicit documentation |
| **Tier C** | `TIER_C_PROXY_WEAK` | Rule-based heuristic tags, distance-to-landuse proxies, unverified detections | **PROHIBITED** as ground truth |

---

## 4. Feature Management & Leakage Audit

### 4.1 Feature Registry (`services/ml/features/registry.py`)
Features are explicitly registered with physical units, temporal availability lag, and missingness contracts:
- `validate_availability(feature_name, observation_time, prediction_time, inference_mode, max_allowed_nrt_latency_seconds)`
  - Enforces `observation_time <= prediction_time`
  - Enforces `observation_time + availability_lag <= prediction_time`
  - Enforces NRT latency thresholds for `REAL_TIME_NRT` mode.
  - Rejects features flagged with `DIRECT_LEAKAGE`, `TEMPORAL_LEAKAGE`, or `LABEL_CONTAMINATION`.

### 4.2 Leakage Auditor (`services/ml/features/leakage.py`)
Audits feature definitions and derivations against:
- Disallowed source entities (`ReferenceLabel`, `GroundTruth`, `TargetDefinition`).
- Forward-looking temporal phrases in derivation logic (`future`, `next_observation`, `subsequent`, `post_event`).
- Class vocabulary contamination in feature naming or unverified proxy derivations.

---

## 5. Dataset Manifests & Split Integrity Engine

### 5.1 Deterministic Dataset Manifests (`services/ml/training/dataset.py`)
- `DatasetBuilder.compute_records_hash()` sorts records deterministically by entity ID and canonical JSON before computing SHA-256 hashes.
- `DatasetBuilder.audit_duplicates()` detects duplicate entity IDs and exact space-time coordinate collisions.
- `SHOWCASE_ISOLATION`: Permanently isolates demonstration events (DATASET-003) from train/val/test partitions.

### 5.2 Split Assignment & Integrity (`services/ml/training/splits.py`)
Supported split strategies:
1. `GROUPED_EVENT_HOLDOUT`: All detections comprising a single thermal event are strictly assigned to the same partition.
2. `PERSISTENT_SOURCE_HOLDOUT`: Persistent industrial sources present in training never appear in test.
3. `SPATIO_TEMPORAL_SOURCE_GROUPED`: Combined spatial facility and temporal partition holdout.
4. `TEMPORAL_HOLDOUT`: Chronological cutoffs ($t_{train} < t_{val} < t_{test}$).

`SplitIntegrityValidator` audits partition assignments and emits violation reports for event leakage, source leakage, and temporal inversions.

---

## 6. Evaluation Harness, Calibration & Abstention

### 6.1 Evaluation Harness (`services/ml/evaluation/harness.py`)
Generates comprehensive `EvaluationReport` metrics:
- Per-class precision, recall, F1-score, and support.
- Multi-class confusion matrices.
- Macro-averaged precision, recall, F1, and balanced accuracy.
- Multi-class probabilistic metrics: Brier score and log loss.
- Selective classification / abstention metrics.

### 6.2 Calibration Contract (`services/ml/calibration/contract.py`)
- **Scientific Invariant**: Calibration must **never** fit on the `TEST` partition (`SplitPartition.TEST`).
- Computes Expected Calibration Error (ECE) and Maximum Calibration Error (MCE) across probability bins.

### 6.3 Abstention Decision Engine (`services/ml/calibration/abstention.py`)
Enforces model abstention under uncertainty:
- `confidence < confidence_threshold` $\rightarrow$ `AbstentionReason.LOW_CONFIDENCE`
- `uncertainty > uncertainty_threshold` $\rightarrow$ `AbstentionReason.HIGH_UNCERTAINTY`
- `evidence_completeness < min_completeness` $\rightarrow$ `AbstentionReason.INSUFFICIENT_EVIDENCE`
- Calculates operational coverage fraction and selective risk.

---

## 7. Scientific ML Readiness Auditor (`services/ml/readiness.py`)

Assesses whether all 8 scientific pillars are satisfied:
1. Target definition and class taxonomy approved/frozen.
2. Reference label quality and Tier A/B provenance verified.
3. Feature metadata definitions and latency compatibility checked.
4. Leakage audit clean (0 violations).
5. Split strategy defined and group independence verified.
6. Benchmark scope and evaluation metrics frozen.
7. Calibration and abstention contracts defined.
8. Deterministic dataset hash and configuration fingerprint available.

Outputs `MLReadinessReport` with overall status:
- `READY`: All 8 pillars satisfied; supervised training is scientifically permitted.
- `BLOCKED`: Fundamental blockers or unadjudicated weak labels exist.
- `NOT_READY`: Technical prerequisites incomplete.

---

## 8. Downstream Consumption (ML-002 through ML-009)

| Milestone | Task | Consumes from ML-001 |
| :--- | :--- | :--- |
| **ML-002** | Target & Taxonomy Definition | `TargetDefinition`, `TargetType`, `TargetUnit`, `MLConfig` |
| **ML-003** | Reference Data & Benchmark Splits | `LabelMetadata`, `DatasetBuilder`, `SplitAssignmentService`, `SplitIntegrityValidator` |
| **ML-004** | Baseline Models (B0/B1) | `FeatureRegistry`, `LeakageAuditor`, `EvaluationHarness`, `MLConfig` |
| **ML-005** | Advanced Modeling | `DatasetManifest`, `EvaluationReport`, `MLReadinessAuditor` |
| **ML-006** | Probability Calibration | `CalibrationContract`, `CalibrationManager`, `ECE/MCE` |
| **ML-007** | Abstention & Out-of-Distribution | `AbstentionContract`, `AbstentionDecisionEngine` |
| **ML-008** | End-to-End Evaluation Report | Full `EvaluationHarness`, `SplitIntegrityReport`, `MLReadinessReport` |
| **ML-009** | Real-Time Model Serving | `InferenceMode`, `validate_availability`, `FeatureMissingnessHandling` |
