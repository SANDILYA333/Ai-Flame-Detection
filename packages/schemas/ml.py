"""Canonical domain models and enumerations for Phase 4 Machine Learning readiness.

This module establishes the foundational contracts for:
- Supervised prediction targets and class vocabularies
- Reference label provenance and quality tiers
- Feature definitions, availability lag, and missingness semantics
- Dataset manifests with deterministic hashing and reproducibility tracking
- Grouped/spatial/temporal split assignments and integrity validation
- Multi-class and per-class evaluation metrics and confusion matrices
- Calibration and abstention metadata representations
- Machine learning readiness assessment
"""

import hashlib
import json
import math
from enum import StrEnum
from typing import Any

from pydantic import Field, field_validator, model_validator

from packages.schemas.common import (
    BaseDomainModel,
    Coordinate,
    ProvenanceReference,
    UtcDatetime,
)
from packages.schemas.enums import SourceRole


class ReadinessStatus(StrEnum):
    """Categorical evaluation of ML readiness for a task or milestone."""

    READY = "READY"
    NOT_READY = "NOT_READY"
    BLOCKED = "BLOCKED"
    PROVISIONAL = "PROVISIONAL"


class TargetType(StrEnum):
    """Mathematical formulation of the machine learning prediction target."""

    BINARY_CLASSIFICATION = "BINARY_CLASSIFICATION"
    MULTICLASS_CLASSIFICATION = "MULTICLASS_CLASSIFICATION"
    MULTI_LABEL_CLASSIFICATION = "MULTI_LABEL_CLASSIFICATION"
    REGRESSION = "REGRESSION"
    ORDINAL_CLASSIFICATION = "ORDINAL_CLASSIFICATION"


class TargetUnit(StrEnum):
    """Fundamental unit of observation or entity being classified/predicted."""

    DETECTION = "DETECTION"
    EVENT = "EVENT"
    SOURCE = "SOURCE"
    SPATIAL_CLUSTER = "SPATIAL_CLUSTER"


class LabelTier(StrEnum):
    """Hierarchical reliability tier for reference labels.

    Tier A: Authoritative ground truth with direct verifiable confirmation.
    Tier B: Strong independent evidence (e.g. high-resolution optical corroboration).
    Tier C: Proxy/weak heuristic labels (must NEVER be claimed as ground truth).
    """

    TIER_A_AUTHORITATIVE = "TIER_A_AUTHORITATIVE"
    TIER_B_STRONG_EVIDENCE = "TIER_B_STRONG_EVIDENCE"
    TIER_C_PROXY_WEAK = "TIER_C_PROXY_WEAK"
    UNVERIFIED_HEURISTIC = "UNVERIFIED_HEURISTIC"
    UNKNOWN = "UNKNOWN"


class LabelProvenanceType(StrEnum):
    """Taxonomy of how a label was generated or attributed."""

    GROUND_TRUTH = "GROUND_TRUTH"
    REFERENCE_LABEL = "REFERENCE_LABEL"
    WEAK_LABEL = "WEAK_LABEL"
    PSEUDO_LABEL = "PSEUDO_LABEL"
    DETERMINISTIC_INFERENCE = "DETERMINISTIC_INFERENCE"
    UNKNOWN = "UNKNOWN"


class ExclusionReason(StrEnum):
    """Explicit rationale for excluding a sample from supervised training/eval."""

    INSUFFICIENT_LABEL_EVIDENCE = "INSUFFICIENT_LABEL_EVIDENCE"
    CONFLICTING_LABEL_EVIDENCE = "CONFLICTING_LABEL_EVIDENCE"
    PROHIBITED_FEATURE_LEAKAGE = "PROHIBITED_FEATURE_LEAKAGE"
    SHOWCASE_ISOLATION = "SHOWCASE_ISOLATION"
    MISSING_REQUIRED_FEATURES = "MISSING_REQUIRED_FEATURES"
    AMBIGUOUS_CLASS = "AMBIGUOUS_CLASS"
    OUTSIDE_SPATIOTEMPORAL_SCOPE = "OUTSIDE_SPATIOTEMPORAL_SCOPE"


class DatasetRowStatus(StrEnum):
    """Supervised dataset sample eligibility status."""

    TRAIN_ELIGIBLE = "TRAIN_ELIGIBLE"
    VALIDATION_ELIGIBLE = "VALIDATION_ELIGIBLE"
    TEST_ELIGIBLE = "TEST_ELIGIBLE"
    SHOWCASE_ISOLATED = "SHOWCASE_ISOLATED"
    EXCLUDED = "EXCLUDED"
    UNLABELED = "UNLABELED"


class LabelConflictPolicy(StrEnum):
    """Policy for resolving conflicting evidence across reference sources."""

    TIER_PRECEDENCE = "TIER_PRECEDENCE"
    STRICT_CONSENSUS = "STRICT_CONSENSUS"
    AUTHORITATIVE_OVERRIDE = "AUTHORITATIVE_OVERRIDE"


class FeatureType(StrEnum):
    """Data representation type for machine learning features."""

    NUMERIC = "NUMERIC"
    CATEGORICAL = "CATEGORICAL"
    BOOLEAN = "BOOLEAN"
    GEOSPATIAL_DISTANCE = "GEOSPATIAL_DISTANCE"
    TEMPORAL_SPAN = "TEMPORAL_SPAN"
    EMBEDDING = "EMBEDDING"
    COUNT = "COUNT"


class FeatureGroup(StrEnum):
    """Logical grouping of features for ablation studies and provenance."""

    THERMAL_CORE = "THERMAL_CORE"
    TEMPORAL_HISTORY = "TEMPORAL_HISTORY"
    PERSISTENCE_SOURCE = "PERSISTENCE_SOURCE"
    SPATIAL_CONTEXT = "SPATIAL_CONTEXT"
    LAND_COVER = "LAND_COVER"
    ENVIRONMENTAL_WEATHER = "ENVIRONMENTAL_WEATHER"
    SATELLITE_OPTICAL = "SATELLITE_OPTICAL"


