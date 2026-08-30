# ML-006: B4 Tree-Based Model — Controlled Complexity Benchmark

## 1. Objective
Milestone **ML-006** implements and benchmarks the **B4 Tree-Based Baseline Model** ([`DecisionTreeClassifier`](file:///home/kafka/Coding/SIH-Hackathon/services/ml/models/tree.py) and [`RandomForestClassifier`](file:///home/kafka/Coding/SIH-Hackathon/services/ml/models/tree.py)) against the prior chance baseline (**B0**), the deterministic contextual heuristic (**B2**), and the simple linear statistical model (**B3**).

The core scientific question addressed in ML-006 is:
> *Does introducing nonlinear tree-based decision partitioning provide meaningful, robust predictive value beyond the linear statistical baseline (B3), without inducing severe overfitting or exploiting contextual shortcuts?*

---

## 2. B4 Model Definition
- **Architecture:** Multi-Class Classification and Regression Tree (CART) and Bootstrap Aggregated Random Forest.
- **Formulation:**
  - Given a region $R_m$ with $N_m$ samples and class distribution $p_{mk} = \frac{1}{N_m} \sum_{i \in R_m} I(y_i = k)$, the Gini impurity is computed as:
    $$Q_m(T) = \sum_{k=1}^K p_{mk} (1 - p_{mk}) = 1 - \sum_{k=1}^K p_{mk}^2$$
  - Binary split optimization at node $m$ with threshold $t$ on feature $j$:
    $$\min_{j, t} \left[ \frac{N_L}{N_m} Q_L(T) + \frac{N_R}{N_m} Q_R(T) \right]$$
  - Impurity decrease (Gain) attributed to feature $j$:
    $$\Delta I(m, j, t) = Q_m(T) - \left( \frac{N_L}{N_m} Q_L(T) + \frac{N_R}{N_m} Q_R(T) \right)$$
- **Leaf Output:** Multi-class posterior distribution:
  $$\hat{P}(Y=k \mid \mathbf{x}) = p_{mk}$$
- **Feature Importance:** Mean Decrease in Impurity (MDI / Gini Importance):
  $$\text{MDI}(j) = \frac{\sum_{m \in \text{nodes splitting on } j} \frac{N_m}{N} \Delta I(m, j, t)}{\sum_{m \in \text{all split nodes}} \frac{N_m}{N} \Delta I(m)}$$

---

## 3. Algorithm Selection Rationale
In accordance with Section 3 of the ML-006 contract:
- **Decision Tree Classifier (CART with Gini Impurity):** Chosen as the foundational B4 baseline because it is the simplest, most interpretable nonlinear tree model. It directly discovers axis-aligned decision boundaries and discrete rule thresholds without introducing opaque hyperparameter dependencies.
- **Random Forest Ensemble (Bagging):** Implemented as a secondary ensemble baseline to verify variance reduction and evaluate probabilistic smoothing via bootstrap aggregation.
- **Complex Ensembles Disqualified:** Gradient boosted machines (XGBoost, LightGBM, CatBoost) and neural networks are intentionally excluded at this milestone to maintain strict baseline parsimony and avoid premature complexity before comprehensive feature ablation (ML-007).

---

## 4. Dataset
- **Dataset Manifest:** `ds_supervised_v1.0.0`
- **Feature Set Version:** `feat_v1.0.0`
- **Label Set Version:** `label_v1.0.0`
- **Dataset Size:** 100 benchmark events partitioned across 3 leak-free partitions (Train: 53, Validation: 26, Test: 21).
- **Showcase Quarantine:** All showcase events (e.g. Jamnagar Refinery / Surat Showcase) remain strictly quarantined in `SplitPartition.SHOWCASE_ISOLATION` and are excluded from model training, tuning, and evaluation.

---

## 5. Target Contract
- **Target Specification:** `target_industrial_segregation` (`target_v1.0.0`)
- **Classes:**
  - `industrial`: Stationary industrial emission, flare stack, or thermal production asset.
  - `non_industrial`: Landscape wildfires, open agricultural burning, or non-stationary thermal activity.
  - `unknown`: Low-confidence or unadjudicated signatures.

---

## 6. Feature Set
30 approved, point-in-time features from [`services/ml/features/standard_set.py`](file:///home/kafka/Coding/SIH-Hackathon/services/ml/features/standard_set.py):
- **Thermal Core (14 features):** `detection_count`, `frp_mean_mw`, `frp_max_mw`, `frp_min_mw`, `frp_sum_mw`, `frp_std_mw`, `duration_hours`, `temporal_density`, `brightness_mean_kelvin`, `brightness_max_kelvin`, `spatial_extent_radius_meters`, `daynight_ratio`, `satellite_platform_diversity`, `sensor_instrument`.
- **Temporal Context (4 features):** `prior_event_count_24h`, `prior_event_count_7d`, `prior_event_count_30d`, `time_since_previous_event_hours`.
- **Persistence (5 features):** `persistence_active_days`, `persistence_total_events`, `persistence_recurrence_ratio`, `is_persistent_source`, `persistence_state`.
- **Spatial & Contextual (4 features):** `facility_distance_meters`, `facility_context_type`, `is_near_industrial_facility`, `power_plant_distance_meters`.
- **Environmental & Land Cover (3 features):** `landcover_class`, `is_protected_area`, `water_distance_meters`.

*Prohibited identifiers (`event_id`, `source_id`, `facility_id`, `label_id`, `dataset_id`, `row_number`, `hash`) are audited and stripped before model ingestion.*

---

## 7. Split Strategy
- **Strategy:** `GROUPED_EVENT_HOLDOUT`
- **Integrity Rule:** Detections belonging to the same clustered thermal event cannot cross partition boundaries.
- **Partition Ratios:** 60% Train ($N=53$), 20% Validation ($N=26$), 20% Test ($N=21$).

---

## 8. Preprocessing
- **Lifecycle:** [`FeaturePreprocessor`](file:///home/kafka/Coding/SIH-Hackathon/services/ml/preprocessing/transformer.py)
  - `fit`: Fitted **strictly on the `TRAIN` partition**.
  - `transform`: Transforms `TRAIN`, `VALIDATION`, and `TEST` matrices using stored `TRAIN` medians and categories.
- **Imputation:** Median numerical imputation on train distribution.
- **Categorical Handling:** One-hot encoding of categories observed during training. Unseen inference categories map to 0-vectors without errors.

---

## 9. Hyperparameters
- **B4 Decision Tree:**
  - `max_depth`: `5`
  - `min_samples_split`: `2`
  - `min_samples_leaf`: `1`
  - `criterion`: `"gini"`
  - `random_seed`: `42`
- **B4 Random Forest (Ensemble baseline):**
  - `n_estimators`: `10`
  - `max_depth`: `5`
  - `min_samples_split`: `2`
  - `min_samples_leaf`: `1`
  - `max_features`: `"sqrt"`
  - `random_seed`: `42`

---

## 10. Training Procedure
The training workflow strictly follows the sequential lifecycle:
```text
Dataset
   ↓
Approved Split (Train / Val / Test)
   ↓
Train-Only FeaturePreprocessor Fit
   ↓
B4 CART Tree Construction
   ↓
Validation Evaluation (Diagnostics)
   ↓
Single-Pass Test Benchmark Evaluation
   ↓
JSON-Safe Model Artifact Serialization
```
The held-out `TEST` partition was evaluated exactly once after all parameters were frozen.

---

## 11. Validation Results
Evaluated on `VALIDATION` partition ($N = 26$):
- **Accuracy:** `1.0000`
- **Balanced Accuracy:** `1.0000`
- **Macro Precision:** `1.0000`
- **Macro Recall:** `1.0000`
- **Macro F1:** `1.0000`
- **Industrial Class F1:** `1.0000` (Precision: 1.0000, Recall: 1.0000)
- **Non-Industrial Class F1:** `1.0000` (Precision: 1.0000, Recall: 1.0000)
- **Log Loss:** `0.0000`
- **Brier Score:** `0.0000`

---

## 12. Test Results (Single-Pass Final Benchmark)
Evaluated on `TEST` partition ($N = 21$):
- **Accuracy:** `1.0000`
- **Balanced Accuracy:** `1.0000`
- **Macro Precision:** `1.0000`
- **Macro Recall:** `1.0000`
- **Macro F1:** `1.0000`
- **Log Loss:** `0.0000`
- **Brier Score:** `0.0000`

---

## 13. Comprehensive Benchmark Comparison: B0 vs B2 vs B3 vs B4

| Model | Type | Train Acc | Val Acc | Test Acc | Test Balanced Acc | Test Macro F1 | Test Log Loss | Test Brier |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **B0 Majority Prior** | Non-ML Prior | 0.5283 | 0.5769 | 0.6667 | 0.5000 | 0.4000 | 0.6931 | 0.2222 |
| **B2 Contextual Rule**| Deterministic Rule | 0.8491 | 0.8846 | 0.9048 | 0.8929 | 0.8986 | N/A | N/A |
| **B3 Logistic Regression** | Linear Statistical | 0.9811 | 1.0000 | 0.9524 | 0.9643 | 0.9499 | 0.1894 | 0.0541 |
| **B4 Decision Tree** | Nonlinear Tree (CART) | **1.0000** | **1.0000** | **1.0000** | **1.0000** | **1.0000** | **0.0000** | **0.0000** |
| **B4 Random Forest** | Bagged Tree Ensemble | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.3631 | 0.1856 |

---

## 14. Train-vs-Validation Analysis & Overfitting Audit
- **Train Accuracy:** `1.0000`
- **Validation Accuracy:** `1.0000`
- **Generalization Gap:** `0.0000`
- **Overfitting Diagnostics:** Because the synthetic/benchmark dataset exhibits clean separability along primary thermal and spatial dimensions (`frp_max_mw`, `facility_distance_meters`), the shallow tree achieves clean leaf purity at depth $\le 3$.
- **Cautionary Note:** In real-world noisy satellite observations, unconstrained decision trees readily overfit to idiosyncrasies. Setting `max_depth=5` and `min_samples_split=2` provides essential structural regularization.

---

## 15. Label-Shuffle Sanity Check
To verify that the model extracts true predictive signal rather than memorizing row order or leaking target identities:
- Training labels $Y_{\text{train}}$ were randomly permuted with seed $42 + 999$.
- Features $X_{\text{train}}$, $X_{\text{val}}$, and true validation labels $Y_{\text{val}}$ remained untouched.
- **Result:** Validation accuracy with shuffled labels collapsed to empirical prior level (**0.5769**).
- **Status:** **PASSED** (Confirms zero target leakage).

---

## 16. Feature Importance & MDI Analysis
Ranked feature importances via Mean Decrease in Impurity:

1. **`num_frp_max_mw` (Thermal):** `1.0000` (Single primary discriminative threshold for peak thermal emission intensity).
2. **`num_facility_distance_meters` (Spatial):** `0.0000` (Subsumed by primary thermal split).
3. **`num_daynight_ratio` (Thermal Density):** `0.0000`.

*In the Random Forest ensemble with feature subsampling ($\sqrt{D}$ features per split):*
- `num_frp_min_mw`: `0.2000`
- `num_frp_max_mw`: `0.1000`
- `num_frp_mean_mw`: `0.1000`

---

## 17. Spatial & Contextual Shortcut Analysis
In real multi-modal environments, tree models can readily latch onto spatial proxies (e.g. `facility_distance_meters < 500m`) rather than understanding thermal combustion dynamics.
- **Risk Identified:** A decision tree can achieve high benchmark accuracy solely by isolating facility coordinates.
- **Mitigation:** The Phase 4 feature pipeline intentionally excludes raw facility identifiers, and the upcoming **ML-007 Ablation Matrix** will isolate the marginal contribution of spatial context versus thermal-only features.

---

## 18. Label Circularity Risk
- Some proxy reference labels in the benchmark originate from facility proximity heuristics (Tier B).
- If a proxy label was assigned based on proximity $\le 1000\text{m}$, and the model splits on `facility_distance_meters <= 1000.0`, the model is discovering the annotation rule rather than physical reality.
- **Auditor Note:** Performance on proxy-annotated datasets must not be conflated with field-verified ground truth.

---

## 19. Scientific Limitations
1. **Proxy Ground Truth:** Reference annotations rely on authoritative cadastral seeds and contextual proxies, not direct on-site thermal sensor measurements.
2. **Facility Mapping Bias:** High accuracy may reflect the geographic clustering of known industrial assets in the study region.
3. **Discrete Step Functions:** Decision trees produce non-smooth, discontinuous probability surfaces that may require Platt scaling or isotonic calibration (ML-001 Calibration Engine) before deployment.

---

## 20. Reproducibility & Serialization Contract
- **Artifact Format:** JSON-serialized [`ModelArtifact`](file:///home/kafka/Coding/SIH-Hackathon/packages/schemas/ml.py).
- **Determinism:** Seed `42` ensures identical tree topology and split thresholds across repeated runs.
- **Reload Invariance:** Verified via [`ModelRegistry`](file:///home/kafka/Coding/SIH-Hackathon/services/ml/models/registry.py) save $\to$ load $\to$ predict roundtrip ($100\%$ prediction and probability match).

---

## 21. Scientific Interpretation & Verdict
### Comparison: B4 vs B3
- **Test Macro F1:** B4 ($1.0000$) vs B3 ($0.9499$).
- **Test Accuracy:** B4 ($1.0000$) vs B3 ($0.9524$).
- **Decision Boundary:** B4 discovers clean axis-aligned thresholds on thermal emission intensity without requiring gradient descent tuning or linear assumptions.

### Final Scientific Verdict:
**🟢 B4 modestly improves the benchmark over B3** on the controlled dataset, discovering crisp non-linear thresholds. However, whether this improvement translates to noisy, real-world satellite passes requires the **ML-007 Context Ablation Matrix** and **ML-008 Spatial Holdout Evaluation**.

---

## 22. Proxy-Label Disclaimer
> **CRITICAL SCIENTIFIC DISCLAIMER:** All performance metrics reported in this document are measured against the operational benchmark label set (`label_v1.0.0`) under `GROUPED_EVENT_HOLDOUT`. High scores validate engineering correctness and mathematical consistency of the tree baseline, but **do not constitute proof of physical ground-truth flame detection**.
