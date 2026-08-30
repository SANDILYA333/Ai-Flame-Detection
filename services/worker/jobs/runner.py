"""Synchronous Job Runner & Execution Engine (WORK-001).

Implements the synchronous execution of background and analytical pipeline jobs,
enforcing authoritative state transitions, idempotency, failure semantics, and
secret-safe error reporting.
"""

from datetime import UTC, datetime
from typing import Any

from packages.errors import (
    AppError,
    ErrorCode,
    JobCancelledError,
    MissingConfigurationError,
)
from packages.logging import get_logger, log_with_context
from packages.logging.sanitizer import sanitize_log_dict, sanitize_log_value
from packages.schemas.job import (
    JobRecord,
    JobState,
    PipelineRun,
    PipelineRunStatus,
)
from services.worker.jobs.context import JobContext
from services.worker.jobs.handler import JobRegistry
from services.worker.jobs.repository import InMemoryJobRepository, JobRepositoryProtocol
from services.worker.jobs.state_machine import JobStateMachine

logger = get_logger("services.worker.jobs.runner")


class SyncJobRunner:
    """Synchronous job execution engine with state machine and idempotency."""

    def __init__(
        self,
        repository: JobRepositoryProtocol | None = None,
        registry: JobRegistry | None = None,
    ) -> None:
        self.repository = repository or InMemoryJobRepository()
        self.registry = registry or JobRegistry()

    def create_job(
        self,
        job_type: str,
        input_reference: dict[str, Any] | None = None,
        *,
        idempotency_key: str | None = None,
        pipeline_run_id: str | None = None,
        max_attempts: int = 3,
        metadata: dict[str, Any] | None = None,
    ) -> JobRecord:
        """Create and persist a new job or return existing job if key matches.

        Args:
            job_type: Registered job type string.
            input_reference: Optional input parameters or data pointers.
            idempotency_key: Optional key to enforce idempotent deduplication.
            pipeline_run_id: Optional parent pipeline run ID.
            max_attempts: Maximum execution attempts before terminal failure.
            metadata: Optional execution metadata.

        Returns:
            Authoritative JobRecord.
        """
        # 1. Idempotency deduplication check
        if idempotency_key:
            existing_job = self.repository.get_job_by_idempotency_key(idempotency_key)
            if existing_job is not None:
                log_with_context(
                    logger,
                    20,  # INFO
                    f"Idempotency hit for key '{idempotency_key}'. "
                    f"Returning existing job '{existing_job.job_id}'.",
                    context={
                        "idempotency_key": idempotency_key,
                        "job_id": existing_job.job_id,
                        "state": existing_job.state.value,
                    },
                )
                return existing_job

        # 2. Construct sanitized new job record
        sanitized_input = (
            sanitize_log_dict(input_reference) if input_reference is not None else None
        )
        sanitized_meta = sanitize_log_dict(metadata or {})

        new_job = JobRecord(
            job_type=job_type,
            pipeline_run_id=pipeline_run_id,
            idempotency_key=idempotency_key,
            state=JobState.QUEUED,
            attempt_count=0,
            max_attempts=max_attempts,
            input_reference=sanitized_input,
            metadata=sanitized_meta,
        )

        self.repository.save_job(new_job)
        log_with_context(
            logger,
            20,  # INFO
            f"Created job '{new_job.job_id}' of type '{job_type}' [QUEUED].",
            context={
                "job_id": new_job.job_id,
                "job_type": job_type,
                "pipeline_run_id": pipeline_run_id,
                "idempotency_key": idempotency_key,
            },
        )
        return new_job

    def run_job(self, job_id_or_record: str | JobRecord) -> JobRecord:
        """Execute a job synchronously through its full state machine lifecycle.

        Args:
            job_id_or_record: Either the string job_id or a JobRecord.

        Returns:
            Final updated JobRecord.
        """
        job_id = (
            job_id_or_record
            if isinstance(job_id_or_record, str)
            else job_id_or_record.job_id
        )
        job = self.repository.get_job(job_id)

        if job is None:
            raise KeyError(f"Job with ID '{job_id}' not found in repository.")

        # If already terminal or cancelled, return as-is
        if JobStateMachine.is_terminal_state(job.state):
            return job

        # Check if cancellation was requested while queued
        if job.state == JobState.CANCEL_REQUESTED:
            cancelled_job = JobStateMachine.transition(
                job,
                JobState.CANCELLED,
                error_code=ErrorCode.JOB_CANCELLED_ERROR.value,
                error_message_safe="Job cancelled before execution started.",
            )
            self.repository.save_job(cancelled_job)
            return cancelled_job

        # If retrying a failed or unblocking a blocked job, transition to QUEUED first
        if (
            job.state in (JobState.FAILED, JobState.BLOCKED)
            and job.attempt_count < job.max_attempts
        ):
            job = JobStateMachine.transition(job, JobState.QUEUED)
            self.repository.save_job(job)

        # Resolve handler
        handler = self.registry.get(job.job_type)

        # Transition QUEUED -> RUNNING
        running_job = JobStateMachine.transition(job, JobState.RUNNING)
        self.repository.save_job(running_job)

        # Build context
        ctx = JobContext(
            job_id=running_job.job_id,
            job_type=running_job.job_type,
            attempt_count=running_job.attempt_count,
            pipeline_run_id=running_job.pipeline_run_id,
            cancellation_checker=lambda: self._is_cancelled_or_requested(
                running_job.job_id
            ),
            metadata=running_job.metadata,
        )

        try:
            # Execute handler synchronously
            result = handler.execute(ctx, running_job.input_reference)

            # Check if cancellation was requested during execution
            if ctx.is_cancellation_requested():
                cancelled_job = JobStateMachine.transition(
                    running_job,
                    JobState.CANCELLED,
                    error_code=ErrorCode.JOB_CANCELLED_ERROR.value,
                    error_message_safe="Job execution cancelled upon request.",
                )
                self.repository.save_job(cancelled_job)
                return cancelled_job

            # Format summary
            summary: dict[str, Any]
            if isinstance(result, dict):
                summary = result
            elif hasattr(result, "model_dump"):
                dumped = result.model_dump(mode="json")
                summary = dumped if isinstance(dumped, dict) else {"result": dumped}
            else:
                summary = {"result": str(result)}

            # Transition RUNNING -> SUCCEEDED
            succeeded_job = JobStateMachine.transition(
                running_job,
                JobState.SUCCEEDED,
                result_summary=summary,
            )
            self.repository.save_job(succeeded_job)
            log_with_context(
                logger,
                20,  # INFO
                f"Job '{succeeded_job.job_id}' completed successfully [SUCCEEDED].",
                context={
                    "job_id": succeeded_job.job_id,
                    "job_type": succeeded_job.job_type,
                    "duration_seconds": (
                        (
                            succeeded_job.completed_at - succeeded_job.started_at
                        ).total_seconds()
                        if succeeded_job.completed_at and succeeded_job.started_at
                        else None
                    ),
                },
            )
            return succeeded_job

        except MissingConfigurationError as e:
            # Scientific missing configuration triggers BLOCKED state per Section 21
            safe_msg = sanitize_log_value(str(e))
            blocked_job = JobStateMachine.transition(
                running_job,
                JobState.BLOCKED,
                error_code=ErrorCode.MISSING_CONFIGURATION.value,
                error_message_safe=safe_msg,
            )
            self.repository.save_job(blocked_job)
            log_with_context(
                logger,
                30,  # WARNING
                f"Job '{blocked_job.job_id}' is BLOCKED on missing config: {safe_msg}",
                context={
                    "job_id": blocked_job.job_id,
                    "error_code": "MISSING_CONFIGURATION",
                },
            )
            return blocked_job

        except JobCancelledError as e:
            safe_msg = sanitize_log_value(str(e))
            cancelled_job = JobStateMachine.transition(
                running_job,
                JobState.CANCELLED,
                error_code=ErrorCode.JOB_CANCELLED_ERROR.value,
                error_message_safe=safe_msg,
            )
            self.repository.save_job(cancelled_job)
            return cancelled_job

        except Exception as e:
            error_code_val = (
                getattr(e, "code", ErrorCode.JOB_EXECUTION_ERROR).value
                if isinstance(e, AppError)
                else ErrorCode.JOB_EXECUTION_ERROR.value
            )
            safe_msg = sanitize_log_value(str(e))

            failed_job = JobStateMachine.transition(
                running_job,
                JobState.FAILED,
                error_code=error_code_val,
                error_message_safe=safe_msg,
            )
            self.repository.save_job(failed_job)
            log_with_context(
                logger,
                40,  # ERROR
                f"Job '{failed_job.job_id}' failed execution: {safe_msg}",
                context={
                    "job_id": failed_job.job_id,
                    "job_type": failed_job.job_type,
                    "error_code": error_code_val,
                },
            )
            return failed_job

    def request_cancel(self, job_id: str) -> JobRecord:
        """Request cancellation of an active or queued job."""
        job = self.repository.get_job(job_id)
        if job is None:
            raise KeyError(f"Job with ID '{job_id}' not found.")

        if job.state == JobState.QUEUED:
            cancelled_job = JobStateMachine.transition(
                job,
                JobState.CANCELLED,
                error_code=ErrorCode.JOB_CANCELLED_ERROR.value,
                error_message_safe="Cancelled while queued.",
            )
            self.repository.save_job(cancelled_job)
            return cancelled_job

        if job.state == JobState.RUNNING:
            cancel_req_job = JobStateMachine.transition(
                job,
                JobState.CANCEL_REQUESTED,
            )
            self.repository.save_job(cancel_req_job)
            return cancel_req_job

        return job

    def get_job(self, job_id: str) -> JobRecord | None:
        """Retrieve job record by ID."""
        return self.repository.get_job(job_id)

    def create_pipeline_run(
        self,
        pipeline_name: str,
        pipeline_version: str = "v1.0.0",
        *,
        scientific_contract_id: str | None = None,
        input_snapshot_ids: list[str] | None = None,
        dataset_version_id: str | None = None,
        model_version_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PipelineRun:
        """Create and persist a new PipelineRun record for multi-stage execution."""
        run = PipelineRun(
            pipeline_name=pipeline_name,
            pipeline_version=pipeline_version,
            scientific_contract_id=scientific_contract_id,
            input_snapshot_ids=input_snapshot_ids or [],
            dataset_version_id=dataset_version_id,
            model_version_id=model_version_id,
            status=PipelineRunStatus.RUNNING,
            metadata=sanitize_log_dict(metadata or {}),
        )
        self.repository.save_pipeline_run(run)
        return run

    def finish_pipeline_run(
        self,
        pipeline_run_id: str,
        status: PipelineRunStatus,
        *,
        output_manifest_hash: str | None = None,
        error_code: str | None = None,
    ) -> PipelineRun:
        """Update and finalize a PipelineRun record."""
        run = self.repository.get_pipeline_run(pipeline_run_id)
        if run is None:
            raise KeyError(f"Pipeline run '{pipeline_run_id}' not found.")

        updated_run = PipelineRun(
            pipeline_run_id=run.pipeline_run_id,
            pipeline_name=run.pipeline_name,
            pipeline_version=run.pipeline_version,
            scientific_contract_id=run.scientific_contract_id,
            input_snapshot_ids=run.input_snapshot_ids,
            dataset_version_id=run.dataset_version_id,
            model_version_id=run.model_version_id,
            started_at=run.started_at,
            completed_at=datetime.now(UTC),
            status=status,
            code_version=run.code_version,
            configuration_hash=run.configuration_hash,
            output_manifest_hash=output_manifest_hash or run.output_manifest_hash,
            error_code=error_code or run.error_code,
            metadata=run.metadata,
        )
        self.repository.save_pipeline_run(updated_run)
        return updated_run

    def _is_cancelled_or_requested(self, job_id: str) -> bool:
        """Helper to inspect current database/repository state for cancellation."""
        current = self.repository.get_job(job_id)
        if current is not None:
            return current.state in (
                JobState.CANCEL_REQUESTED,
                JobState.CANCELLED,
            )
        return False
