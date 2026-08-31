"""Unit tests for ML feature registry and leakage audit framework."""

from datetime import UTC, datetime, timedelta

import pytest

from packages.errors import ConflictError, NotFoundError
from packages.schemas.ml import (
    FeatureDefinition,
    FeatureMissingnessHandling,
    FeatureType,
    InferenceMode,
    LeakageRisk,
    TargetDefinition,
    TargetType,
    TargetUnit,
)
from services.ml.features.leakage import LeakageAuditor
from services.ml.features.registry import FeatureRegistry


class TestMLFeaturesAndLeakage:
    """Test suite validating feature registration, availability, and leakage."""

    def test_feature_registry_register_and_get(self) -> None:
        """Register and retrieve feature definition."""
        registry = FeatureRegistry()
        feat = FeatureDefinition(
            feature_name="frp_max_mw",
            feature_type=FeatureType.NUMERIC,
            source_entity="Event",
            derivation_description=(
                "Maximum FRP observed across all detections in event."
            ),
            physical_unit="MW",
            availability_lag_seconds=120.0,
            missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
            allowed_for_training=True,
            leakage_risk=LeakageRisk.SAFE,
            version="v1.0",
        )
        registry.register(feat)
        retrieved = registry.get("frp_max_mw")
        assert retrieved.feature_name == "frp_max_mw"
        assert retrieved.availability_lag_seconds == 120.0

        # Duplicate identical registration is idempotent
        registry.register(feat)

        # Different definition with same name raises ConflictError
        feat_conflict = FeatureDefinition(
            feature_name="frp_max_mw",
            feature_type=FeatureType.NUMERIC,
            source_entity="Event",
            derivation_description="Different derivation description.",
            physical_unit="MW",
            availability_lag_seconds=500.0,
            missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
            allowed_for_training=True,
            leakage_risk=LeakageRisk.SAFE,
            version="v2.0",
        )
        with pytest.raises(ConflictError):
            registry.register(feat_conflict)

    def test_feature_registry_not_found(self) -> None:
        """Unregistered feature name raises NotFoundError."""
        registry = FeatureRegistry()
        with pytest.raises(NotFoundError):
            registry.get("non_existent_feature")

    def test_feature_availability_future_observation_rejected(self) -> None:
        """Observation time after prediction time is rejected as future leakage."""
        registry = FeatureRegistry()
        feat = FeatureDefinition(
            feature_name="temp_k",
            feature_type=FeatureType.NUMERIC,
            source_entity="Detection",
            derivation_description="Brightness temperature.",
            availability_lag_seconds=0.0,
            missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
            allowed_for_training=True,
            leakage_risk=LeakageRisk.SAFE,
            version="v1.0",
        )
        registry.register(feat)

        t_pred = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        t_obs_future = datetime(2026, 1, 1, 12, 10, 0, tzinfo=UTC)

        is_valid, reason = registry.validate_availability(
            feature_name="temp_k",
            observation_time=t_obs_future,
            prediction_time=t_pred,
            inference_mode=InferenceMode.REAL_TIME_NRT,
        )
        assert is_valid is False
        assert reason is not None
        assert "in the future" in reason

    def test_feature_availability_lag_constraint(self) -> None:
        """Feature with 600s lag requires at least 600s elapsed before prediction."""
        registry = FeatureRegistry()
        feat = FeatureDefinition(
            feature_name="processed_satellite_index",
            feature_type=FeatureType.NUMERIC,
            source_entity="Satellite",
            derivation_description="L2 processed surface reflectance.",
            availability_lag_seconds=600.0,  # 10 minutes
            missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
            allowed_for_training=True,
            leakage_risk=LeakageRisk.SAFE,
            version="v1.0",
        )
        registry.register(feat)

        t_obs = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        t_pred_too_early = t_obs + timedelta(seconds=300)  # 5 minutes elapsed
        t_pred_ready = t_obs + timedelta(seconds=605)  # 10m 5s elapsed

        is_valid_early, reason_early = registry.validate_availability(
            feature_name="processed_satellite_index",
            observation_time=t_obs,
            prediction_time=t_pred_too_early,
            inference_mode=InferenceMode.HOURLY_BATCH,
        )
        assert is_valid_early is False
        assert "requires 600.0s lag" in str(reason_early)

        is_valid_ready, reason_ready = registry.validate_availability(
            feature_name="processed_satellite_index",
            observation_time=t_obs,
            prediction_time=t_pred_ready,
            inference_mode=InferenceMode.HOURLY_BATCH,
        )
        assert is_valid_ready is True
        assert reason_ready is None

    def test_leakage_auditor_flags_violations(self) -> None:
        """Auditor detects direct reference source, future temporal logic, and risks."""
        auditor = LeakageAuditor()
        target = TargetDefinition(
            target_id="target_phenomenon_v1",
            name="Phenomenon",
            target_type=TargetType.MULTICLASS_CLASSIFICATION,
            unit_of_prediction=TargetUnit.EVENT,
            class_vocabulary=["flare", "fire"],
        )

        clean_feature = FeatureDefinition(
            feature_name="duration_minutes",
            feature_type=FeatureType.NUMERIC,
            source_entity="Event",
            derivation_description="Duration in minutes from first to last detection.",
            availability_lag_seconds=0.0,
            missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
            allowed_for_training=True,
            leakage_risk=LeakageRisk.SAFE,
            version="v1.0",
        )

        direct_leak_feature = FeatureDefinition(
            feature_name="reference_label_flag",
            feature_type=FeatureType.BOOLEAN,
            source_entity="ReferenceLabel",  # Disallowed
            derivation_description="Annotator assigned label.",
            availability_lag_seconds=0.0,
            missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
            allowed_for_training=False,
            leakage_risk=LeakageRisk.DIRECT_LEAKAGE,
            version="v1.0",
        )

        future_leak_feature = FeatureDefinition(
            feature_name="subsequent_flare_confirmation",
            feature_type=FeatureType.NUMERIC,
            source_entity="Event",
            derivation_description="Subsequent observations 3 days after prediction.",
            availability_lag_seconds=0.0,
            missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
            allowed_for_training=True,
            leakage_risk=LeakageRisk.UNKNOWN,
            version="v1.0",
        )

        report = auditor.audit_feature_set(
            [clean_feature, direct_leak_feature, future_leak_feature],
            target_definition=target,
        )

        assert report.is_safe is False
        assert report.total_audited == 3
        assert report.safe_count == 1
        assert "duration_minutes" in report.safe_features
        assert report.violation_count >= 2
