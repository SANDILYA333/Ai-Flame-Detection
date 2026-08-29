"""Canonical Intelligence and Inference domain models."""

import math

from pydantic import Field, field_validator, model_validator

from packages.schemas.common import BaseDomainModel, UtcDatetime
from packages.schemas.enums import (
    AttributionStrength,
    ContextType,
    EvidenceAvailabilityState,
    PersistenceState,
    PhenomenonType,
)


class UncertaintyMetric(BaseDomainModel):
    """Structured uncertainty representation for intelligence inference.

    IMPORTANT ARCHITECTURAL INVARIANTS:
    - Model probability, calibrated confidence, and data quality are distinct.
    - Low-evidence or high-uncertainty events may trigger abstention.
    - Abstention (selective classification) is a valid, first-class outcome.
    """

    model_probability: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Raw output probability from model (0.0 to 1.0).",
    )
    calibrated_confidence: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Post-hoc calibrated confidence estimate (0.0 to 1.0).",
    )
    data_quality_score: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Composite input data quality score (0.0 to 1.0).",
    )
    abstention_recommended: bool = Field(
        default=False,
        description="Whether system recommends abstaining from label.",
    )
    abstention_reason: str | None = Field(
        None,
        description="Explanation for why abstention was triggered.",
    )

    @field_validator(
        "model_probability",
        "calibrated_confidence",
        "data_quality_score",
        mode="after",
    )
    @classmethod
    def _validate_finite_optional(cls, v: float | None) -> float | None:
        if v is not None and not math.isfinite(v):
            raise ValueError("Uncertainty metric value must be finite.")
        return v


class EvidenceCategoryState(BaseDomainModel):
    """Availability and provenance state for an individual evidence category."""

    category: str = Field(
        ...,
        min_length=1,
        description="Evidence category name (e.g. 'firms', 'satellite').",
    )
    status: EvidenceAvailabilityState = Field(
        ...,
        description="Availability status of this evidence category.",
    )
    details: str | None = Field(
        None,
        description="Contextual details on acquisition or unavailability.",
    )


class EvidenceCompleteness(BaseDomainModel):
    """Structured breakdown of evidence availability across categories.

    Prevents missing evidence (e.g. unavailable satellite imagery)
    from being conflated with evidence of absence.
    """

    categories: list[EvidenceCategoryState] = Field(
        default_factory=list,
        description="Status breakdown across all evaluated categories.",
    )
    available_count: int = Field(
        0,
        ge=0,
        description="Count of successfully acquired evidence categories.",
    )
    total_expected_count: int = Field(
        0,
        ge=0,
        description="Total count of expected evidence categories.",
    )
    completeness_ratio: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Ratio of available to expected categories (0.0 to 1.0).",
    )

    @field_validator("completeness_ratio", mode="after")
    @classmethod
    def _validate_finite_optional(cls, v: float | None) -> float | None:
        if v is not None and not math.isfinite(v):
            raise ValueError("completeness_ratio must be finite.")
        return v

    @model_validator(mode="after")
    def _validate_counts(self) -> "EvidenceCompleteness":
        if (
            self.available_count > self.total_expected_count
            and self.total_expected_count > 0
        ):
            raise ValueError(
                f"available_count ({self.available_count}) cannot exceed "
                f"total_expected_count ({self.total_expected_count})."
            )
        return self


class IntelligenceResult(BaseDomainModel):
    """Canonical Intelligence Result preserving the orthogonal ontology.

    Combines independent dimensions:
    1. Phenomenon: Physical thermal process (flare, fire, unknown, etc.)
    2. Context: Surrounding environment (industrial, oil_gas, agriculture)
    3. Persistence: Observed temporal pattern (persistent, recurring)
    4. Attribution: Association strength with contextual facilities
    5. Uncertainty: Explicit calibrated confidence and abstention state
    6. Evidence Completeness: Detailed breakdown of available/missing evidence
    """

    intelligence_id: str = Field(
        ...,
        min_length=1,
        description="Unique canonical identifier for intelligence result.",
    )
    event_id: str = Field(
        ...,
        min_length=1,
        description="Identifier of thermal event evaluated.",
    )
    phenomenon: PhenomenonType = Field(
        ...,
        description="Physical phenomenon classification (orthogonal).",
    )
    context: ContextType = Field(
        ...,
        description="Contextual site classification (orthogonal).",
    )
    persistence: PersistenceState = Field(
        ...,
        description="Temporal persistence classification (orthogonal).",
    )
    attribution: AttributionStrength = Field(
        ...,
        description="Attribution strength linking event to context.",
    )
    uncertainty: UncertaintyMetric = Field(
        ...,
        description="Structured uncertainty and calibration metrics.",
    )
    evidence_completeness: EvidenceCompleteness = Field(
        ...,
        description="Breakdown of evidence availability.",
    )
    created_at: UtcDatetime = Field(
        ...,
        description="Timestamp when intelligence result was generated in UTC.",
    )

    # Optional linkage and provenance
    source_id: str | None = Field(
        None,
        min_length=1,
        description="Identifier of associated persistent source if linked.",
    )
    pipeline_run_id: str | None = Field(
        None,
        min_length=1,
        description="Lineage identifier of inference pipeline execution.",
    )
    model_version: str | None = Field(
        None,
        min_length=1,
        description="Version of ML model or rule engine used.",
    )
    configuration_version: str | None = Field(
        None,
        min_length=1,
        description="Version of intelligence configuration contract.",
    )
    notes: str | None = Field(
        None,
        description="Explanatory analyst notes or structured summaries.",
    )
