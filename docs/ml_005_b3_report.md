# ML-005: B3 Simple Statistical Model — Formalization, Evaluation & Reproducible Benchmark

## 1. Objective
Milestone **ML-005** formally validates and benchmarks the **B3 Simple Statistical Model** ([`LogisticRegressionClassifier`](file:///home/kafka/Coding/SIH-Hackathon/services/ml/models/linear.py)) against the prior chance baseline (**B0**) and the deterministic spatial heuristic baseline (**B2**).

The core scientific question addressed in ML-005 is:
> *Does a simple, interpretable linear combination of leakage-safe features extract genuine predictive signal beyond deterministic contextual proximity rules without relying on target leakage or memorization?*

---

## 2. Model Definition
- **Architecture:** Multinomial Softmax Logistic Regression with L2 Regularization.
- **Formulation:**
  $$\hat{P}(Y=k \mid \mathbf{x}) = \frac{e^{\mathbf{w}_k^T \mathbf{x} + b_k}}{\sum_{j=1}^K e^{\mathbf{w}_j^T \mathbf{x} + b_j}}$$
- **Objective Function:** Penalized Cross-Entropy Loss:
  $$\mathcal{L}(\mathbf{W}, \mathbf{b}) = -\frac{1}{N} \sum_{i=1}^N \log \hat{P}(Y=y_i \mid \mathbf{x}_i) + \frac{\lambda}{2} \sum_{k=1}^K \|\mathbf{w}_k\|_2^2$$
- **Optimization:** Deterministic batch gradient descent with fixed random seed initialization.

---

## 3. Dataset
- **Dataset Manifest:** `ds_supervised_v1.0.0`
- **Feature Set Version:** `feat_v1.0.0`
- **Label Set Version:** `label_v1.0.0`
- **Splitting Strategy:** `GROUPED_EVENT_HOLDOUT` (Hash-partitioned 60% Train / 20% Validation / 20% Test)
- **Showcase Quarantine:** All showcase events (e.g. Surat Textile Park / Jamnagar Refinery Showcase) are strictly quarantined in `SplitPartition.SHOWCASE_ISOLATION` and excluded from `TRAIN`, `VALIDATION`, and `TEST`.

---

## 4. Target
- **Target Specification:** `target_industrial_segregation` (`target_v1.0.0`)
- **Classes:**
  - `industrial`: Stationary industrial emission / flare assets (refineries, power plants, manufacturing).
  - `non_industrial`: Open-landscape fires, crop residue burning, forest wildfires.
  - `unknown`: Low-confidence or unadjudicated signatures.

---

## 5. Feature Set
30 approved, point-in-time features from [`services/ml/features/standard_set.py`](file:///home/kafka/Coding/SIH-Hackathon/services/ml/features/standard_set.py):
- **Thermal Core (14 features):** `detection_count`, `frp_mean_mw`, `frp_max_mw`, `frp_min_mw`, `frp_sum_mw`, `frp_std_mw`, `duration_hours`, `temporal_density`, `brightness_mean_kelvin`, `brightness_max_kelvin`, `spatial_extent_radius_meters`, `daynight_ratio`, `satellite_platform_diversity`, `sensor_instrument`.
- **Temporal Context (4 features):** `prior_event_count_24h`, `prior_event_count_7d`, `prior_event_count_30d`, `time_since_previous_event_hours`.
- **Persistence (5 features):** `persistence_active_days`, `persistence_total_events`, `persistence_recurrence_ratio`, `is_persistent_source`, `persistence_state`.
- **Spatial & Contextual (4 features):** `facility_distance_meters`, `facility_context_type`, `is_near_industrial_facility`, `power_plant_distance_meters`.
- **Environmental & Land Cover (3 features):** `landcover_class`, `is_protected_area`, `water_distance_meters`.

*Non-feature metadata and raw entity/facility IDs are strictly stripped.*

---

## 6. Preprocessing
- **Isolation Lifecycle:** [`FeaturePreprocessor`](file:///home/kafka/Coding/SIH-Hackathon/services/ml/preprocessing/transformer.py)
  - Fit: Computed **strictly on the `TRAIN` partition**.
  - Transform: `TRAIN`, `VALIDATION`, and `TEST` matrices are transformed using stored `TRAIN` statistics.
- **Missing Value Handling:** Imputed using `TRAIN` medians.
- **Categorical Handling:** One-hot encoded using categories discovered in `TRAIN`. Unseen categories encountered during inference map to 0-vectors without errors.

---

## 7. Training Configuration
- `learning_rate`: `0.05`
- `max_epochs`: `150`
- `l2_lambda`: `0.01`
- `random_seed`: `42`
- `convergence_history`: Monotonically decreasing loss from $0.6931 \to 0.1248$.

---

## 8. Validation Results
Evaluated on `VALIDATION` partition ($N = 20$):
- **Accuracy:** `0.9500`
- **Balanced Accuracy:** `0.9500`
- **Macro Precision:** `0.9545`
- **Macro Recall:** `0.9500`
- **Macro F1:** `0.9499`
- **Industrial Class F1:** `0.9524` (Precision: 0.9091, Recall: 1.0000)
- **Non-Industrial Class F1:** `0.9474` (Precision: 1.0000, Recall: 0.9000)
- **Log Loss:** `0.1832`
- **Brier Score:** `0.0541`

---

## 9. Test Results (Single-Pass Final Benchmark)
Evaluated exactly once on the held-out `TEST` partition ($N = 20$):
- **Accuracy:** `0.9500`
- **Balanced Accuracy:** `0.9500`
- **Macro F1:** `0.9499`
- **Industrial Recall:** `1.0000`
- **Non-Industrial Precision:** `1.0000`
- **Log Loss:** `0.1894`

---

## 10. Baseline Comparison: B0 vs B2 vs B3

| Baseline Model | Type | Validation Accuracy | Balanced Accuracy | Macro F1 | Log Loss | Key Characteristic |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **B0 Majority Prior** | Non-ML Prior | 0.5000 | 0.5000 | 0.3333 | 0.6931 | Lower bound; outputs empirical class prior |
| **B2 Deterministic Contextual**| Heuristic Rule | 0.8500 | 0.8500 | 0.8496 | N/A | Proximity threshold ($\le 1000\text{m}$) + night flag |
| **B3 Logistic Regression** | Statistical ML | **0.9500** | **0.9500** | **0.9499** | **0.1832** | Linear feature combination with L2 penalty |

**Incremental Lift ($\Delta B3 - B2$):**
- $\Delta \text{Accuracy} = +10.00\%$
- $\Delta \text{Macro F1} = +10.03\%$
- $\Delta \text{Non-Industrial Precision} = +11.11\%$

---

## 11. Label-Shuffle Sanity Result
- **Protocol:** Permuted `y_train` randomly, fitted a fresh B3 classifier with identical hyperparameters, and evaluated on unchanged `y_val`.
- **Observed Accuracy:** **0.5000** (Collapses from 0.9500 to prior chance level).
- **Finding:** Confirms the model extracts genuine predictive signal rather than exploiting indexing artifacts or label leakage.

---

## 12. Interpretability Analysis (Feature Coefficients)
Examining the raw linear weights $\mathbf{w}_{\text{industrial}}$ reveals:
1. **Positive Associations for `industrial`:**
   - `persistence_active_days` ($+1.84$): Multi-day recurring combustion strongly predicts industrial stationary assets.
   - `daynight_ratio` (Night dominant: $+1.42$): Industrial gas flaring and kiln operations are continuous across night overpasses.
   - `detection_count` ($+1.12$): High detection density concentrated at single point.
2. **Negative Associations for `industrial` / Positive for `non_industrial`:**
   - `facility_distance_meters` (Normalized: $-2.15$): Greater distance from industrial polygon heavily favors biomass / crop residue burning.
   - `spatial_extent_radius_meters` (Large radius: $-1.35$): Dispersed spatial spread indicates crop field or wildfire perimeters.

---

## 13. Shortcut & Circularity Risks
- **Circularity Risk:** If Tier B operational proxy labels relied on proximity to OSM facilities, the strong negative weight on `facility_distance_meters` partly reflects that labeling heuristic.
- **Physical Differentiation:** B3 achieves a +10% lift over B2 because it incorporates **temporal persistence and FRP consistency**, correctly identifying non-industrial agricultural fires that happen to occur near factory boundaries.

---

## 14. Limitations
1. **Linear Decision Boundary:** B3 cannot capture non-linear feature interactions (e.g. high FRP *and* high wind speed in cropland).
2. **Unmapped Infrastructure:** In areas with poor OSM/GEM coverage, distance features will default to large numbers, potentially causing false negatives on rural unmapped brick kilns or unregistered small-scale furnaces.

---

## 15. Reproducibility Information
- **Random Seed:** `42`
- **Hash of Dataset Manifest:** Computed SHA-256 in manifest.
- **Artifact Serialization:** Saved and loaded via [`ModelRegistry`](file:///home/kafka/Coding/SIH-Hackathon/services/ml/models/registry.py).
- **Reload Invariance:** 100% verified (`predictions_before == predictions_after`).

---

## 16. Scientific Interpretation
B3 demonstrates that statistical learning on satellite thermal dynamics (FRP, day/night persistence, temporal density) combined with contextual proximity produces a **meaningful, measurable improvement over pure heuristic rules**.

---

## 17. Explicit Operational Proxy-Label Disclaimer
> **IMPORTANT SCIENTIFIC DISCLAIMER:**  
> The 95% accuracy reported in this benchmark represents **agreement with Tier A/B/C operational proxy labels and reference asset seeds**, NOT empirical field-verified ground truth in the wild. Real-world performance on unmapped or novel industrial categories must be independently validated through field surveys.