class FeatureEligibilityStatus(StrEnum):
    """Eligibility classification for candidate features in ML models."""

    APPROVED = "APPROVED"
    CONTEXT_ONLY = "CONTEXT_ONLY"
    LABEL_REFERENCE = "LABEL_REFERENCE"
    VALIDATION_ONLY = "VALIDATION_ONLY"
    OPTIONAL = "OPTIONAL"
    REJECTED = "REJECTED"
    BLOCKED = "BLOCKED"


class LeakageRisk(StrEnum):
    """Classification of potential data leakage risk for a feature."""

    SAFE = "SAFE"
    DIRECT_LEAKAGE = "DIRECT_LEAKAGE"
    INDIRECT_LEAKAGE = "INDIRECT_LEAKAGE"
    TEMPORAL_LEAKAGE = "TEMPORAL_LEAKAGE"
    SPATIAL_LEAKAGE = "SPATIAL_LEAKAGE"
    LABEL_CONTAMINATION = "LABEL_CONTAMINATION"
    UNKNOWN = "UNKNOWN"


class FeatureMissingnessHandling(StrEnum):
    """Semantic strategy for handling missing feature values.

    Enforces the scientific rule: missing != zero, missing != negative,
    missing != absence.
    """

    EXPLICIT_INDICATOR = "EXPLICIT_INDICATOR"
    PRESERVE_NONE = "PRESERVE_NONE"
    DOMAIN_SENTINEL = "DOMAIN_SENTINEL"
    IMPUTATION_PROHIBITED = "IMPUTATION_PROHIBITED"
    ALLOW_IMPUTATION = "ALLOW_IMPUTATION"


class InferenceMode(StrEnum):
    """Operational mode in which predictions will be generated."""

    REAL_TIME_NRT = "REAL_TIME_NRT"
    HOURLY_BATCH = "HOURLY_BATCH"
    DAILY_BATCH = "DAILY_BATCH"
    RETROSPECTIVE_ANALYSIS = "RETROSPECTIVE_ANALYSIS"
    HISTORICAL_BENCHMARK = "HISTORICAL_BENCHMARK"


class SplitStrategy(StrEnum):
    """Evaluation data splitting protocol preventing data leakage."""

    TEMPORAL_HOLDOUT = "TEMPORAL_HOLDOUT"
    SPATIAL_GEOGRAPHIC_HOLDOUT = "SPATIAL_GEOGRAPHIC_HOLDOUT"
    PERSISTENT_SOURCE_HOLDOUT = "PERSISTENT_SOURCE_HOLDOUT"
    GROUPED_EVENT_HOLDOUT = "GROUPED_EVENT_HOLDOUT"
    FACILITY_HOLDOUT = "FACILITY_HOLDOUT"
    SOURCE_SENSOR_HOLDOUT = "SOURCE_SENSOR_HOLDOUT"
    SPATIO_TEMPORAL_SOURCE_GROUPED = "SPATIO_TEMPORAL_SOURCE_GROUPED"
    STRATIFIED_GROUPED = "STRATIFIED_GROUPED"


class SplitPartition(StrEnum):
    """Designation of dataset partition."""

    TRAIN = "TRAIN"
    VALIDATION = "VALIDATION"
    TEST = "TEST"
    CALIBRATION = "CALIBRATION"
    SHOWCASE_ISOLATION = "SHOWCASE_ISOLATION"


class CalibrationMethod(StrEnum):
    """Method used for post-hoc probability calibration."""

    PLATT_SCALING = "PLATT_SCALING"
    ISOTONIC_REGRESSION = "ISOTONIC_REGRESSION"
    TEMPERATURE_SCALING = "TEMPERATURE_SCALING"
    BETA_CALIBRATION = "BETA_CALIBRATION"
    NONE_RAW = "NONE_RAW"


class AbstentionReason(StrEnum):
    """Reason why an ML or intelligence model chose to abstain from prediction."""

    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    HIGH_UNCERTAINTY = "HIGH_UNCERTAINTY"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    OUT_OF_DISTRIBUTION = "OUT_OF_DISTRIBUTION"
    MISSING_CRITICAL_CONTEXT = "MISSING_CRITICAL_CONTEXT"
    UNRESOLVED_DISAGREEMENT = "UNRESOLVED_DISAGREEMENT"
    NONE = "NONE"


# ---------------------------------------------------------------------------
# Domain Models
# ---------------------------------------------------------------------------


class TargetDefinition(BaseDomainModel):
    """Specification of an ML prediction target and class vocabulary."""

    target_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for the target specification.",
    )
    name: str = Field(
        ...,
        min_length=1,
        description="Human-readable name of the target.",
    )
    target_type: TargetType = Field(
        ...,
        description="Mathematical formulation (binary, multiclass, etc.).",
    )
    unit_of_prediction: TargetUnit = Field(
        ...,
        description="Entity unit being classified (Event, Source, Detection).",
    )
    class_vocabulary: list[str] = Field(
        default_factory=list,
        description="Permitted class vocabulary strings.",
    )
    positive_definition: str | None = Field(
        None,
        description="Scientific definition of positive class if binary.",
    )
    negative_definition: str | None = Field(
        None,
        description="Scientific definition of negative/background class.",
    )
    unknown_definition: str | None = Field(
        None,
        description="Scientific definition of unknown/unresolved class.",
    )
    is_approved: bool = Field(
        default=False,
        description="Whether taxonomy and definition are officially frozen/approved.",
    )
    unresolved_reason: str | None = Field(
        None,
        description="Explanation if target definition remains open or unapproved.",
    )


