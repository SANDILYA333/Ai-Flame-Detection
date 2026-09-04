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


class TemporalBaselineTelemetry(BaseDomainModel):
    """Telemetry and anomaly metrics from 90-day rolling baseline."""

    recurrence_90d: float = Field(
        ..., ge=0.0, le=1.0, description="Fraction of active calendar days in 90-day window."
    )
    historical_mean_frp: float = Field(
        ..., ge=0.0, description="Mean historical FRP in MW."
    )
    historical_std_frp: float = Field(
        ..., ge=0.0, description="Sample standard deviation of historical FRP in MW."
    )
    sample_count: int = Field(..., ge=0, description="Count of historical observations.")
    active_calendar_days: int = Field(
        ..., ge=0, description="Number of unique active calendar days."
    )
    frp_z_score: float = Field(..., description="FRP Z-score anomaly metric.")
    frp_surge_ratio: float = Field(..., description="Ratio of current FRP to historical mean.")
    operational_status: str = Field(
        ..., description="Operational interpretation (e.g. ROUTINE_PERSISTENT_FLARING)."
    )
    is_critical_anomaly: bool = Field(
        default=False, description="Whether event qualifies as critical thermal surge."
    )
    window_days: int = Field(default=90, description="Historical window span in days.")
    radius_km: float = Field(default=1.0, description="Spatial search radius in km.")
    is_cold_start: bool = Field(
        default=False, description="Whether baseline operates in cold-start regime."
    )


class PyrometryTelemetry(BaseDomainModel):
    """Planck / Dozier dual-band radiance pyrometry telemetry."""

    available: bool = Field(
        default=True, description="Whether dual-band radiometric inversion was possible."
    )
    emitter_temp_k: float = Field(
        ..., description="True flame/emitter temperature in Kelvin."
    )
    emitter_area_m2: float = Field(
        ..., description="Sub-pixel flame area in square meters."
    )
    fractional_area_p: float | None = Field(
        None, description="Fractional sub-pixel area ratio p."
    )
    background_temp_k: float = Field(
        default=295.0, description="Ambient background temperature in Kelvin."
    )
    mwir_radiance_observed: float | None = Field(
        None, description="Observed MWIR radiance."
    )
    lwir_radiance_observed: float | None = Field(
        None, description="Observed LWIR radiance."
    )
    radiance_residual: float | None = Field(
        None, description="Relative radiance optimization residual loss."
    )
    is_valid: bool = Field(
        default=True, description="Whether solver converged within physical bounds."
    )
    convergence_status: str = Field(
        default="CONVERGED", description="Solver convergence status tag."
    )
    phenomenon_tag: str = Field(
        default="INTERMEDIATE_COMBUSTION_SOURCE",
        description="Physical phenomenon classification tag.",
    )


class FeatureAttributionTelemetry(BaseDomainModel):
    """Individual feature Shapley attribution."""

    feature: str = Field(..., description="Human-readable feature name.")
    raw_feature_name: str = Field(..., description="Internal feature key.")
    value: str | float | int | bool | None = Field(
        None, description="Observed feature value."
    )
    shap_value: float = Field(..., description="Raw Shapley attribution value.")
    impact: str = Field(
        ..., description="Directional impact ('supports_predicted', 'opposes_predicted', 'neutral')."
    )
    description: str = Field(..., description="Operational / physical interpretation.")


class ShapExplanationTelemetry(BaseDomainModel):
    """Container for XAI feature attribution explanation."""

    target_class: str = Field(..., description="Class explained by attributions.")
    base_value: float = Field(default=0.5, description="Expected base value probability.")
    predicted_probability: float = Field(..., description="Model predicted probability.")
    attribution_method: str = Field(
        default="TREE_SHAP", description="Attribution method (e.g. TREE_SHAP or DOMAIN_FALLBACK)."
    )
    attributions: list[FeatureAttributionTelemetry] = Field(
        default_factory=list, description="Ranked feature attributions."
    )


class IntelligenceResult(BaseDomainModel):
    """Canonical Intelligence Result preserving the orthogonal ontology.

    Combines independent dimensions:
    1. Phenomenon: Physical thermal process (flare, fire, unknown, etc.)
    2. Context: Surrounding environment (industrial, oil_gas, agriculture)
    3. Persistence: Observed temporal pattern (persistent, recurring)
    4. Attribution: Association strength with contextual facilities
    5. Uncertainty: Explicit calibrated confidence and abstention state
    6. Evidence Completeness: Detailed breakdown of available/missing evidence
    7. Temporal Baseline: 90-day historical window & anomaly metrics
    8. Pyrometry: Sub-pixel Planck/Dozier temperature and area
    9. XAI / SHAP: Shapley feature attributions
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

    # Scientific Intelligence Capabilities
    temporal_baseline: TemporalBaselineTelemetry | None = Field(
        None,
        description="Rolling 90-day historical baseline and anomaly metrics.",
    )
    pyrometry: PyrometryTelemetry | None = Field(
        None,
        description="Sub-pixel Planck/Dozier pyrometry inversion results.",
    )
    xai: ShapExplanationTelemetry | None = Field(
        None,
        description="SHAP feature attribution explanations.",
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
