"""Unit tests for BE-004 canonical scientific configuration contract."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.config.scientific import (
    SCIENTIFIC_PARAMETER_FIELDS,
    ScientificConfig,
)
from packages.config.settings import Settings
from packages.errors import MissingConfigurationError


class TestScientificConfiguration:
    """Test suite validating the typed, versioned scientific configuration contract."""

    def test_default_config_is_explicitly_incomplete(self) -> None:
        """TEST 1: Default config has all thresholds as None and is_complete False."""
        config = ScientificConfig(version="v0.1.0-draft")
        assert config.version == "v0.1.0-draft"
        assert config.is_complete is False
        assert len(config.missing_parameters) == len(SCIENTIFIC_PARAMETER_FIELDS)

        for param in SCIENTIFIC_PARAMETER_FIELDS:
            assert getattr(config, param) is None

    def test_validate_completeness_raises_when_incomplete(self) -> None:
        """TEST 2: validate_completeness raises MissingConfigurationError if unset."""
        config = ScientificConfig(version="v0.1.0-draft")
        with pytest.raises(MissingConfigurationError) as exc_info:
            config.validate_completeness()

        assert "incomplete" in str(exc_info.value)
        assert exc_info.value.code == "MISSING_CONFIGURATION"
        assert "missing_parameters" in exc_info.value.details

    def test_fully_populated_valid_config_succeeds(self) -> None:
        """TEST 3: A fully populated config is marked complete and validates cleanly."""
        config = ScientificConfig(
            version="v1.0.0",
            name="test_profile",
            spatial_cluster_radius_meters=1000.0,
            temporal_window_hours=24.0,
            persistence_threshold_days=30.0,
            persistence_min_observations=5,
            attribution_radius_meters=2000.0,
            attribution_confidence_threshold=0.85,
            minimum_event_confidence=0.70,
            abstention_confidence_threshold=0.50,
        )

        assert config.is_complete is True
        assert config.missing_parameters == []
        # Should not raise
        config.validate_completeness()

    def test_validation_rejects_non_positive_spatial_temporal(self) -> None:
        """TEST 4: Non-positive radii or windows raise Pydantic ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ScientificConfig(
                version="v1.0.0",
                spatial_cluster_radius_meters=-500.0,
            )
        assert "spatial_cluster_radius_meters" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            ScientificConfig(
                version="v1.0.0",
                temporal_window_hours=0.0,
            )
        assert "temporal_window_hours" in str(exc_info.value)

    def test_validation_rejects_invalid_confidence_probabilities(self) -> None:
        """TEST 5: Probabilities outside [0.0, 1.0] raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ScientificConfig(
                version="v1.0.0",
                attribution_confidence_threshold=1.05,
            )
        assert "attribution_confidence_threshold" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            ScientificConfig(
                version="v1.0.0",
                abstention_confidence_threshold=-0.1,
            )
        assert "abstention_confidence_threshold" in str(exc_info.value)

    def test_config_immutability(self) -> None:
        """TEST 6: ScientificConfig is frozen and cannot be mutated after creation."""
        config = ScientificConfig(version="v1.0.0")
        with pytest.raises(ValidationError):
            config.spatial_cluster_radius_meters = 500.0  # type: ignore[misc]

    def test_deterministic_serialization_and_fingerprinting(self) -> None:
        """TEST 7: Identical configs produce identical canonical JSON and SHA-256."""
        fixed_time = datetime(2026, 8, 29, 12, 0, 0, tzinfo=UTC)
        c1 = ScientificConfig(
            version="v1.0.0",
            name="experiment_alpha",
            created_at=fixed_time,
            spatial_cluster_radius_meters=1500.0,
            temporal_window_hours=12.0,
            persistence_threshold_days=14.0,
            persistence_min_observations=3,
            attribution_radius_meters=3000.0,
            attribution_confidence_threshold=0.80,
            minimum_event_confidence=0.65,
            abstention_confidence_threshold=0.40,
        )

        c2 = ScientificConfig(
            version="v1.0.0",
            name="experiment_alpha",
            created_at=fixed_time,
            spatial_cluster_radius_meters=1500.0,
            temporal_window_hours=12.0,
            persistence_threshold_days=14.0,
            persistence_min_observations=3,
            attribution_radius_meters=3000.0,
            attribution_confidence_threshold=0.80,
            minimum_event_confidence=0.65,
            abstention_confidence_threshold=0.40,
        )

        assert c1.to_canonical_json() == c2.to_canonical_json()
        assert c1.compute_fingerprint() == c2.compute_fingerprint()

    def test_distinct_configurations_have_different_fingerprints(self) -> None:
        """TEST 8: Changing a parameter alters the configuration fingerprint."""
        fixed_time = datetime(2026, 8, 29, 12, 0, 0, tzinfo=UTC)
        c1 = ScientificConfig(
            version="v1.0.0",
            created_at=fixed_time,
            spatial_cluster_radius_meters=1000.0,
        )
        c2 = ScientificConfig(
            version="v1.0.0",
            created_at=fixed_time,
            spatial_cluster_radius_meters=2000.0,
        )

        assert c1.compute_fingerprint() != c2.compute_fingerprint()

    def test_operational_and_scientific_separation(self) -> None:
        """TEST 9: Settings and ScientificConfig remain strictly segregated."""
        # Operational fields must not be in ScientificConfig
        operational_keys = {
            "POSTGRES_DB",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "DATABASE_URL",
            "API_PORT",
            "DEBUG",
            "ENVIRONMENT",
        }
        for op_key in operational_keys:
            assert op_key.lower() not in ScientificConfig.model_fields

        # Scientific parameters must not be in Settings
        for sci_key in SCIENTIFIC_PARAMETER_FIELDS:
            assert sci_key not in Settings.model_fields