class LabelMetadata(BaseDomainModel):
    """Provenance and quality metadata for an individual reference label."""

    label_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for the label instance.",
    )
    target_id: str = Field(
        ...,
        min_length=1,
        description="Target definition identifier this label satisfies.",
    )
    entity_id: str = Field(
        ...,
        min_length=1,
        description="Entity ID (detection_id, event_id, or source_id).",
    )
    label_value: str = Field(
        ...,
        min_length=1,
        description="The assigned label value from class vocabulary.",
    )
    label_tier: LabelTier = Field(
        ...,
        description="Quality and reliability tier of the label.",
    )
    provenance_type: LabelProvenanceType = Field(
        ...,
        description="Generation method / provenance classification.",
    )
    source_name: str = Field(
        ...,
        min_length=1,
        description="Originating source or catalog name.",
    )
    source_url: str | None = Field(
        None,
        description="URL reference to original data if available.",
    )
    source_date: UtcDatetime | None = Field(
        None,
        description="Publication or observation timestamp of reference data in UTC.",
    )
    annotator: str | None = Field(
        None,
        description="Annotator, analyst, or automated process identifier.",
    )
    confidence_score: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Subjective or calculated confidence of the label (0.0 to 1.0).",
    )
    annotation_notes: str | None = Field(
        None,
        description="Contextual notes explaining the rationale for this label.",
    )
    geographic_evidence: str | None = Field(
        None,
        description="Geographic justification (imagery coordinates, facility).",
    )
    temporal_evidence: str | None = Field(
        None,
        description="Temporal justification (active date match, timestamp).",
    )

    @property
    def is_authoritative_ground_truth(self) -> bool:
        """Return True if this label is Tier A ground truth."""
        return (
            self.label_tier == LabelTier.TIER_A_AUTHORITATIVE
            and self.provenance_type == LabelProvenanceType.GROUND_TRUTH
        )

    @field_validator("confidence_score", mode="after")
    @classmethod
    def _validate_finite_confidence(cls, v: float | None) -> float | None:
        if v is not None and not math.isfinite(v):
            raise ValueError("confidence_score must be a finite float.")
        return v


class LabelQualityProfile(BaseDomainModel):
    """Aggregate quality and coverage summary for a reference label dataset."""

    source_name: str = Field(
        ...,
        min_length=1,
        description="Name of the evaluated reference source.",
    )
    coverage_count: int = Field(
        ...,
        ge=0,
        description="Total count of labeled instances.",
    )
    class_distribution: dict[str, int] = Field(
        default_factory=dict,
        description="Count of instances per class vocabulary entry.",
    )
    geographic_coverage: list[str] = Field(
        default_factory=list,
        description="Regions or bounding areas covered.",
    )
    temporal_start: UtcDatetime | None = Field(
        None,
        description="Earliest reference observation timestamp in UTC.",
    )
    temporal_end: UtcDatetime | None = Field(
        None,
        description="Latest reference observation timestamp in UTC.",
    )
    known_biases: list[str] = Field(
        default_factory=list,
        description="Documented sampling or observation biases in reference data.",
    )
    is_authoritative: bool = Field(
        default=False,
        description="Whether this source is approved as authoritative.",
    )


