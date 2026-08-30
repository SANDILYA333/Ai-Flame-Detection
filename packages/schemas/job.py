"""Canonical domain models and enumerations for jobs and pipeline runs (WORK-001).

Defines authoritative job state representations, pipeline lineage metadata,
and execution status models according to Migrations 025 and 026 in the
canonical execution plan.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import Field

from packages.schemas.common import BaseDomainModel, UtcDatetime


class JobState(StrEnum):
    """Authoritative lifecycle states for background and pipeline jobs.

    Allowed states per Section 3.26 and Section 21 of the canonical plan.
    """

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    CANCELLED = "CANCELLED"


class JobType(StrEnum):
    """Standard job categories within the SIH26162 analytical architecture."""

    INGEST = "ingest"
    ENRICH = "enrich"
    CLASSIFY = "classify"
    EVENT_CONSTRUCTION = "event_construction"
    E2E_PIPELINE = "e2e_pipeline"
    FEASIBILITY = "feasibility"
    EVALUATION = "evaluation"
    CUSTOM = "custom"


class PipelineRunStatus(StrEnum):
    """Execution status for multi-stage analytical pipeline runs."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    BLOCKED = "BLOCKED"


class JobRecord(BaseDomainModel):
    """Authoritative representation of a discrete processing job (Migration 026).

    Guarantees state machine auditability, idempotency, retry counting,
    and safe error reporting.
    """

    job_id: str = Field(
        default_factory=lambda: f"job_{uuid4().hex[:12]}",
        description="Unique authoritative job identifier",
    )
    job_type: str = Field(
        ...,
        min_length=1,
        description="Job type descriptor or canonical JobType string",
    )
    pipeline_run_id: str | None = Field(
        None,
        description="Optional parent pipeline run ID for lineage tracking",
    )
    idempotency_key: str | None = Field(
        None,
        description="Optional idempotency key preventing duplicate executions",
    )
    state: JobState = Field(
        default=JobState.QUEUED,
        description="Current authoritative job state",
    )
    attempt_count: int = Field(
        default=0,
        ge=0,
        description="Number of execution attempts performed",
    )
    max_attempts: int = Field(
        default=3,
        ge=1,
        description="Maximum allowed execution attempts before terminal failure",
    )
    created_at: UtcDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when job record was created",
    )
    started_at: UtcDatetime | None = Field(
        None,
        description="UTC timestamp when job execution began",
    )
    completed_at: UtcDatetime | None = Field(
        None,
        description="UTC timestamp when job reached a terminal state",
    )
    error_code: str | None = Field(
        None,
        description="Structured error code if job failed or was blocked",
    )
    error_message_safe: str | None = Field(
        None,
        description="Sanitized user-facing error message free of secrets and paths",
    )
    input_reference: dict[str, Any] | None = Field(
        None,
        description="Serialized input parameters or reference snapshot pointers",
    )
    result_summary: dict[str, Any] | None = Field(
        None,
        description="High-level execution summary or output pointers upon success",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Operational metadata and lineage attributes",
    )


class PipelineRun(BaseDomainModel):
    """Lineage and reproducibility record for multi-stage pipeline executions."""

    pipeline_run_id: str = Field(
        default_factory=lambda: f"run_{uuid4().hex[:12]}",
        description="Unique authoritative pipeline run identifier",
    )
    pipeline_name: str = Field(
        ...,
        min_length=1,
        description="Identifier name of the executed analytical pipeline",
    )
    pipeline_version: str = Field(
        default="v1.0.0",
        min_length=1,
        description="Version string of the pipeline definition",
    )
    scientific_contract_id: str | None = Field(
        None,
        description="Active scientific configuration contract ID",
    )
    input_snapshot_ids: list[str] = Field(
        default_factory=list,
        description="List of input source snapshot IDs consumed by the run",
    )
    dataset_version_id: str | None = Field(
        None,
        description="Dataset version produced or consumed",
    )
    model_version_id: str | None = Field(
        None,
        description="ML model version utilized for inference/evaluation",
    )
    started_at: UtcDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when pipeline run started",
    )
    completed_at: UtcDatetime | None = Field(
        None,
        description="UTC timestamp when pipeline run finished",
    )
    status: PipelineRunStatus = Field(
        default=PipelineRunStatus.QUEUED,
        description="Overall pipeline execution status",
    )
    code_version: str | None = Field(
        None,
        description="Git commit hash or build version",
    )
    configuration_hash: str | None = Field(
        None,
        description="Cryptographic SHA-256 hash of active configuration parameters",
    )
    output_manifest_hash: str | None = Field(
        None,
        description="Cryptographic SHA-256 hash of generated output artifacts",
    )
    error_code: str | None = Field(
        None,
        description="Error code if pipeline execution encountered an error",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional execution metadata and stage timing",
    )
