"""Canonical Machine Learning configuration contract for SIH26162.

Provides a typed, versioned, and immutable configuration contract governing
target definitions, feature selections, splitting rules, calibration methods,
evaluation metrics, and abstention parameters.
All ML parameters default to None (explicit incomplete state) to prevent
unapproved scientific assumptions from being silently injected.
"""

import hashlib
import json
import math
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from packages.errors import MissingConfigurationError
from packages.schemas.ml import (
    CalibrationMethod,
    SplitPartition,
    SplitStrategy,
    TargetType,
    TargetUnit,
)

ML_PARAMETER_FIELDS: frozenset[str] = frozenset(
    {
        "target_name",
        "target_type",
        "target_unit",
        "class_vocabulary",
        "feature_set_version",
        "allowed_feature_names",
        "split_strategy",
        "train_ratio",
        "validation_ratio",
        "test_ratio",
        "random_seed",
        "required_metrics",
        "primary_metric",
    }
)


class MLConfig(BaseModel):
    """Canonical contract for Phase 4 ML experiment and pipeline configuration.

    Defines explicit types and constraints. All scientific and operational parameters
    default to None to represent an uncalibrated / unapproved configuration state.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # 1. Contract Identification & Provenance
    version: str = Field(
        ...,
        min_length=1,
        description="Version string for ML configuration contract.",
    )
    name: str = Field(
        default="default_ml_config",
        description="Human-readable identifier for configuration profile.",
    )
    description: str = Field(
        default="",
        description="Scientific justification, experimental notes, or calibration.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC creation timestamp for provenance tracking.",
    )

    # 2. Target Specification
    target_name: str | None = Field(
        default=None,
        min_length=1,
        description="Identifier of prediction target.",
    )
    target_type: TargetType | None = Field(
        default=None,
        description="Mathematical formulation of target.",
    )
    target_unit: TargetUnit | None = Field(
        default=None,
        description="Unit of prediction (Event, Source, Detection).",
    )
    class_vocabulary: tuple[str, ...] | None = Field(
        default=None,
        description="Permitted class vocabulary strings (immutable tuple).",
    )

    # 3. Feature Selection & Timing Rules
    feature_set_version: str | None = Field(
        default=None,
        min_length=1,
        description="Version identifier of feature engineering manifest.",
    )
    allowed_feature_names: tuple[str, ...] | None = Field(
        default=None,
        description="List of feature names permitted in this configuration.",
    )
    max_allowed_nrt_latency_seconds: float | None = Field(
        default=None,
        ge=0.0,
        description="Max feature latency allowed for NRT inference mode.",
    )

    # 4. Split Strategy & Partitioning
    split_strategy: SplitStrategy | None = Field(
        default=None,
        description="Data splitting strategy.",
    )
    train_ratio: float | None = Field(
        default=None,
        gt=0.0,
        lt=1.0,
        description="Fraction allocated to train partition.",
    )
    validation_ratio: float | None = Field(
        default=None,
        gt=0.0,
        lt=1.0,
        description="Fraction allocated to validation partition.",
    )
    test_ratio: float | None = Field(
        default=None,
        gt=0.0,
        lt=1.0,
        description="Fraction allocated to test partition.",
    )
    random_seed: int | None = Field(
        default=None,
        ge=0,
        description="Explicit random seed for deterministic operations.",
    )
    isolated_showcase_ids: tuple[str, ...] = Field(
        default_factory=tuple,
        description="List of entity IDs permanently isolated from train/val/test.",
    )

    # 5. Evaluation Protocol
    required_metrics: tuple[str, ...] | None = Field(
        default=None,
        description="Metrics required to be computed during evaluation.",
    )
    primary_metric: str | None = Field(
        default=None,
        min_length=1,
        description="Primary metric for benchmark ranking (e.g. 'macro_f1').",
    )

    # 6. Calibration Parameters
    calibration_method: CalibrationMethod | None = Field(
        default=None,
        description="Probability calibration method.",
    )
    calibration_split_partition: SplitPartition | None = Field(
        default=None,
        description="Partition used for calibration fitting.",
    )

    # 7. Abstention Parameters
    abstention_enabled: bool = Field(
        default=True,
        description="Whether model abstention is enabled.",
    )
    confidence_cutoff: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence cutoff below which model abstains.",
    )
    max_uncertainty_cutoff: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Uncertainty score above which model abstains.",
    )
    min_completeness_ratio: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum evidence completeness ratio required.",
    )

    @field_validator("calibration_split_partition", mode="after")
    @classmethod
    def _validate_not_test_split(
        cls, v: SplitPartition | None
    ) -> SplitPartition | None:
        if v == SplitPartition.TEST:
            raise ValueError(
                "Calibration split partition cannot be TEST (leakage violation)."
            )
        return v

    @model_validator(mode="after")
    def _validate_split_ratios(self) -> "MLConfig":
        if (
            self.train_ratio is not None
            and self.validation_ratio is not None
            and self.test_ratio is not None
        ):
            total = self.train_ratio + self.validation_ratio + self.test_ratio
            if not math.isclose(total, 1.0, rel_tol=1e-5):
                raise ValueError(
                    f"train_ratio ({self.train_ratio}) + "
                    f"validation_ratio ({self.validation_ratio}) + "
                    f"test_ratio ({self.test_ratio}) must sum to 1.0, got {total:.5f}."
                )
        return self

    @property
    def is_complete(self) -> bool:
        """Return True if all core ML configuration parameters are populated."""
        return len(self.missing_parameters) == 0

    @property
    def missing_parameters(self) -> list[str]:
        """Return a sorted list of unset core ML parameter names."""
        return sorted(
            field for field in ML_PARAMETER_FIELDS if getattr(self, field) is None
        )

    def validate_completeness(self) -> None:
        """Validate that all core ML parameters are configured before execution.

        Raises:
            MissingConfigurationError: If any required parameter is None.
        """
        missing = self.missing_parameters
        if missing:
            msg = (
                f"ML configuration '{self.version}' is incomplete. "
                f"Unset parameters: {', '.join(missing)}"
            )
            raise MissingConfigurationError(
                msg,
                details={
                    "version": self.version,
                    "missing_parameters": missing,
                },
            )

    def to_canonical_dict(self) -> dict[str, Any]:
        """Produce a deterministic, sorted dictionary of this configuration."""
        raw = self.model_dump()
        raw["created_at"] = self.created_at.isoformat()
        # Convert tuples/lists to sorted formats where appropriate
        return {k: raw[k] for k in sorted(raw.keys())}

    def to_canonical_json(self) -> str:
        """Produce a deterministic canonical JSON string suitable for hashing."""
        return json.dumps(
            self.to_canonical_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=str,
        )

    def compute_fingerprint(self) -> str:
        """Compute the SHA-256 hex digest of canonical JSON for provenance."""
        canonical_bytes = self.to_canonical_json().encode("utf-8")
        return hashlib.sha256(canonical_bytes).hexdigest()