class ReferenceEvidence(BaseDomainModel):
    """Structured observation evidence from external reference databases."""

    evidence_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for the reference evidence record.",
    )
    source_name: str = Field(
        ...,
        min_length=1,
        description="Originating source catalog (e.g. GEM, WRI, VNF).",
    )
    source_role: SourceRole = Field(
        default=SourceRole.GROUND_TRUTH_EVIDENCE,
        description="Assigned role of this source in ML label construction.",
    )
    entity_id: str = Field(
        ...,
        min_length=1,
        description="Matched canonical entity ID (event_id or source_id).",
    )
    geometry: Coordinate = Field(
        ...,
        description="Centroid or match coordinates of reference evidence.",
    )
    observed_at: UtcDatetime | None = Field(
        None,
        description="Timestamp of reference observation or publication in UTC.",
    )
    claim_class: str = Field(
        ...,
        min_length=1,
        description="Phenomenon or category class asserted by this evidence.",
    )
    confidence_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score of this reference claim (0.0 to 1.0).",
    )
    tier: LabelTier = Field(
        default=LabelTier.TIER_B_STRONG_EVIDENCE,
        description="Reliability tier of the originating reference source.",
    )
    provenance_type: LabelProvenanceType = Field(
        default=LabelProvenanceType.REFERENCE_LABEL,
        description="Provenance classification of this evidence.",
    )
    evidence_payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Raw metadata dictionary from reference catalog.",
    )
    notes: str | None = Field(
        None,
        description="Contextual or scientific notes regarding this evidence.",
    )

    @field_validator("confidence_score", mode="after")
    @classmethod
    def _validate_finite_score(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("confidence_score must be finite.")
        return v


class LabelDecision(BaseDomainModel):
    """Auditable label decision for a target on a prediction entity."""

    decision_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for this label decision.",
    )
    target_id: str = Field(
        ...,
        min_length=1,
        description="Target definition identifier this label satisfies.",
    )
    entity_id: str = Field(
        ...,
        min_length=1,
        description="Entity ID (event_id or source_id).",
    )
    assigned_class: str = Field(
        ...,
        min_length=1,
        description="Assigned class vocabulary string.",
    )
    label_tier: LabelTier = Field(
        ...,
        description="Assigned quality and reliability tier.",
    )
    provenance_type: LabelProvenanceType = Field(
        ...,
        description="Assigned provenance classification.",
    )
    confidence_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Assigned confidence score for this label (0.0 to 1.0).",
    )
    contributing_evidence_ids: list[str] = Field(
        default_factory=list,
        description="List of reference evidence IDs used to construct this label.",
    )
    has_conflicting_evidence: bool = Field(
        default=False,
        description="Whether conflicting evidence was detected during construction.",
    )
    conflict_resolution_notes: str | None = Field(
        None,
        description="Notes detailing how conflicting evidence was resolved.",
    )
    is_train_eligible: bool = Field(
        default=True,
        description="Whether this sample is eligible for model training.",
    )
    is_eval_eligible: bool = Field(
        default=True,
        description="Whether this sample is eligible for model evaluation.",
    )
    exclusion_reason: ExclusionReason | None = Field(
        None,
        description="Reason for exclusion if not eligible.",
    )
    decision_timestamp: UtcDatetime = Field(
        ...,
        description="Timestamp when label decision was constructed in UTC.",
    )

    @field_validator("confidence_score", mode="after")
    @classmethod
    def _validate_finite_confidence(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("confidence_score must be finite.")
        return v


class FeatureDefinition(BaseDomainModel):
    """Metadata specification for an engineered ML feature."""

    feature_name: str = Field(
        ...,
        min_length=1,
        description="Canonical programmatic feature name.",
    )
    feature_type: FeatureType = Field(
        ...,
        description="Data type and physical representation of feature.",
    )
    feature_group: FeatureGroup = Field(
        default=FeatureGroup.THERMAL_CORE,
        description="Logical grouping of feature for ablation studies.",
    )
    eligibility_status: FeatureEligibilityStatus = Field(
        default=FeatureEligibilityStatus.APPROVED,
        description="Eligibility status (e.g. APPROVED, REJECTED, BLOCKED).",
    )
    source_entity: str = Field(
        ...,
        min_length=1,
        description="Upstream entity source (Detection, Event, Source, Context).",
    )
    derivation_description: str = Field(
        ...,
        min_length=1,
        description="Exact derivation algorithm or mathematical formula.",
    )
    physical_unit: str | None = Field(
        None,
        description="Physical unit (e.g. 'meters', 'MW', 'Kelvin', 'hours').",
    )
    availability_lag_seconds: float = Field(
        default=0.0,
        ge=0.0,
        description="Time delay after observation before feature is available.",
    )
    missingness_handling: FeatureMissingnessHandling = Field(
        ...,
        description="Semantics for handling missing observations.",
    )
    allowed_for_training: bool = Field(
        default=True,
        description="Whether feature is permitted in training datasets.",
    )
    is_model_input: bool = Field(
        default=True,
        description="Whether feature is a direct model input (False for metadata).",
    )
    spatial_semantics: str | None = Field(
        None,
        description="Spatial aggregation and alignment semantics.",
    )
    temporal_semantics: str | None = Field(
        None,
        description="Temporal aggregation and cutoff semantics.",
    )
    source_version: str | None = Field(
        None,
        description="Version or vintage of upstream source dataset.",
    )
    leakage_risk: LeakageRisk = Field(
        default=LeakageRisk.UNKNOWN,
        description="Assessment of leakage vulnerability.",
    )
    leakage_justification: str | None = Field(
        None,
        description="Reasoning explaining why feature is safe or flagging risk.",
    )
    version: str = Field(
        ...,
        min_length=1,
        description="Feature definition contract version.",
    )

    @field_validator("availability_lag_seconds", mode="after")
    @classmethod
    def _validate_finite_lag(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("availability_lag_seconds must be finite.")
        return v


class FeatureRecord(BaseDomainModel):
    """Canonical feature row representing an individual prediction sample."""

    entity_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier of prediction entity (e.g. event_id).",
    )
    prediction_unit: TargetUnit = Field(
        default=TargetUnit.EVENT,
        description="Unit of prediction for this feature row.",
    )
    as_of_time: UtcDatetime = Field(
        ...,
        description="Strict prediction cutoff timestamp in UTC.",
    )
    event_id: str | None = Field(
        None,
        description="Event ID for group-holdout splitting.",
    )
    source_id: str | None = Field(
        None,
        description="Persistent Source ID for group-holdout splitting.",
    )
    features: dict[str, float | int | str | bool | None] = Field(
        default_factory=dict,
        description="Dictionary of engineered feature name to value.",
    )
    missingness_flags: dict[str, bool] = Field(
        default_factory=dict,
        description="Explicit boolean missingness indicator for each feature.",
    )
    provenance: ProvenanceReference | None = Field(
        None,
        description="Lineage reference linking upstream observations/records.",
    )


class FeatureDataset(BaseDomainModel):
    """Complete, versioned, and content-addressable feature dataset."""

    manifest: "DatasetManifest" = Field(
        ...,
        description="Dataset manifest containing version, hash, and metadata.",
    )
    records: list[FeatureRecord] = Field(
        default_factory=list,
        description="List of feature records in deterministic order.",
    )
    feature_definitions: list[FeatureDefinition] = Field(
        default_factory=list,
        description="List of feature definitions present in this dataset.",
    )
    feature_groups: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Mapping of feature group name to list of feature names.",
    )
    summary_statistics: dict[str, Any] = Field(
        default_factory=dict,
        description="Quality and missingness diagnostics across feature records.",
    )


class DatasetManifest(BaseDomainModel):
    """Deterministic, content-addressable manifest for an ML dataset."""

    dataset_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for the dataset.",
    )
    dataset_version: str = Field(
        ...,
        min_length=1,
        description="Version string for this dataset build.",
    )
    target_id: str = Field(
        ...,
        min_length=1,
        description="Target definition ID.",
    )
    feature_set_version: str = Field(
        ...,
        min_length=1,
        description="Version of feature definitions used.",
    )
    label_set_version: str = Field(
        ...,
        min_length=1,
        description="Version of reference labels used.",
    )
    geographic_scope: str = Field(
        ...,
        min_length=1,
        description="Identifier of geographic study area bounding box.",
    )
    temporal_start: UtcDatetime = Field(
        ...,
        description="Earliest timestamp of included data in UTC.",
    )
    temporal_end: UtcDatetime = Field(
        ...,
        description="Latest timestamp of included data in UTC.",
    )
    split_strategy: SplitStrategy = Field(
        ...,
        description="Strategy used to partition dataset.",
    )
    record_count: int = Field(
        ...,
        ge=0,
        description="Total count of records/samples in dataset.",
    )
    sha256_hash: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="Deterministic SHA-256 hash of dataset content.",
    )
    created_at: UtcDatetime = Field(
        ...,
        description="Timestamp when dataset manifest was generated in UTC.",
    )
    provenance: ProvenanceReference | None = Field(
        None,
        description="Upstream pipeline and git commit lineage reference.",
    )

    @model_validator(mode="after")
    def _validate_temporal_span(self) -> "DatasetManifest":
        if self.temporal_start > self.temporal_end:
            raise ValueError("temporal_start cannot be after temporal_end.")
        return self


