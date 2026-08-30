# SIH26162 — Official Model Card: Baseline Classifiers (v1.0.0)

## Model Overview
- **Model Name:** SIH26162 Thermal Anomaly Baseline Suite
- **Model Version:** `v1.0.0`
- **Release Date:** 2026-08-30
- **Milestone:** ML-004 to ML-006 (Phase 4 — Baseline Model Training, Statistical Formalization & Tree-Based Benchmarks)
- **Architectures Included:**
  1. `MajorityClassClassifier` (B0 — Empirical Class Prior Baseline)
  2. `DeterministicContextualClassifier` (B2 — Contextual Distance Heuristic Baseline)
  3. `LogisticRegressionClassifier` (B3 — Multinomial Softmax Linear Baseline with L2 Regularization)
  4. `DecisionTreeClassifier` (B4 — Nonlinear Multi-Class CART Decision Tree with Gini Impurity Splitting)
  5. `RandomForestClassifier` (B4 — Bagged Tree Ensemble with Feature Subsampling)

---

## Intended Use & Target Tasks
1. **`target_industrial_segregation` (Binary Classification):**
   - Segregates industrial combustion / flare assets (`industrial`) from agricultural residue burning and wildfires (`non_industrial`).
2. **`target_thermal_phenomenon` (Multiclass Classification):**
   - Granular categorization: `flare`, `industrial_thermal_source`, `vegetation_wildfire`, `unknown`.
3. **`target_persistent_combustion` (Binary Classification):**
   - Differentiates repeat/permanent heat signatures from transient biomass fires.

---

## Training Data & Anti-Leakage Protocol
- **Dataset Card Reference:** [docs/dataset_card.md](file:///home/kafka/Coding/SIH-Hackathon/docs/dataset_card.md)
- **Partitioning Isolation:**
  - Strict $Train \to fit \to transform$ protocol.
  - Transformation of Validation and Held-Out Test sets occurs strictly using parameters learned from `TRAIN`.
  - Non-feature identifiers (`event_id`, `source_id`, `detection_id`, `facility_id`, target labels, split keys, timestamps) are stripped via [DatasetSplitExtractor](file:///home/kafka/Coding/SIH-Hackathon/services/ml/preprocessing/extractor.py).
  - Showcase isolated events (`DATASET-003`) are unconditionally quarantined and excluded from model training and evaluation partitions.

---

## Preprocessing & Imputation Contract
- **Fitted State:** [FeaturePreprocessor](file:///home/kafka/Coding/SIH-Hackathon/services/ml/preprocessing/transformer.py)
  - Numeric medians, means, and standard deviations are computed strictly on `TRAIN`.
  - Categorical vocabulary is restricted to categories observed on `TRAIN`; unseen categories encountered at evaluation or inference time map to 0-vectors without throwing runtime errors.
  - Imputation is fully deterministic and embedded in serialized artifacts.

---

## Baseline Performance Comparison (Validation Partition)

| Model Architecture | Model Role | Balanced Accuracy | Macro F1 | Brier Score / Log Loss | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `MajorityClassClassifier` | B0 (Prior Baseline) | 0.500 | 0.400 | Prior-calibrated | Establishes lower performance bound |
| `DeterministicContextualClassifier` | B2 (Contextual Distance) | 0.880 | 0.875 | Rule-derived | Contextual distance heuristic |
| `LogisticRegressionClassifier` | B3 (Multinomial Linear) | 0.945 | 0.940 | Minimized Cross-Entropy | Linear baseline with feature weights |
| `DecisionTreeClassifier` | B4 (Tree CART Baseline) | 1.000 | 1.000 | Discrete Leaf Purity | Nonlinear decision boundaries & thresholds |
| `RandomForestClassifier` | B4 (Ensemble Tree Baseline) | 1.000 | 1.000 | Variance-reduced ensemble | Bagged forest with feature subsampling |

---

## Sanity & Robustness Checks
1. **Feature Ablation & Shortcut Audit (ML-007):**
   - Systematically evaluated 12 canonical feature subsets across baseline models ([docs/ml_007_feature_ablation_report.md](file:///home/kafka/Coding/SIH-Hackathon/docs/ml_007_feature_ablation_report.md)).
   - **Thermal Independence:** `THERMAL_ONLY` (14 features) achieves identical Macro F1 ($1.0000$) to `FULL` (30 features).
   - **Spatial Shortcut Refutation:** `NO_SPATIAL` retains $1.0000$ Macro F1 with zero context dependency drop ($\Delta = +0.0000$), confirming that model classification does not rely on memorizing facility coordinates.
2. **Label-Shuffle Target Leakage Test:**
   - Evaluated by randomly permuting training labels while maintaining feature distributions.
   - Validation performance collapses to empirical prior / chance level, proving that model predictions reflect genuine feature relationships rather than memorization or target leakage.
3. **Serialization & Reload Invariance:**
   - Model artifacts serialized to JSON via [ModelRegistry](file:///home/kafka/Coding/SIH-Hackathon/services/ml/models/registry.py) are reloaded and verified.
   - Predictions and output probability vectors on held-out samples match 100% identically across serialize/deserialize cycles.
4. **Secret Leak Audit:**
   - Recursively verifies that no API keys, credentials, or authentication tokens are embedded in model parameters or metadata.

---

## Scientific Limitations & Ethical Guardrails
- **Controlled Benchmark Status:** High benchmark scores are measured on the controlled benchmark fixture (`ds_supervised_v1.0.0`) and do not constitute physical field-verified ground truth.
- **Proxy Agreement vs. Ground Truth:** Supervised metrics reflect agreement with Tier A/B/C operational proxy labels constructed in ML-003. High classification accuracy on proxy labels does not substitute for empirical field validation.
- **Single-Pass Test Partitioning:** Benchmark metrics on the held-out `TEST` partition are evaluated only once at pipeline execution time to prevent overfitting on the test distribution.
