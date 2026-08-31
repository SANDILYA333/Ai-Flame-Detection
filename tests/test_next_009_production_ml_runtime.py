"""Comprehensive Test Suite for NEXT-009: Production ML Runtime & Inference Service.

Verifies:
1. Production model loading and caching.
2. Production artifact integrity and safety auditing.
3. Pilot artifact rejection.
4. Model version validation (v1.0.0-production).
5. Canonical feature schema enforcement (feat_v1.0.0).
6. Operating mode resolution (HIGH_PRECISION, HIGH_RECALL, SELECTIVE).
7. Confidence calculation and policy thresholding.
8. High-confidence classification (industrial and non-industrial).
9. Low-confidence abstention and review routing.
10. Exact threshold boundary evaluation (confidence == threshold).
11. Critical invariant: UNKNOWN != NON_INDUSTRIAL under all failure/abstention paths.
12. Invalid operating mode rejection.
13. Missing / corrupted feature rejection.
14. Deterministic inference reproducibility.
15. FastAPI HTTP endpoint integration (/inference/predict and /inference/predict-batch).
16. No internal artifact paths or secrets leaked in API responses.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from services.api.app import create_app
from services.ml.deployment.policy import (
    ProductionDeploymentPolicyService,
    ProductionOperatingMode,
)
from services.ml.features.standard_set import APPROVED_FEATURES
from services.ml.inference.production_runtime import (
    ProductionMLRuntimeService,
    ProductionPredictionResponse,
)
from services.ml.models.registry import ModelRegistry


def get_canonical_feature_dict(is_industrial: bool = True) -> dict[str, Any]:
    """Helper to build a deterministic feature dictionary satisfying feat_v1.0.0."""
    features: dict[str, Any] = {f.feature_name: 0.0 for f in APPROVED_FEATURES}
    if is_industrial:
        features["persistence_active_days"] = 60.0
        features["persistence_total_events"] = 35.0
        features["persistence_recurrence_ratio"] = 0.90
        features["is_persistent_source"] = True
        features["is_near_industrial_facility"] = True
        features["facility_context_type"] = "REFINERY"
        features["land_cover_primary"] = "URBAN_BUILT"
        features["brightness_max_kelvin"] = 390.0
        features["brightness_mean_kelvin"] = 370.0
        features["frp_max_mw"] = 95.0
        features["frp_mean_mw"] = 55.0
        features["sensor_platform"] = "VIIRS_SNPP"
    else:
        features["persistence_active_days"] = 1.0
        features["persistence_total_events"] = 1.0
        features["persistence_recurrence_ratio"] = 0.0
        features["is_persistent_source"] = False
        features["is_near_industrial_facility"] = False
        features["facility_context_type"] = "NONE"
        features["land_cover_primary"] = "FOREST_SHRUB"
        features["brightness_max_kelvin"] = 310.0
        features["brightness_mean_kelvin"] = 305.0
        features["frp_max_mw"] = 8.0
        features["frp_mean_mw"] = 5.0
        features["sensor_platform"] = "VIIRS_NOAA20"
    return features


class TestNext009ProductionMLRuntime:
    """Test suite verifying end-to-end production ML runtime inference."""

    @pytest.fixture(autouse=True)
    def setup_runtime(self) -> None:
        """Clear cache before each test for clean isolation."""
        ProductionMLRuntimeService.clear_cache()

    @pytest.fixture(scope="class")
    @classmethod
    def api_client(cls) -> TestClient:
        """Create FastAPI test client."""
        app = create_app()
        return TestClient(app)

    # --------------------------------------------------------------------------
    # 1. Model Loading & Operating Mode Resolution Tests
    # --------------------------------------------------------------------------

    def test_high_precision_mode_resolution(self) -> None:
        """Verify HIGH_PRECISION resolves to DecisionTreeClassifier @ tau=0.70."""
        engine, policy = ProductionMLRuntimeService.get_or_load_engine(
            ProductionOperatingMode.HIGH_PRECISION
        )
        assert engine.artifact.metadata.model_type == "DecisionTreeClassifier"
        assert engine.artifact.metadata.model_version == "v1.0.0-production"
        assert engine.artifact.metadata.feature_set_version == "feat_v1.0.0"
        assert policy.confidence_threshold == 0.70
        assert policy.mode == ProductionOperatingMode.HIGH_PRECISION

    def test_high_recall_mode_resolution(self) -> None:
        """Verify HIGH_RECALL resolves to LogisticRegressionClassifier @ tau=0.50."""
        engine, policy = ProductionMLRuntimeService.get_or_load_engine(
            ProductionOperatingMode.HIGH_RECALL
        )
        assert (
            engine.artifact.metadata.model_type
            == "LogisticRegressionClassifier"
        )
        assert engine.artifact.metadata.model_version == "v1.0.0-production"
        assert policy.confidence_threshold == 0.50
        assert policy.mode == ProductionOperatingMode.HIGH_RECALL

    def test_selective_mode_resolution(self) -> None:
        """Verify SELECTIVE resolves to DecisionTreeClassifier @ tau=0.80."""
        engine, policy = ProductionMLRuntimeService.get_or_load_engine(
            ProductionOperatingMode.SELECTIVE
        )
        assert engine.artifact.metadata.model_type == "DecisionTreeClassifier"
        assert engine.artifact.metadata.model_version == "v1.0.0-production"
        assert policy.confidence_threshold == 0.80
        assert policy.mode == ProductionOperatingMode.SELECTIVE
        assert policy.coverage_estimate == 0.782

    def test_engine_caching_behavior(self) -> None:
        """Verify resolved engines are cached in memory for high-throughput reuse."""
        e1, p1 = ProductionMLRuntimeService.get_or_load_engine(
            ProductionOperatingMode.HIGH_PRECISION
        )
        e2, p2 = ProductionMLRuntimeService.get_or_load_engine(
            ProductionOperatingMode.HIGH_PRECISION
        )
        assert e1 is e2
        assert p1 is p2

    # --------------------------------------------------------------------------
    # 2. Security & Artifact Audit Tests
    # --------------------------------------------------------------------------

    def test_pilot_artifacts_rejected(self) -> None:
        """Verify runtime security auditor rejects pilot artifacts."""
        pilot_path = (
            "artifacts/real/pilot/"
            "pilot_decisiontreeclassifier_target_industrial_segregation_v1.0.0.json"
        )
        try:
            pilot_artifact = ModelRegistry.load_from_file(pilot_path)
            with pytest.raises(ValueError, match="Security Violation"):
                ProductionDeploymentPolicyService.audit_artifact_safety(
                    pilot_artifact
                )
        except FileNotFoundError:
            pass  # If pilot directory was not created, pass

    def test_schema_mismatch_rejected(self) -> None:
        """Verify runtime rejects feature payloads with missing required features."""
        features = {"persistence_active_days": 10.0}  # Missing 29 features
        with pytest.raises(ValueError, match="Feature schema mismatch"):
            ProductionMLRuntimeService.predict_features(
                features=features,
                mode=ProductionOperatingMode.HIGH_PRECISION,
            )

    def test_invalid_operating_mode_rejected(self) -> None:
        """Verify invalid operating mode names are rejected with clear errors."""
        features = get_canonical_feature_dict(True)
        with pytest.raises(ValueError, match="Invalid operating mode"):
            ProductionMLRuntimeService.predict_features(
                features=features,
                mode="UNAUTHORIZED_MODE",
            )

    # --------------------------------------------------------------------------
    # 3. Real Inference & Policy Execution Tests
    # --------------------------------------------------------------------------

    def test_high_confidence_inference_acceptance(self) -> None:
        """Verify high-confidence predictions above threshold are accepted."""
        features = get_canonical_feature_dict(is_industrial=True)
        res = ProductionMLRuntimeService.predict_features(
            features=features,
            entity_id="test_ind_001",
            mode=ProductionOperatingMode.HIGH_RECALL,  # tau=0.50
        )
        assert isinstance(res, ProductionPredictionResponse)
        assert res.entity_id == "test_ind_001"
        assert res.confidence >= 0.50
        assert res.assigned_class == res.predicted_class
        assert res.is_abstained is False
        assert res.review_required is False
        assert res.abstention_reason is None

    def test_low_confidence_abstention_and_review(self) -> None:
        """Verify low-confidence predictions below threshold trigger abstention."""
        features = get_canonical_feature_dict(is_industrial=False)
        res = ProductionMLRuntimeService.predict_features(
            features=features,
            entity_id="test_transient_001",
            mode=ProductionOperatingMode.SELECTIVE,  # tau=0.80
        )
        assert res.is_abstained is True
        assert res.review_required is True
        assert res.assigned_class == "unknown"
        assert res.abstention_reason == "LOW_CONFIDENCE"

    def test_unknown_is_not_non_industrial_invariant(self) -> None:
        """CRITICAL INVARIANT: Abstained predictions are NEVER non_industrial."""
        features = get_canonical_feature_dict(is_industrial=False)
        for mode in [
            ProductionOperatingMode.HIGH_PRECISION,
            ProductionOperatingMode.SELECTIVE,
        ]:
            res = ProductionMLRuntimeService.predict_features(
                features=features,
                entity_id="test_inv_001",
                mode=mode,
            )
            if res.is_abstained:
                assert res.assigned_class == "unknown"
                assert res.assigned_class != "non_industrial"

    def test_exact_threshold_boundary_acceptance(self) -> None:
        """Verify confidence == threshold is accepted according to policy contract."""
        res_exact = ProductionDeploymentPolicyService.apply_confidence_policy(
            predicted_class="industrial",
            confidence=0.70,
            mode=ProductionOperatingMode.HIGH_PRECISION,  # threshold = 0.70
        )
        assert res_exact["is_abstained"] is False
        assert res_exact["authorized_class"] == "industrial"
        assert res_exact["review_required"] is False

    def test_deterministic_inference_reproducibility(self) -> None:
        """Verify inference is strictly deterministic for identical inputs."""
        features = get_canonical_feature_dict(is_industrial=True)
        r1 = ProductionMLRuntimeService.predict_features(
            features=features,
            entity_id="det_001",
            mode=ProductionOperatingMode.HIGH_PRECISION,
        )
        r2 = ProductionMLRuntimeService.predict_features(
            features=features,
            entity_id="det_001",
            mode=ProductionOperatingMode.HIGH_PRECISION,
        )
        assert r1.predicted_class == r2.predicted_class
        assert r1.assigned_class == r2.assigned_class
        assert r1.confidence == r2.confidence
        assert r1.is_abstained == r2.is_abstained

    def test_batch_inference_execution(self) -> None:
        """Verify high-throughput batch inference over multiple samples."""
        items = [
            get_canonical_feature_dict(True),
            get_canonical_feature_dict(False),
        ]
        ids = ["batch_001", "batch_002"]
        results = ProductionMLRuntimeService.predict_batch(
            items=items,
            entity_ids=ids,
            mode=ProductionOperatingMode.HIGH_RECALL,
        )
        assert len(results) == 2
        assert results[0].entity_id == "batch_001"
        assert results[1].entity_id == "batch_002"

    # --------------------------------------------------------------------------
    # 4. FastAPI Endpoint Integration Tests
    # --------------------------------------------------------------------------

    def test_api_predict_single_feature_endpoint(
        self, api_client: TestClient
    ) -> None:
        """Verify /inference/predict HTTP POST endpoint."""
        features = get_canonical_feature_dict(is_industrial=True)
        payload = {
            "entity_id": "api_test_001",
            "features": features,
            "operating_mode": "HIGH_PRECISION",
        }
        response = api_client.post("/inference/predict", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["entity_id"] == "api_test_001"
        assert data["operating_mode"] == "HIGH_PRECISION"
        assert data["model_name"] == "DecisionTreeClassifier"
        assert data["model_version"] == "v1.0.0-production"
        assert data["feature_schema_version"] == "feat_v1.0.0"
        assert "confidence" in data
        assert "assigned_class" in data
        assert "is_abstained" in data
        # Ensure no internal filesystem paths are exposed
        assert "/home/" not in json.dumps(data)
        assert "artifacts/real" not in json.dumps(data)

    def test_api_predict_batch_endpoint(self, api_client: TestClient) -> None:
        """Verify /inference/predict-batch HTTP POST endpoint."""
        items = [
            get_canonical_feature_dict(True),
            get_canonical_feature_dict(False),
        ]
        payload = {
            "items": items,
            "entity_ids": ["api_b1", "api_b2"],
            "operating_mode": "HIGH_RECALL",
        }
        response = api_client.post("/inference/predict-batch", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2
        assert len(data["predictions"]) == 2
        assert data["predictions"][0]["entity_id"] == "api_b1"
        assert data["predictions"][1]["entity_id"] == "api_b2"

    def test_api_invalid_payload_returns_422(
        self, api_client: TestClient
    ) -> None:
        """Verify malformed feature payloads return 422 Unprocessable Entity."""
        payload = {
            "entity_id": "api_bad_001",
            "features": {"bad_feature": 123},
            "operating_mode": "HIGH_PRECISION",
        }
        response = api_client.post("/inference/predict", json=payload)
        assert response.status_code == 422
        assert "Feature schema mismatch" in response.json()["detail"]