class SplitAssignment(BaseDomainModel):
    """Partition assignment for an individual entity record."""

    entity_id: str = Field(
        ...,
        min_length=1,
        description="Identifier of sample entity.",
    )
    partition: SplitPartition = Field(
        ...,
        description="Assigned dataset partition.",
    )
    event_id: str | None = Field(
        None,
        description="Associated event ID for group independence verification.",
    )
    source_id: str | None = Field(
        None,
        description="Associated persistent source ID for group independence.",
    )
    facility_id: str | None = Field(
        None,
        description="Associated facility ID for facility holdout splitting.",
    )
    spatial_block_id: str | None = Field(
        None,
        description="Associated geographic spatial block ID for spatial holdout.",
    )
    sensor_id: str | None = Field(
        None,
        description="Associated sensor or satellite platform ID.",
    )
    split_key: str = Field(
        ...,
        min_length=1,
        description="Grouped key or partition identifier used for assignment.",
    )
    assignment_reason: str | None = Field(
        None,
        description="Machine-readable justification for partition assignment.",
    )


class SplitIntegrityReport(BaseDomainModel):
    """Audit report verifying group, spatial, and temporal split independence."""

    is_valid: bool = Field(
        ...,
        description="True if split satisfies all leakage prevention invariants.",
    )
    split_strategy: SplitStrategy = Field(
        ...,
        description="Evaluated split strategy.",
    )
    train_count: int = Field(0, ge=0)
    validation_count: int = Field(0, ge=0)
    test_count: int = Field(0, ge=0)
    calibration_count: int = Field(0, ge=0)
    isolated_showcase_count: int = Field(0, ge=0)
    event_leakage_violations: list[str] = Field(
        default_factory=list,
        description="Event IDs appearing in multiple partitions.",
    )
    source_leakage_violations: list[str] = Field(
        default_factory=list,
        description="Source IDs appearing in both train and test partitions.",
    )
    facility_leakage_violations: list[str] = Field(
        default_factory=list,
        description="Facility IDs appearing in multiple partitions.",
    )
    spatial_leakage_violations: list[str] = Field(
        default_factory=list,
        description="Spatial block IDs appearing in multiple partitions.",
    )
    sensor_leakage_violations: list[str] = Field(
        default_factory=list,
        description="Sensors appearing in multiple conflicting partitions.",
    )
    temporal_inversion_violations: list[str] = Field(
        default_factory=list,
        description="Records violating temporal ordering (e.g. test before train).",
    )


class SplitManifest(BaseDomainModel):
    """Complete manifest of dataset partitions and split integrity audit."""

    split_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for this split allocation.",
    )
    dataset_id: str = Field(
        ...,
        min_length=1,
        description="Associated dataset identifier.",
    )
    dataset_version: str = Field(
        ...,
        min_length=1,
        description="Version string of the partitioned dataset.",
    )
    split_strategy: SplitStrategy = Field(
        ...,
        description="Strategy applied to partition the dataset.",
    )
    random_seed: int = Field(
        default=42,
        description="Random seed used for deterministic hashing.",
    )
    train_count: int = Field(
        default=0,
        ge=0,
        description="Count of samples in TRAIN partition.",
    )
    validation_count: int = Field(
        default=0,
        ge=0,
        description="Count of samples in VALIDATION partition.",
    )
    test_count: int = Field(
        default=0,
        ge=0,
        description="Count of samples in TEST partition.",
    )
    showcase_count: int = Field(
        default=0,
        ge=0,
        description="Count of samples isolated in SHOWCASE_ISOLATION.",
    )
    excluded_count: int = Field(
        default=0,
        ge=0,
        description="Count of excluded samples.",
    )
    assignments: list[SplitAssignment] = Field(
        default_factory=list,
        description="List of partition assignments for all entities.",
    )
    integrity_report: SplitIntegrityReport | None = Field(
        None,
        description="Integrity validation report for this split.",
    )
    created_at: UtcDatetime = Field(
        ...,
        description="Timestamp when split manifest was generated in UTC.",
    )


class LabeledFeatureRecord(BaseDomainModel):
    """Unified record combining feature representation and target label decisions."""

    entity_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier of prediction entity.",
    )
    feature_record: FeatureRecord = Field(
        ...,
        description="Underlying ML-002 feature record.",
    )
    labels: dict[str, LabelDecision] = Field(
        default_factory=dict,
        description="Dictionary mapping target_id to constructed LabelDecision.",
    )
    split_partition: SplitPartition = Field(
        default=SplitPartition.TRAIN,
        description="Assigned evaluation partition.",
    )
    row_status: DatasetRowStatus = Field(
        default=DatasetRowStatus.TRAIN_ELIGIBLE,
        description="Eligibility status for supervised learning.",
    )
    exclusion_reason: ExclusionReason | None = Field(
        None,
        description="Reason for exclusion if not eligible.",
    )


class SupervisedDataset(BaseDomainModel):
    """Complete supervised learning dataset with features, labels, and splits."""

    manifest: DatasetManifest = Field(
        ...,
        description="Dataset manifest containing version, hash, and metadata.",
    )
    split_manifest: SplitManifest = Field(
        ...,
        description="Split manifest documenting train/val/test partitions.",
    )
    records: list[LabeledFeatureRecord] = Field(
        default_factory=list,
        description="List of labeled feature records.",
    )
    target_definitions: list[TargetDefinition] = Field(
        default_factory=list,
        description="List of target specifications present in this dataset.",
    )
    feature_definitions: list[FeatureDefinition] = Field(
        default_factory=list,
        description="List of feature definitions present in this dataset.",
    )
    summary_statistics: dict[str, Any] = Field(
        default_factory=dict,
        description="Diagnostic statistics across classes, tiers, and splits.",
    )


class PerClassEvaluationMetrics(BaseDomainModel):
    """Detailed evaluation performance metrics for an individual class."""

    class_name: str = Field(
        ...,
        min_length=1,
        description="Class name from target vocabulary.",
    )
    true_positives: int = Field(0, ge=0)
    false_positives: int = Field(0, ge=0)
    false_negatives: int = Field(0, ge=0)
    true_negatives: int = Field(0, ge=0)
    support: int = Field(
        ...,
        ge=0,
        description="Total ground-truth count of this class in evaluation set.",
    )
    precision: float | None = Field(None, ge=0.0, le=1.0)
    recall: float | None = Field(None, ge=0.0, le=1.0)
    f1_score: float | None = Field(None, ge=0.0, le=1.0)

    @field_validator("precision", "recall", "f1_score", mode="after")
    @classmethod
    def _validate_finite_metrics(cls, v: float | None) -> float | None:
        if v is not None and not math.isfinite(v):
            raise ValueError("Metric value must be finite.")
        return v


