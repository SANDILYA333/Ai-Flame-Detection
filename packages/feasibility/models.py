"""Domain models and data schemas for study-area feasibility assessment."""

from enum import StrEnum

from pydantic import Field

from packages.schemas.common import BaseDomainModel, BoundingBox, UtcDatetime


class FeasibilityLevel(StrEnum):
    """Categorical evaluation of study area data and evidence feasibility."""

    HIGH_FEASIBILITY = "HIGH_FEASIBILITY"
    MODERATE_FEASIBILITY = "MODERATE_FEASIBILITY"
    LIMITED_FEASIBILITY = "LIMITED_FEASIBILITY"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class StudyAreaRole(StrEnum):
    """Recommended role of a candidate study area in the benchmark design."""

    PRIMARY_BENCHMARK_CANDIDATE = "PRIMARY_BENCHMARK_CANDIDATE"
    CONTRAST_NEGATIVE_CONTROL = "CONTRAST_NEGATIVE_CONTROL"
    SECONDARY_VALIDATION = "SECONDARY_VALIDATION"
    RESERVE_CANDIDATE = "RESERVE_CANDIDATE"


class StudyArea(BaseDomainModel):
    """Definition of a candidate geographic study area in India."""

    area_id: str = Field(
        ...,
        min_length=1,
        description="Unique slug identifier (e.g. 'jamnagar_kutch').",
    )
    name: str = Field(
        ...,
        min_length=1,
        description="Human-readable study area title.",
    )
    state: str = Field(
        ...,
        min_length=1,
        description="Indian State(s) or administrative territory.",
    )
    bounding_box: BoundingBox = Field(
        ...,
        description="Geographic WGS-84 bounding envelope.",
    )
    approx_area_sqkm: float = Field(
        ...,
        gt=0.0,
        description="Approximate surface area in square kilometers.",
    )
    description: str = Field(
        ...,
        min_length=1,
        description="Summary of regional geography and industrial/natural activity.",
    )
    scientific_rationale: str = Field(
        ...,
        min_length=1,
        description="Scientific reason for evaluating this region as a candidate.",
    )
    is_provisional: bool = Field(
        default=True,
        description="Indicator that geography is provisional and not frozen.",
    )


class FirmsFeasibilityMetrics(BaseDomainModel):
    """Quantitative measurement of NASA FIRMS observation availability."""

    total_detections: int = Field(
        ...,
        ge=0,
        description="Total satellite detections within bounding envelope.",
    )
    unique_observation_dates: int = Field(
        ...,
        ge=0,
        description="Count of unique calendar dates with thermal observations.",
    )
    temporal_span_days: float = Field(
        ...,
        ge=0.0,
        description="Span in days from first to last observation.",
    )
    sensor_breakdown: dict[str, int] = Field(
        default_factory=dict,
        description="Detection counts partitioned by satellite/instrument.",
    )
    day_night_breakdown: dict[str, int] = Field(
        default_factory=dict,
        description="Detection counts partitioned by day/night passes.",
    )
    frp_mean_mw: float | None = Field(
        None,
        description="Mean Fire Radiative Power (MW).",
    )
    frp_max_mw: float | None = Field(
        None,
        description="Maximum Fire Radiative Power (MW).",
    )
    missing_frp_count: int = Field(
        0,
        ge=0,
        description="Count of detections lacking valid FRP measurements.",
    )
    spatial_density_per_sqkm: float = Field(
        ...,
        ge=0.0,
        description="Average detections per square kilometer.",
    )


class DerivationFeasibilityMetrics(BaseDomainModel):
    """Quantitative measurement of Phase 3 derived events and persistent sources."""

    candidate_events_count: int = Field(
        ...,
        ge=0,
        description="Total thermal events derived via spatiotemporal clustering.",
    )
    mean_detections_per_event: float = Field(
        ...,
        ge=0.0,
        description="Average detection count per derived event.",
    )
    candidate_sources_count: int = Field(
        ...,
        ge=0,
        description="Total longitudinal persistent sources tracked.",
    )
    persistence_state_breakdown: dict[str, int] = Field(
        default_factory=dict,
        description="Count of sources by state (PERSISTENT, RECURRING, etc.).",
    )
    persistent_source_density: float = Field(
        ...,
        ge=0.0,
        description="Persistent / recurring sources per 1,000 sq km.",
    )


class ContextFeasibilityMetrics(BaseDomainModel):
    """Quantitative measurement of contextual infrastructure availability."""

    total_context_features: int = Field(
        ...,
        ge=0,
        description="Total mapped contextual features within study area.",
    )
    context_by_category: dict[str, int] = Field(
        default_factory=dict,
        description="Contextual features partitioned by ContextType category.",
    )
    events_with_context_count: int = Field(
        ...,
        ge=0,
        description="Count of derived events with at least one nearby context feature.",
    )
    context_coverage_ratio: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Fraction of derived events having proximate contextual evidence.",
    )


class ReferenceFeasibilityMetrics(BaseDomainModel):
    """Quantitative measurement of candidate reference / ground-truth evidence."""

    candidate_reference_points: int = Field(
        ...,
        ge=0,
        description="Total candidate reference facilities / known emission points.",
    )
    reference_by_source: dict[str, int] = Field(
        default_factory=dict,
        description="Reference points partitioned by originating database.",
    )
    reference_by_tier: dict[str, int] = Field(
        default_factory=dict,
        description="Reference points partitioned by tier (Tier A, Tier B, Tier C).",
    )
    events_with_reference_count: int = Field(
        ...,
        ge=0,
        description="Count of events associated with known reference points.",
    )
    reference_coverage_ratio: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Fraction of events having reference evidence.",
    )


class FeasibilityAssessment(BaseDomainModel):
    """Comprehensive feasibility evaluation for a single candidate study area."""

    study_area: StudyArea
    firms_metrics: FirmsFeasibilityMetrics
    derivation_metrics: DerivationFeasibilityMetrics
    context_metrics: ContextFeasibilityMetrics
    reference_metrics: ReferenceFeasibilityMetrics
    data_adequacy_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Composite score (0.0 to 1.0) of data sufficiency.",
    )
    source_diversity_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Composite score (0.0 to 1.0) of multi-source thermal diversity.",
    )
    overall_feasibility: FeasibilityLevel
    recommended_role: StudyAreaRole
    key_strengths: list[str] = Field(default_factory=list)
    major_limitations: list[str] = Field(default_factory=list)


class FeasibilityComparativeReport(BaseDomainModel):
    """Comprehensive multi-region comparative study-area feasibility report."""

    generated_at: UtcDatetime
    harness_version: str = Field(..., min_length=1)
    scientific_config_version: str = Field(..., min_length=1)
    scientific_config_fingerprint: str = Field(..., min_length=1)
    candidate_assessments: list[FeasibilityAssessment] = Field(default_factory=list)
    comparative_ranking: list[str] = Field(
        default_factory=list,
        description="Ranked study area IDs from most to least feasible.",
    )
    measured_findings: list[str] = Field(default_factory=list)
    inferred_insights: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
