# ML-004 Baseline Model Training & Reproducible ML Pipeline Report

## Executive Summary
Milestone **ML-004** delivers the complete baseline machine learning training, evaluation, and serialization pipeline for Phase 4 of the SIH26162 Thermal Anomaly Intelligence System.

Building upon the dataset foundation established in ML-001 through ML-003, ML-004 implements:
1. **Leakage-Free Preprocessing Isolation:** Strict $Train \to fit \to transform$ enforcement via [FeaturePreprocessor](file:///home/kafka/Coding/SIH-Hackathon/services/ml/preprocessing/transformer.py) and [DatasetSplitExtractor](file:///home/kafka/Coding/SIH-Hackathon/services/ml/preprocessing/extractor.py).
2. **Defensible Baseline Model Suite:**
   - Baseline 0 (B0): [MajorityClassClassifier](file:///home/kafka/Coding/SIH-Hackathon/services/ml/models/trivial.py) (empirical prior lower bound).
   - Baseline 2 (B2): [DeterministicContextualClassifier](file:///home/kafka/Coding/SIH-Hackathon/services/ml/models/contextual.py) (heuristic proximity classifier).
   - Baseline 3 (B3): [LogisticRegressionClassifier](file:///home/kafka/Coding/SIH-Hackathon/services/ml/models/linear.py) (multinomial softmax linear classifier with L2 regularization and feature interpretability).
3. **Reproducible End-to-End Orchestrator:** [MLTrainingPipeline](file:///home/kafka/Coding/SIH-Hackathon/services/ml/training/pipeline.py) orchestrating dataset extraction, training, validation, single-pass test evaluation, label-shuffle sanity checks, and artifact verification.
4. **Secure Model Registry & Serialization:** [ModelRegistry](file:///home/kafka/Coding/SIH-Hackathon/services/ml/models/registry.py) with secret-leak auditing and exact reload invariance.

---

## Technical Implementations

### 1. Preprocessing & Extraction Architecture
- **Non-Feature Column Filtering:** Strips `event_id`, `source_id`, `detection_id`, `facility_id`, labels, tiers, timestamps, and split keys before vectorization.
- **Showcase Isolation Enforcement:** Quarantines showcase events (`DATASET-003`) from both training and benchmark evaluation splits.
- **Zero-Lookahead Feature Imputation:** Learns numeric means, medians, standard deviations, and categorical vocabularies exclusively from the `TRAIN` partition. Imputes missing values on validation/test sets without leaking test distribution statistics.

### 2. Model Implementations & Hierarchy
```text
Baseline 0 (B0: Majority Class)
      ↓ (Establishes prior chance baseline)
Baseline 2 (B2: Contextual Heuristics)
      ↓ (Establishes deterministic spatial rules baseline)
Baseline 3 (B3: Multinomial Logistic Regression)
      ↓ (Establishes interpretable statistical linear baseline)
Phase 4 Advanced Models (Future: Non-linear / tree baselines)
```

### 3. Sanity Checks & Scientific Controls
- **Label-Shuffle Sanity Test:** Randomly shuffles training labels only, fits a fresh classifier, and verifies that validation accuracy collapses to empirical prior level.
- **Single-Pass Held-Out Test Evaluation:** Test partition is evaluated exactly once at the conclusion of training without iterative tuning or hyperparameter selection on test data.
- **Reload Invariance:** Proves identical prediction and calibrated probability vectors when saving to JSON and reloading via `ModelRegistry`.

---

## Verification & Test Results
- **Full Test Suite:** 360 unit/integration tests passing (`pytest`).
- **Code Quality:** 0 Ruff linting errors, 0 Ruff formatting issues.
- **Type Safety:** 0 MyPy type errors across 166 source files.
