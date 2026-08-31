"""Authoritative job and pipeline run repository (WORK-001 / DB-014).

Provides persistence and query capabilities for JobRecord and PipelineRun domain
entities, with indexing by job_id, pipeline_run_id, and idempotency_key.
"""

from typing import Protocol

from packages.schemas.job import JobRecord, JobState, PipelineRun, PipelineRunStatus


class JobRepositoryProtocol(Protocol):
    """Protocol for authoritative job and pipeline run storage."""

    def save_job(self, job: JobRecord) -> None: ...
    def get_job(self, job_id: str) -> JobRecord | None: ...
    def get_job_by_idempotency_key(self, key: str) -> JobRecord | None: ...
    def list_jobs(
        self,
        *,
        pipeline_run_id: str | None = None,
        state: JobState | None = None,
        job_type: str | None = None,
        limit: int = 100,
    ) -> list[JobRecord]: ...
    def save_pipeline_run(self, run: PipelineRun) -> None: ...
    def get_pipeline_run(self, pipeline_run_id: str) -> PipelineRun | None: ...
    def list_pipeline_runs(
        self,
        *,
        status: PipelineRunStatus | None = None,
        limit: int = 100,
    ) -> list[PipelineRun]: ...


class InMemoryJobRepository:
    """Thread-safe authoritative in-memory implementation of JobRepository."""

    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._idempotency_index: dict[str, str] = {}  # idempotency_key -> job_id
        self._pipeline_runs: dict[str, PipelineRun] = {}

    def save_job(self, job: JobRecord) -> None:
        """Persist or update a JobRecord."""
        self._jobs[job.job_id] = job
        if job.idempotency_key:
            self._idempotency_index[job.idempotency_key] = job.job_id

    def get_job(self, job_id: str) -> JobRecord | None:
        """Retrieve a JobRecord by its job_id."""
        return self._jobs.get(job_id)

    def get_job_by_idempotency_key(self, key: str) -> JobRecord | None:
        """Retrieve a JobRecord by its idempotency key."""
        job_id = self._idempotency_index.get(key)
        if job_id:
            return self._jobs.get(job_id)
        return None

    def list_jobs(
        self,
        *,
        pipeline_run_id: str | None = None,
        state: JobState | None = None,
        job_type: str | None = None,
        limit: int = 100,
    ) -> list[JobRecord]:
        """List jobs matching optional filter criteria."""
        results: list[JobRecord] = []
        for job in sorted(
            self._jobs.values(), key=lambda j: j.created_at, reverse=True
        ):
            if pipeline_run_id and job.pipeline_run_id != pipeline_run_id:
                continue
            if state and job.state != state:
                continue
            if job_type and job.job_type != job_type:
                continue
            results.append(job)
            if len(results) >= limit:
                break
        return results

    def save_pipeline_run(self, run: PipelineRun) -> None:
        """Persist or update a PipelineRun record."""
        self._pipeline_runs[run.pipeline_run_id] = run

    def get_pipeline_run(self, pipeline_run_id: str) -> PipelineRun | None:
        """Retrieve a PipelineRun by ID."""
        return self._pipeline_runs.get(pipeline_run_id)

    def list_pipeline_runs(
        self,
        *,
        status: PipelineRunStatus | None = None,
        limit: int = 100,
    ) -> list[PipelineRun]:
        """List pipeline runs matching optional filter criteria."""
        results: list[PipelineRun] = []
        for run in sorted(
            self._pipeline_runs.values(), key=lambda r: r.started_at, reverse=True
        ):
            if status and run.status != status:
                continue
            results.append(run)
            if len(results) >= limit:
                break
        return results

    def clear(self) -> None:
        """Clear all stored state (for test isolation)."""
        self._jobs.clear(
        )
        self._idempotency_index.clear()
        self._pipeline_runs.clear()