class EvaluationReport(BaseDomainModel):
    """Comprehensive, human-auditable and machine-readable evaluation report."""

    evaluation_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for the evaluation execution.",
    )
    experiment_id: str = Field(
        ...,
        min_length=1,
        description="Experiment identifier.",
    )
    dataset_id: str = Field(
        ...,
        min_length=1,
        description="Dataset identifier evaluated.",
    )
    dataset_version: str = Field(
        ...,
        min_length=1,
        description="Dataset version evaluated.",
    )
    model_id: str = Field(
        ...,
        min_length=1,
        description="Model or baseline identifier evaluated.",
    )
    model_version: str = Field(
        ...,
        min_length=1,
        description="Model or baseline version.",
    )
    split_partition_evaluated: SplitPartition = Field(
        ...,
        description="Partition evaluated (TEST or VALIDATION).",
    )
    # Aggregate Metrics
    accuracy: float | None = Field(None, ge=0.0, le=1.0)
    balanced_accuracy: float | None = Field(None, ge=0.0, le=1.0)
    macro_precision: float | None = Field(None, ge=0.0, le=1.0)
    macro_recall: float | None = Field(None, ge=0.0, le=1.0)
    macro_f1: float | None = Field(None, ge=0.0, le=1.0)
    # Probabilistic Metrics
    brier_score: float | None = Field(None, ge=0.0, le=2.0)
    log_loss: float | None = Field(None, ge=0.0)
    roc_auc_macro: float | None = Field(None, ge=0.0, le=1.0)
    pr_auc_macro: float | None = Field(None, ge=0.0, le=1.0)
    # Detailed Breakdowns
    per_class_metrics: dict[str, PerClassEvaluationMetrics] = Field(
        default_factory=dict,
        description="Per-class metric breakdowns.",
    )
    confusion_matrix: list[list[int]] = Field(
        default_factory=list,
        description="Confusion matrix rows (ground truth) x columns (prediction).",
    )
    class_labels: list[str] = Field(
        default_factory=list,
        description="Class label ordering corresponding to confusion matrix.",
    )
    # Sample and Abstention Counts
    total_samples: int = Field(0, ge=0)
    evaluated_samples: int = Field(0, ge=0)
    abstained_samples: int = Field(0, ge=0)
    abstention_rate: float = Field(0.0, ge=0.0, le=1.0)
    created_at: UtcDatetime = Field(
        ...,
        description="Timestamp when report was generated in UTC.",
    )

    @field_validator(
        "accuracy",
        "balanced_accuracy",
        "macro_precision",
        "macro_recall",
        "macro_f1",
        "brier_score",
        "log_loss",
        "roc_auc_macro",
        "pr_auc_macro",
        "abstention_rate",
        mode="after",
    )
    @classmethod
    def _validate_finite_floats(cls, v: float | None) -> float | None:
        if v is not None and not math.isfinite(v):
            raise ValueError("Evaluation metric value must be finite.")
        return v


class CalibrationContract(BaseDomainModel):
    """Metadata specification for probability calibration."""

    calibration_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for calibration record.",
    )
    method: CalibrationMethod = Field(
        ...,
        description="Calibration algorithm applied.",
    )
    fitting_dataset_id: str = Field(
        ...,
        min_length=1,
        description="Dataset identifier used to fit calibration.",
    )
    fitting_split_partition: SplitPartition = Field(
        ...,
        description="Partition used for fitting (must be CALIBRATION or VALIDATION).",
    )
    is_fitted: bool = Field(
        default=False,
        description="Whether calibration model is fitted and ready.",
    )
    expected_calibration_error: float | None = Field(None, ge=0.0, le=1.0)
    maximum_calibration_error: float | None = Field(None, ge=0.0, le=1.0)
    brier_score_before: float | None = Field(None, ge=0.0, le=2.0)
    brier_score_after: float | None = Field(None, ge=0.0, le=2.0)

    @field_validator("fitting_split_partition", mode="after")
    @classmethod
    def _validate_not_test_partition(cls, v: SplitPartition) -> SplitPartition:
        if v == SplitPartition.TEST:
            raise ValueError(
                "Calibration fitting on the TEST partition is strictly prohibited."
            )
        return v


class AbstentionContract(BaseDomainModel):
    """Configuration and audit specification for model abstention."""

    abstention_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for abstention rule set.",
    )
    confidence_threshold: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Confidence score below which model must abstain.",
    )
    uncertainty_threshold: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Uncertainty metric above which model must abstain.",
    )
    require_evidence_completeness: bool = Field(
        default=False,
        description="Whether incomplete evidence triggers abstention.",
    )
    min_completeness_ratio: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Minimum completeness ratio required for prediction.",
    )
    allow_abstention: bool = Field(
        default=True,
        description="Whether abstention is enabled.",
    )
    coverage: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Fraction of samples not abstained in benchmark.",
    )
    selective_risk: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Error rate computed strictly on non-abstained samples.",
    )


