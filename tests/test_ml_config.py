"""Unit tests for Phase 4 ML configuration contract."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.config.ml import ML_PARAMETER_FIELDS, MLConfig
from packages.errors import MissingConfigurationError
from packages.schemas.ml import (
    CalibrationMethod,
    SplitPartition,
    SplitStrategy,
    TargetType,
    TargetUnit,
)


class TestMLConfiguration:
    """Test suite validating typed, versioned ML configuration contracts."""

    def test_default_config_is_explicitly_incomplete(self) -> None:
        """Default MLConfig has all core parameters unset (None)."""
        config = MLConfig(version="v0.1.0-draft")
        assert config.version == "v0.1.0-draft"
        assert config.is_complete is False
        assert len(config.missing_parameters) == len(ML_PARAMETER_FIELDS)

        for param in ML_PARAMETER_FIELDS:
            assert getattr(config, param) is None

    def test_validate_completeness_raises_when_incomplete(self) -> None:
        """validate_completeness raises MissingConfigurationError on unset fields."""
        config = MLConfig(version="v0.1.0-draft")
        with pytest.raises(MissingConfigurationError) as exc_info:
            config.validate_completeness()

        assert "incomplete" in str(exc_info.value)
        assert exc_info.value.code == "MISSING_CONFIGURATION"
        assert "missing_parameters" in exc_info.value.details

    def test_fully_populated_valid_config_succeeds(self) -> None:
        """Fully populated MLConfig passes completeness validation."""
        config = MLConfig(
            version="v1.0.0",
            name="jamnagar_baseline_profile",
            target_name="thermal_phenomenon",
            target_type=TargetType.MULTICLASS_CLASSIFICATION,
            target_unit=TargetUnit.EVENT,
            class_vocabulary=(
                "flare",
                "fire",
                "industrial_thermal_source",
                "unknown",
            ),
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
            calibration_method=CalibrationMethod.ISOTONIC_REGRESSION,
            calibration_split_partition=SplitPartition.VALIDATION,
            abstention_enabled=True,
            confidence_cutoff=0.65,
        )
        assert config.is_complete is True
        assert config.missing_parameters == []
        config.validate_completeness()

    def test_split_ratios_must_sum_to_one(self) -> None:
        """Ratios must sum to 1.0 within tolerance."""
        with pytest.raises(ValidationError):
            MLConfig(
                version="v1.0.0",
                train_ratio=0.50,
                validation_ratio=0.20,
                test_ratio=0.20,  # Sum = 0.90 != 1.0
            )

    def test_deterministic_fingerprint_reproducibility(self) -> None:
        """Fingerprint produces identical SHA-256 for identical configs."""
        c1 = MLConfig(
            version="v1.0.0",
            target_name="thermal_phenomenon",
            target_type=TargetType.MULTICLASS_CLASSIFICATION,
            target_unit=TargetUnit.EVENT,
            created_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
        )
        c2 = MLConfig(
            version="v1.0.0",
            target_name="thermal_phenomenon",
            target_type=TargetType.MULTICLASS_CLASSIFICATION,
            target_unit=TargetUnit.EVENT,
            created_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
        )
        assert c1.compute_fingerprint() == c2.compute_fingerprint()
        assert len(c1.compute_fingerprint()) == 64
