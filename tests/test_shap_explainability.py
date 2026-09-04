"""Comprehensive unit tests for SHAP Feature Attribution & TreeSHAP Explainer."""

import pytest
from services.ml.explainability.shap_explainer import TreeSHAPExplainer
from services.ml.models.tree import DecisionTreeClassifier, RandomForestClassifier


def test_tree_shap_decision_tree():
    """Verify TreeSHAP on a fitted CART DecisionTreeClassifier."""
    # Synthetic 2-feature dataset
    # Feature 0: FRP (high -> INDUSTRIAL)
    # Feature 1: Distance (low -> INDUSTRIAL)
    x_train = [
        [100.0, 200.0],
        [80.0, 500.0],
        [90.0, 300.0],
        [10.0, 4000.0],
        [15.0, 5000.0],
        [8.0, 8000.0],
    ]
    y_train = [
        "INDUSTRIAL",
        "INDUSTRIAL",
        "INDUSTRIAL",
        "NON_INDUSTRIAL",
        "NON_INDUSTRIAL",
        "NON_INDUSTRIAL",
    ]

    dt = DecisionTreeClassifier(max_depth=3, random_seed=42)
    dt.fit(x_train, y_train)

    # Explain high FRP, low distance sample
    sample = [95.0, 250.0]
    names = ["frp_mean_mw", "facility_distance_meters"]
    res = TreeSHAPExplainer.explain_decision_tree(
        tree_model=dt,
        sample=sample,
        target_class="INDUSTRIAL",
        feature_names=names,
    )

    assert res.attribution_method == "TREE_SHAP"
    assert res.target_class == "INDUSTRIAL"
    assert len(res.attributions) == 2
    assert res.predicted_probability >= 0.9

    # Sum of base value + shap values equals predicted leaf probability
    total_attr = sum(a.shap_value for a in res.attributions)
    assert pytest.approx(res.base_value + total_attr, abs=1e-4) == res.predicted_probability


def test_tree_shap_random_forest():
    """Verify TreeSHAP averaging across ensemble on RandomForestClassifier."""
    x_train = [
        [100.0, 200.0],
        [80.0, 500.0],
        [90.0, 300.0],
        [10.0, 4000.0],
        [15.0, 5000.0],
        [8.0, 8000.0],
    ]
    y_train = [
        "INDUSTRIAL",
        "INDUSTRIAL",
        "INDUSTRIAL",
        "NON_INDUSTRIAL",
        "NON_INDUSTRIAL",
        "NON_INDUSTRIAL",
    ]

    rf = RandomForestClassifier(n_estimators=5, max_depth=3, random_seed=42)
    rf.fit(x_train, y_train)

    sample = [85.0, 400.0]
    names = ["frp_mean_mw", "facility_distance_meters"]
    res = TreeSHAPExplainer.explain_random_forest(
        rf_model=rf,
        sample=sample,
        target_class="INDUSTRIAL",
        feature_names=names,
    )

    assert res.attribution_method == "TREE_SHAP"
    assert len(res.attributions) == 2
    total_attr = sum(a.shap_value for a in res.attributions)
    assert pytest.approx(res.base_value + total_attr, abs=1e-4) == res.predicted_probability


def test_shap_domain_fallback():
    """Verify domain fallback explanation when model is heuristic/rule-based."""
    features = {
        "facility_distance_meters": 450.0,
        "frp_mean_mw": 85.0,
        "persistence_recurrence_ratio": 0.82,
        "detection_count": 4,
    }

    res = TreeSHAPExplainer.explain_domain_fallback(
        features=features,
        predicted_class="INDUSTRIAL",
        confidence=0.96,
    )

    assert res.attribution_method == "DOMAIN_FALLBACK"
    assert res.target_class == "INDUSTRIAL"
    assert len(res.attributions) >= 4
    # Positive weights for industrial features
    fac_attr = next(a for a in res.attributions if a.raw_feature_name == "facility_distance_meters")
    assert fac_attr.shap_value > 0
    assert fac_attr.impact == "supports_predicted"