class MLReadinessReport(BaseDomainModel):
    """Comprehensive readiness assessment report for Phase 4 ML."""

    report_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for readiness audit report.",
    )
    overall_status: ReadinessStatus = Field(
        ...,
        description="Overall readiness state (READY, NOT_READY, BLOCKED).",
    )
    evaluated_at: UtcDatetime = Field(
        ...,
        description="Timestamp when readiness audit was executed in UTC.",
    )
    target_ready: bool = Field(
        ...,
        description="Whether target and class taxonomy are approved.",
    )
    labels_ready: bool = Field(
        ...,
        description="Whether reference labels with Tier A/B provenance exist.",
    )
    features_ready: bool = Field(
        ...,
        description="Whether feature registry is populated and timing validated.",
    )
    leakage_audit_passed: bool = Field(
        ...,
        description="Whether features and splits are free of leakage risks.",
    )
    split_strategy_ready: bool = Field(
        ...,
        description="Whether split strategy is defined and group-safe.",
    )
    benchmark_defined: bool = Field(
        ...,
        description="Whether evaluation metrics and benchmark scope are frozen.",
    )
    reproducibility_ready: bool = Field(
        ...,
        description="Whether deterministic hashing and version tracking are active.",
    )
    open_questions: list[str] = Field(
        default_factory=list,
        description="Unresolved scientific questions blocking execution.",
    )
    blockers: list[str] = Field(
        default_factory=list,
        description="Specific actionable blockers preventing progression.",
    )
    readiness_details: dict[str, Any] = Field(
        default_factory=dict,
        description="Detailed diagnostics across evaluated subsystems.",
    )


class ModelMetadata(BaseDomainModel):
    """Metadata specification for a trained ML model artifact."""

    model_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for the trained model artifact.",
    )
    model_type: str = Field(
        ...,
        min_length=1,
        description="Type/architecture of model (e.g. MajorityClass, LogReg).",
    )
    model_version: str = Field(
        default="v1.0.0",
        min_length=1,
        description="Semantic version of the model build.",
    )
    model_family: str | None = Field(
        None,
        description="High-level model family (e.g. Baseline, Tree, Linear).",
    )
    target_id: str = Field(
        ...,
        min_length=1,
        description="Target definition ID this model predicts.",
    )
    target_version: str = Field(
        default="target_v1.0.0",
        description="Version of target definition.",
    )
    dataset_id: str = Field(
        default="ds_supervised_v1.0.0",
        description="Identifier of training dataset.",
    )
    dataset_version: str = Field(
        ...,
        min_length=1,
        description="Dataset version used for training.",
    )
    dataset_hash: str | None = Field(
        None,
        description="SHA-256 hash of training dataset.",
    )
    feature_set_version: str = Field(
        ...,
        min_length=1,
        description="Feature set version used.",
    )
    label_set_version: str = Field(
        ...,
        min_length=1,
        description="Label set version used.",
    )
    split_strategy: str | None = Field(
        None,
        description="Evaluation split strategy used.",
    )
    split_version: str = Field(
        ...,
        min_length=1,
        description="Split strategy/version used.",
    )
    random_seed: int = Field(
        default=42,
        description="Random seed used for deterministic execution.",
    )
    hyperparameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Model hyperparameters and configuration.",
    )
    training_timestamp: UtcDatetime = Field(
        ...,
        description="Timestamp when model was trained in UTC.",
    )
    train_record_count: int = Field(
        ...,
        ge=0,
        description="Number of samples in training partition.",
    )
    feature_names: list[str] = Field(
        default_factory=list,
        description="Ordered list of input feature names consumed by the model.",
    )
    feature_dimensionality: int = Field(
        default=0,
        ge=0,
        description="Total dimension of transformed feature input vector.",
    )
    validation_metrics: dict[str, Any] = Field(
        default_factory=dict,
        description="Validation partition evaluation summary.",
    )
    test_metrics: dict[str, Any] = Field(
        default_factory=dict,
        description="Held-out test partition evaluation summary.",
    )
    artifact_hash: str | None = Field(
        None,
        description="SHA-256 content hash of artifact model state.",
    )


class ModelArtifact(BaseDomainModel):
    """Container for serialized model state, preprocessing parameters, and metadata."""

    metadata: ModelMetadata = Field(
        ...,
        description="Provenance and training metadata.",
    )
    preprocessor_state: dict[str, Any] = Field(
        default_factory=dict,
        description="Fitted preprocessing parameters (fitted on TRAIN only).",
    )
    model_parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Fitted model weights, thresholds, or decision parameters.",
    )
    class_vocabulary: list[str] = Field(
        default_factory=list,
        description="Ordered list of predicted target classes.",
    )
    sha256_hash: str | None = Field(
        None,
        description="Deterministic content hash of serialized parameters and state.",
    )

    def compute_content_hash(self) -> str:
        """Compute deterministic SHA-256 hash of model parameters and preprocessor."""
        state = {
            "model_type": self.metadata.model_type,
            "target_id": self.metadata.target_id,
            "feature_set_version": self.metadata.feature_set_version,
            "preprocessor_state": self.preprocessor_state,
            "model_parameters": self.model_parameters,
            "class_vocabulary": self.class_vocabulary,
        }
        json_bytes = json.dumps(state, sort_keys=True, ensure_ascii=True).encode(
            "utf-8"
        )
        return hashlib.sha256(json_bytes).hexdigest()


class TrainingRunManifest(BaseDomainModel):
    """Immutable audit manifest capturing end-to-end training provenance."""

    run_id: str = Field(..., description="Unique training run execution ID.")
    model_id: str = Field(..., description="Target model identifier.")
    model_type: str = Field(..., description="Model architecture type.")
    model_version: str = Field(..., description="Model version string.")
    dataset_id: str = Field(..., description="Dataset identifier.")
    dataset_version: str = Field(..., description="Dataset version.")
    dataset_hash: str | None = Field(None, description="SHA-256 hash of dataset.")
    feature_set_version: str = Field(..., description="Feature set version.")
    label_set_version: str = Field(..., description="Label set version.")
    target_id: str = Field(..., description="Target specification ID.")
    target_version: str = Field(default="target_v1.0.0", description="Target version.")
    split_strategy: str = Field(..., description="Split strategy used.")
    random_seed: int = Field(default=42, description="Deterministic random seed.")
    hyperparameters: dict[str, Any] = Field(default_factory=dict)
    train_record_count: int = Field(..., ge=0)
    validation_record_count: int = Field(default=0, ge=0)
    test_record_count: int = Field(default=0, ge=0)
    validation_metrics: dict[str, Any] = Field(default_factory=dict)
    test_metrics: dict[str, Any] = Field(default_factory=dict)
    artifact_hash: str | None = Field(None, description="Content hash of artifact.")
    created_at: UtcDatetime = Field(..., description="Run timestamp in UTC.")


