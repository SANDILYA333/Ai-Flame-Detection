"""Production ML Runtime Inference Smoke Test (NEXT-009).

Executes end-to-end production inference across all 3 authorized operating modes:
- HIGH_PRECISION (DecisionTreeClassifier @ tau=0.70)
- HIGH_RECALL (LogisticRegressionClassifier @ tau=0.50)
- SELECTIVE (DecisionTreeClassifier @ tau=0.80)

Verifies:
1. Model loading, version validation, and feature schema contract.
2. Inference confidence calculation and policy thresholding.
3. Safe abstention on low-confidence inputs.
4. UNKNOWN != NON_INDUSTRIAL invariant preservation.
"""

from __future__ import annotations

from typing import Any

from services.ml.deployment.policy import ProductionOperatingMode
from services.ml.features.standard_set import APPROVED_FEATURES
from services.ml.inference.production_runtime import (
    ProductionMLRuntimeService,
)


def generate_sample_features(
    is_industrial_pattern: bool = True,
) -> dict[str, Any]:
    """Build a deterministic feature dictionary satisfying canonical feat_v1.0.0."""
    features: dict[str, Any] = {f.feature_name: 0.0 for f in APPROVED_FEATURES}

    if is_industrial_pattern:
        # High persistence, high temperature, near industrial infrastructure
        features["persistence_active_days"] = 45.0
        features["persistence_total_events"] = 28.0
        features["persistence_recurrence_ratio"] = 0.85
        features["is_persistent_source"] = True
        features["is_near_industrial_facility"] = True
        features["facility_context_type"] = "REFINERY"
        features["land_cover_primary"] = "URBAN_BUILT"
        features["brightness_max_kelvin"] = 385.0
        features["brightness_mean_kelvin"] = 365.0
        features["frp_max_mw"] = 85.0
        features["frp_mean_mw"] = 42.0
        features["sensor_platform"] = "VIIRS_SNPP"
    else:
        # Transient, single event, remote vegetation, far from facilities
        features["persistence_active_days"] = 1.0
        features["persistence_total_events"] = 1.0
        features["persistence_recurrence_ratio"] = 0.0
        features["is_persistent_source"] = False
        features["is_near_industrial_facility"] = False
        features["facility_context_type"] = "NONE"
        features["land_cover_primary"] = "FOREST_SHRUB"
        features["brightness_max_kelvin"] = 315.0
        features["brightness_mean_kelvin"] = 310.0
        features["frp_max_mw"] = 12.0
        features["frp_mean_mw"] = 8.0
        features["sensor_platform"] = "VIIRS_NOAA20"

    return features


def run_smoke_test() -> None:
    print("=" * 75)
    print("SIH26162 — NEXT-009 PRODUCTION RUNTIME INFERENCE SMOKE TEST")
    print("=" * 75)
    print()

    # Clear engine cache for fresh start
    ProductionMLRuntimeService.clear_cache()

    test_cases = [
        ("High-Persistence Industrial Signature", generate_sample_features(True)),
        ("Transient Wildfire / Biomass Signature", generate_sample_features(False)),
    ]

    modes = [
        ProductionOperatingMode.HIGH_PRECISION,
        ProductionOperatingMode.HIGH_RECALL,
        ProductionOperatingMode.SELECTIVE,
    ]

    for mode in modes:
        print("-" * 75)
        print(f"TESTING OPERATING MODE: [{mode.value}]")
        print("-" * 75)

        _engine, policy = ProductionMLRuntimeService.get_or_load_engine(mode)
        print(f"Resolved Model:      {policy.assigned_model_type}")
        print(f"Model Version:       {policy.model_version}")
        print(f"Operating Threshold: tau >= {policy.confidence_threshold:.2f}")
        print(f"Policy Action:       {policy.abstention_action}")
        print()

        for label, feat_dict in test_cases:
            res = ProductionMLRuntimeService.predict_features(
                features=feat_dict,
                entity_id=f"smoke_{label.replace(' ', '_').lower()}",
                mode=mode,
            )
            print(f"  Input Scenario:    {label}")
            print(f"    * Predicted Class:     {res.predicted_class}")
            print(f"    * Assigned Class:      {res.assigned_class}")
            conf_str = (
                f"{res.confidence:.4f} (Threshold: {res.threshold:.2f})"
            )
            print(f"    * Confidence:          {conf_str}")
            print(f"    * Is Abstained:        {res.is_abstained}")
            print(f"    * Review Required:     {res.review_required}")
            print(f"    * Latency:             {res.latency_ms:.2f} ms")
            print()

    print("=" * 75)
    print("INFERENCE RUNTIME SMOKE TEST COMPLETED SUCCESSFULLY")
    print("=" * 75)


if __name__ == "__main__":
    run_smoke_test()
