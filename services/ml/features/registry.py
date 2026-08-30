"""Feature registry and availability timing validator for Phase 4 ML.

Provides centralized registration, metadata querying, and temporal availability
verification for engineered features across real-time and batch inference modes.
"""

from datetime import datetime
from typing import Any

from packages.errors import (
    ConflictError,
    NotFoundError,
)
from packages.schemas.ml import (
    FeatureDefinition,
    FeatureMissingnessHandling,
    InferenceMode,
    LeakageRisk,
)


class FeatureRegistry:
    """Registry managing engineered ML feature definitions and availability rules."""

    def __init__(self) -> None:
        self._features: dict[str, FeatureDefinition] = {}

    def register(self, feature: FeatureDefinition) -> None:
        """Register a feature definition in the registry.

        Raises:
            ConflictError: If a feature with the same name and a different version
                or definition already exists.
        """
        if feature.feature_name in self._features:
            existing = self._features[feature.feature_name]
            if existing != feature:
                msg = (
                    f"Feature '{feature.feature_name}' already registered "
                    f"with version '{existing.version}', cannot overwrite "
                    f"with '{feature.version}'."
                )
                raise ConflictError(
                    msg,
                    details={
                        "feature_name": feature.feature_name,
                        "existing_version": existing.version,
                        "new_version": feature.version,
                    },
                )
            return

        self._features[feature.feature_name] = feature

    def get(self, feature_name: str) -> FeatureDefinition:
        """Retrieve a registered feature definition.

        Raises:
            NotFoundError: If feature_name is not registered.
        """
        if feature_name not in self._features:
            raise NotFoundError(
                f"Feature '{feature_name}' not found in registry.",
                details={"feature_name": feature_name},
            )
        return self._features[feature_name]

    def list_features(
        self, allowed_only: bool = False, version: str | None = None
    ) -> list[FeatureDefinition]:
        """List all registered features matching filter criteria."""
        results: list[FeatureDefinition] = []
        for feat in self._features.values():
            if allowed_only and not feat.allowed_for_training:
                continue
            if version is not None and feat.version != version:
                continue
            results.append(feat)
        return sorted(results, key=lambda f: f.feature_name)

    def validate_availability(
        self,
        feature_name: str,
        observation_time: datetime,
        prediction_time: datetime,
        inference_mode: InferenceMode,
        max_allowed_nrt_latency_seconds: float | None = None,
    ) -> tuple[bool, str | None]:
        """Validate if a feature is temporally available at prediction time.

        Rules:
        1. Observation time <= prediction_time
        2. Feature availability time <= prediction_time
        3. For REAL_TIME_NRT, lag <= max_allowed_nrt_latency_seconds.
        4. Feature cannot have DIRECT_LEAKAGE, TEMPORAL_LEAKAGE, etc.

        Returns:
            Tuple of (is_valid, rejection_reason)
        """
        feature = self.get(feature_name)

        # Check leakage risk
        if feature.leakage_risk in (
            LeakageRisk.DIRECT_LEAKAGE,
            LeakageRisk.TEMPORAL_LEAKAGE,
            LeakageRisk.LABEL_CONTAMINATION,
        ):
            reason = (
                f"Feature '{feature_name}' is disqualified due to "
                f"{feature.leakage_risk.value}."
            )
            return False, reason

        # Check future observation
        if observation_time > prediction_time:
            reason = (
                f"Feature '{feature_name}' observation time "
                f"({observation_time.isoformat()}) is in the future "
                f"relative to prediction time ({prediction_time.isoformat()})."
            )
            return False, reason

        # Check availability lag relative to prediction time
        elapsed_seconds = (prediction_time - observation_time).total_seconds()
        if elapsed_seconds < feature.availability_lag_seconds:
            reason = (
                f"Feature '{feature_name}' requires "
                f"{feature.availability_lag_seconds}s lag, but only "
                f"{elapsed_seconds:.1f}s elapsed at prediction time."
            )
            return False, reason

        # Check NRT latency constraint
        if (
            inference_mode == InferenceMode.REAL_TIME_NRT
            and max_allowed_nrt_latency_seconds is not None
            and feature.availability_lag_seconds > max_allowed_nrt_latency_seconds
        ):
            reason = (
                f"Feature '{feature_name}' lag "
                f"({feature.availability_lag_seconds}s) exceeds "
                f"max NRT threshold ({max_allowed_nrt_latency_seconds}s)."
            )
            return False, reason

        return True, None

    def validate_feature_set_for_mode(
        self,
        feature_names: list[str],
        inference_mode: InferenceMode,
        max_allowed_nrt_latency_seconds: float | None = None,
    ) -> list[str]:
        """Validate an entire feature set for operational eligibility.

        Returns:
            List of error/warning violation messages (empty if fully valid).
        """
        violations: list[str] = []
        for name in feature_names:
            try:
                feat = self.get(name)
            except NotFoundError:
                violations.append(f"Feature '{name}' is not registered.")
                continue

            if not feat.allowed_for_training:
                violations.append(
                    f"Feature '{name}' is marked allowed_for_training=False."
                )

            if feat.leakage_risk != LeakageRisk.SAFE:
                violations.append(
                    f"Feature '{name}' has leakage risk '{feat.leakage_risk.value}'."
                )

            if (
                inference_mode == InferenceMode.REAL_TIME_NRT
                and max_allowed_nrt_latency_seconds is not None
                and feat.availability_lag_seconds > max_allowed_nrt_latency_seconds
            ):
                violations.append(
                    f"Feature '{name}' lag ({feat.availability_lag_seconds}s) "
                    f"exceeds NRT limit ({max_allowed_nrt_latency_seconds}s)."
                )

        return violations

    def check_missingness_handling(
        self, feature_name: str, value: Any
    ) -> tuple[bool, str | None]:
        """Verify that missing values respect the feature's contract.

        Scientific Rule: missing != zero, missing != negative, missing != absence.
        """
        feature = self.get(feature_name)
        if value is None:
            if (
                feature.missingness_handling
                == FeatureMissingnessHandling.IMPUTATION_PROHIBITED
            ):
                return (
                    False,
                    f"Feature '{feature_name}' prohibits imputation for None values.",
                )
            return True, None

        if (
            value == 0
            and feature.missingness_handling == FeatureMissingnessHandling.PRESERVE_NONE
        ):
            return (
                True,
                "Warning: numeric 0 provided for feature preserving None.",
            )

        return True, None