class InferencePredictionResult(BaseDomainModel):
    """Structured inference output returned by MLInferenceEngine."""

    entity_id: str = Field(..., description="Evaluated entity identifier.")
    target_id: str = Field(..., description="Target specification ID.")
    target_version: str = Field(..., description="Target version string.")
    model_id: str = Field(..., description="Model identifier used.")
    model_version: str = Field(..., description="Model version string.")
    model_type: str = Field(..., description="Model architecture used.")
    feature_set_version: str = Field(..., description="Feature set version.")
    predicted_class: str = Field(..., description="Predicted class label.")
    class_probabilities: dict[str, float] = Field(
        default_factory=dict, description="Class probability distribution."
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Highest class probability score."
    )
    is_abstained: bool = Field(
        default=False, description="True if prediction was abstained."
    )
    abstention_reason: str | None = Field(
        None, description="Reason code if prediction was abstained."
    )
    feature_count: int = Field(..., ge=0, description="Features evaluated.")
    inference_timestamp: UtcDatetime = Field(..., description="Prediction timestamp.")
    latency_ms: float = Field(default=0.0, ge=0.0, description="Latency in ms.")


class AblationExperimentResult(BaseDomainModel):
    """Result of a single model evaluation on a specific feature ablation subset."""

    experiment_id: str = Field(..., description="Unique ID of ablation experiment.")
    subset_name: str = Field(
        ..., description="Name of feature subset (e.g. THERMAL_ONLY)."
    )
    model_type: str = Field(..., description="Model architecture evaluated.")
    feature_names: list[str] = Field(
        default_factory=list, description="Included feature names."
    )
    feature_count: int = Field(..., description="Number of features in subset.")
    excluded_features: list[str] = Field(
        default_factory=list, description="Excluded feature names."
    )
    is_applicable: bool = Field(
        default=True,
        description="Whether experiment was semantically applicable for model.",
    )
    train_metrics: dict[str, Any] = Field(
        default_factory=dict, description="Training metrics."
    )
    validation_metrics: dict[str, Any] = Field(
        default_factory=dict, description="Validation metrics."
    )
    test_metrics: dict[str, Any] = Field(
        default_factory=dict, description="Test metrics."
    )
    generalization_gap_macro_f1: float | None = Field(
        default=None, description="Train F1 minus Test F1."
    )
    delta_vs_full_macro_f1: float | None = Field(
        default=None, description="Delta in Test Macro F1 vs FULL subset."
    )
    delta_vs_full_balanced_acc: float | None = Field(
        default=None, description="Delta in Test Balanced Acc vs FULL subset."
    )
    delta_vs_full_acc: float | None = Field(
        default=None, description="Delta in Test Acc vs FULL subset."
    )


class AblationStudyReport(BaseDomainModel):
    """Container for comprehensive multi-model, multi-subset feature ablation study."""

    study_id: str = Field(..., description="Unique ID of ablation study.")
    dataset_id: str = Field(..., description="Supervised dataset ID.")
    dataset_version: str = Field(..., description="Dataset version evaluated.")
    target_id: str = Field(..., description="Target specification ID.")
    created_at: UtcDatetime = Field(..., description="Timestamp of execution.")
    subsets_evaluated: list[str] = Field(
        default_factory=list, description="List of evaluated subset names."
    )
    models_evaluated: list[str] = Field(
        default_factory=list, description="List of evaluated model types."
    )
    results: list[AblationExperimentResult] = Field(
        default_factory=list, description="Per-experiment results."
    )
    shortcut_diagnostics: dict[str, Any] = Field(
        default_factory=dict,
        description="Contextual shortcut and thermal dependency deltas.",
    )


class GeneralizationExperimentResult(BaseDomainModel):
    """Result of evaluating a model on a specific holdout split strategy."""

    experiment_id: str = Field(
        ..., description="Unique ID for generalization experiment."
    )
    split_strategy: SplitStrategy = Field(..., description="Split strategy evaluated.")
    model_type: str = Field(..., description="Model architecture evaluated.")
    is_feasible: bool = Field(
        default=True,
        description="Whether split strategy was feasible with dataset.",
    )
    feasibility_notes: str | None = Field(
        default=None, description="Notes if strategy is infeasible."
    )
    train_record_count: int = Field(default=0, ge=0)
    val_record_count: int = Field(default=0, ge=0)
    test_record_count: int = Field(default=0, ge=0)
    train_metrics: dict[str, Any] = Field(default_factory=dict)
    validation_metrics: dict[str, Any] = Field(default_factory=dict)
    test_metrics: dict[str, Any] = Field(default_factory=dict)
    generalization_gap_macro_f1: float | None = Field(
        default=None,
        description=(
            "Macro F1 under GROUPED_EVENT_HOLDOUT minus Macro F1 under this holdout."
        ),
    )
    generalization_gap_balanced_acc: float | None = Field(
        default=None,
        description=(
            "Balanced Accuracy under GROUPED_EVENT_HOLDOUT minus Balanced Acc"
            " under this holdout."
        ),
    )


class GeneralizationStudyReport(BaseDomainModel):
    """Container for comprehensive multi-strategy generalization benchmark."""

    study_id: str = Field(..., description="Unique ID of generalization study.")
    dataset_id: str = Field(..., description="Supervised dataset identifier.")
    dataset_version: str = Field(..., description="Dataset version.")
    target_id: str = Field(..., description="Target specification.")
    created_at: UtcDatetime = Field(..., description="Timestamp of execution.")
    strategies_evaluated: list[SplitStrategy] = Field(default_factory=list)
    models_evaluated: list[str] = Field(default_factory=list)
    results: list[GeneralizationExperimentResult] = Field(default_factory=list)
    generalization_gaps: dict[str, dict[str, float | None]] = Field(
        default_factory=dict,
        description=(
            "Mapping of model_type -> strategy -> macro_f1 gap vs standard event"
            " holdout."
        ),
    )
    shortcut_resilience: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Analysis of performance under spatial holdout with full vs"
            " thermal-only features."
        ),
    )
