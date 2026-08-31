"""Worker Runner & Background Execution Engine (WORK-003 / Section 21).

Coordinates continuous consumption from the transient queue (JobQueueProtocol),
execution via SyncJobRunner, and authoritative state persistence in the database
(JobRepositoryProtocol).

CRITICAL ARCHITECTURAL INVARIANTS:
1. The database repository remains the authoritative single source of truth.
2. Redis / transient queue is coordination only.
3. Retries respect strict bounds and idempotency guarantees.
4. Non-retryable or exhausted failures route to the dead-letter queue.
5. Missing scientific configuration triggers BLOCKED state and acknowledges queue
   to prevent transient spin-loops.
"""

import logging
import threading
import time
from datetime import UTC, datetime
from uuid import uuid4

from pydantic import Field

from packages.logging import get_logger, log_with_context
from packages.logging.sanitizer import sanitize_log_value
from packages.schemas.common import BaseDomainModel, UtcDatetime
from packages.schemas.job import JobRecord, JobState
from services.worker.jobs.handler import JobRegistry
from services.worker.jobs.handlers import (
    ContextEnrichJobHandler,
    EndToEndPipelineJobHandler,
    EventConstructJobHandler,
    FIRMSIngestJobHandler,
    IntelligenceClassifyJobHandler,
)
from services.worker.jobs.queue import (
    InMemoryJobQueue,
    JobQueueMessage,
    JobQueueProtocol,
)
from services.worker.jobs.repository import (
    InMemoryJobRepository,
    JobRepositoryProtocol,
)
from services.worker.jobs.runner import SyncJobRunner
from services.worker.jobs.state_machine import JobStateMachine

logger = get_logger("services.worker.jobs.worker")


class WorkerStatus(BaseDomainModel):
    """Observable runtime execution metrics for a WorkerRunner."""

    worker_id: str = Field(
        ...,
        description="Unique identifier of the worker instance",
    )
    is_running: bool = Field(
        default=False,
        description="Whether the worker loop is currently active",
    )
    processed_count: int = Field(
        default=0,
        ge=0,
        description="Total queue messages processed",
    )
    succeeded_count: int = Field(
        default=0,
        ge=0,
        description="Total jobs successfully executed",
    )
    failed_count: int = Field(
        default=0,
        ge=0,
        description="Total jobs that failed execution",
    )
    blocked_count: int = Field(
        default=0,
        ge=0,
        description="Total jobs blocked on missing configuration",
    )
    dead_lettered_count: int = Field(
        default=0,
        ge=0,
        description="Total messages routed to dead-letter queue",
    )
    skipped_count: int = Field(
        default=0,
        ge=0,
        description="Total duplicate/terminal messages skipped",
    )
    last_processed_at: UtcDatetime | None = Field(
        default=None,
        description="UTC timestamp of the most recent processed job",
    )


class WorkerRunner:
    """Continuous background worker runner connecting queue and domain execution."""

    def __init__(
        self,
        queue: JobQueueProtocol | None = None,
        repository: JobRepositoryProtocol | None = None,
        runner: SyncJobRunner | None = None,
        worker_id: str | None = None,
    ) -> None:
        self.worker_id = worker_id or f"worker_{uuid4().hex[:8]}"
        self.queue = queue or InMemoryJobQueue()
        self.repository = repository or InMemoryJobRepository()
        self.runner = runner or SyncJobRunner(repository=self.repository)

        self._stop_requested = threading.Event()
        self._worker_thread: threading.Thread | None = None
        self._lock = threading.RLock()

        # Metrics counters
        self._processed_count = 0
        self._succeeded_count = 0
        self._failed_count = 0
        self._blocked_count = 0
        self._dead_lettered_count = 0
        self._skipped_count = 0
        self._last_processed_at: datetime | None = None

    @property
    def is_running(self) -> bool:
        """Check whether the background worker thread is active."""
        return self._worker_thread is not None and self._worker_thread.is_alive()

    def process_one(self) -> JobRecord | None:
        """Process a single message from the transient queue.

        Coordinates between transient queue message and authoritative DB record.
        Returns the updated JobRecord, or None if queue was empty or message orphaned.
        """
        message: JobQueueMessage | None = self.queue.dequeue()
        if message is None:
            return None

        with self._lock:
            self._processed_count += 1
            self._last_processed_at = datetime.now(UTC)

        job_id = message.job_id
        db_job = self.repository.get_job(job_id)

        # 1. Handle orphaned message (not found in authoritative DB repository)
        if db_job is None:
            log_with_context(
                logger,
                logging.WARNING,
                f"Worker '{self.worker_id}' found orphaned message "
                f"'{message.message_id}' referencing unknown job '{job_id}'. "
                "Dead-lettering message.",
                context={"job_id": job_id, "message_id": message.message_id},
            )
            self.queue.reject(
                message.message_id,
                requeue=False,
                reason="JobRecord not found in authoritative database",
            )
            with self._lock:
                self._dead_lettered_count += 1
            return None

        # 2. Idempotency check: Already completed or cancelled in DB
        if db_job.state in (JobState.SUCCEEDED, JobState.CANCELLED):
            log_with_context(
                logger,
                logging.INFO,
                f"Worker '{self.worker_id}' skipped already terminal job '{job_id}' "
                f"in state '{db_job.state.value}'.",
                context={"job_id": job_id, "state": db_job.state.value},
            )
            self.queue.acknowledge(message.message_id)
            with self._lock:
                self._skipped_count += 1
            return db_job

        # 3. Handle pre-execution cancellation request
        if db_job.state == JobState.CANCEL_REQUESTED:
            cancelled_job = JobStateMachine.transition(
                db_job,
                JobState.CANCELLED,
                error_message_safe="Execution cancelled before worker launch",
            )
            self.repository.save_job(cancelled_job)
            self.queue.acknowledge(message.message_id)
            log_with_context(
                logger,
                logging.INFO,
                f"Worker '{self.worker_id}' finalized cancellation for job '{job_id}'.",
                context={"job_id": job_id},
            )
            with self._lock:
                self._skipped_count += 1
            return cancelled_job

        # 4. Execute the job via SyncJobRunner
        log_with_context(
            logger,
            logging.INFO,
            f"Worker '{self.worker_id}' launching job '{job_id}' "
            f"(type: {db_job.job_type}).",
            context={
                "job_id": job_id,
                "job_type": db_job.job_type,
                "attempt": message.attempt_count,
            },
        )

        result_job = self.runner.run_job(job_id)

        # 5. Evaluate execution result against queue delivery contract
        if result_job.state == JobState.SUCCEEDED:
            self.queue.acknowledge(message.message_id)
            with self._lock:
                self._succeeded_count += 1

        elif result_job.state == JobState.BLOCKED:
            # Missing configuration is authoritative: acknowledge queue
            # to prevent transient worker spin-loops
            self.queue.acknowledge(message.message_id)
            with self._lock:
                self._blocked_count += 1

        elif result_job.state == JobState.CANCELLED:
            self.queue.acknowledge(message.message_id)
            with self._lock:
                self._skipped_count += 1

        elif result_job.state == JobState.FAILED:
            with self._lock:
                self._failed_count += 1

            safe_reason = sanitize_log_value(
                result_job.error_message_safe or "Job execution failed"
            )

            # Retryable check: respect retry bounds
            if (
                result_job.attempt_count < result_job.max_attempts
                and message.attempt_count < message.max_retries
            ):
                log_with_context(
                    logger,
                    logging.WARNING,
                    f"Worker '{self.worker_id}' requeuing failed job '{job_id}' "
                    f"(attempt {result_job.attempt_count}/{result_job.max_attempts}).",
                    context={"job_id": job_id, "reason": safe_reason},
                )
                requeued_job = JobStateMachine.transition(
                    result_job,
                    JobState.QUEUED,
                    error_message_safe=safe_reason,
                )
                self.repository.save_job(requeued_job)
                self.queue.reject(
                    message.message_id,
                    requeue=True,
                    reason=safe_reason,
                )
                return requeued_job
            else:
                log_with_context(
                    logger,
                    logging.ERROR,
                    f"Worker '{self.worker_id}' dead-lettering job '{job_id}' "
                    f"(attempts exhausted: "
                    f"{result_job.attempt_count}/{result_job.max_attempts}).",
                    context={"job_id": job_id, "reason": safe_reason},
                )
                self.queue.reject(
                    message.message_id,
                    requeue=False,
                    reason=safe_reason,
                )
                with self._lock:
                    self._dead_lettered_count += 1

        return result_job

    def run_until_empty(self, max_jobs: int = 100) -> list[JobRecord]:
        """Drain the transient queue, executing jobs until empty or limit reached.

        Useful for deterministic testing, batch execution, and offline CLI runs.
        """
        results: list[JobRecord] = []
        for _ in range(max_jobs):
            res = self.process_one()
            if res is None:
                break
            results.append(res)
        return results

    def run_forever(self, poll_interval_seconds: float = 0.1) -> None:
        """Run the worker loop continuously until stop() is invoked."""
        self._stop_requested.clear()
        log_with_context(
            logger,
            logging.INFO,
            f"Worker '{self.worker_id}' starting continuous execution loop.",
        )

        while not self._stop_requested.is_set():
            processed = self.process_one()
            if processed is None:
                time.sleep(poll_interval_seconds)

        log_with_context(
            logger,
            logging.INFO,
            f"Worker '{self.worker_id}' execution loop stopped.",
        )

    def start(self, poll_interval_seconds: float = 0.1) -> None:
        """Start the worker runner in a background daemon thread."""
        with self._lock:
            if self.is_running:
                return

            self._stop_requested.clear()
            self._worker_thread = threading.Thread(
                target=self.run_forever,
                args=(poll_interval_seconds,),
                name=f"Thread-{self.worker_id}",
                daemon=True,
            )
            self._worker_thread.start()

    def stop(self, timeout_seconds: float = 2.0) -> None:
        """Signal the worker thread to stop and wait for completion."""
        with self._lock:
            self._stop_requested.set()
            if self._worker_thread is not None and self._worker_thread.is_alive():
                self._worker_thread.join(timeout=timeout_seconds)
                self._worker_thread = None

    def get_status(self) -> WorkerStatus:
        """Return an immutable snapshot of worker execution metrics."""
        with self._lock:
            return WorkerStatus(
                worker_id=self.worker_id,
                is_running=self.is_running,
                processed_count=self._processed_count,
                succeeded_count=self._succeeded_count,
                failed_count=self._failed_count,
                blocked_count=self._blocked_count,
                dead_lettered_count=self._dead_lettered_count,
                skipped_count=self._skipped_count,
                last_processed_at=self._last_processed_at,
            )


def create_default_worker_registry() -> JobRegistry:
    """Instantiate a JobRegistry configured with canonical domain handlers."""
    registry = JobRegistry()
    registry.register(FIRMSIngestJobHandler())
    registry.register(EventConstructJobHandler())
    registry.register(ContextEnrichJobHandler())
    registry.register(IntelligenceClassifyJobHandler())
    registry.register(EndToEndPipelineJobHandler())
    return registry


def get_default_worker_runner(
    queue: JobQueueProtocol | None = None,
    repository: JobRepositoryProtocol | None = None,
    runner: SyncJobRunner | None = None,
    worker_id: str | None = None,
) -> WorkerRunner:
    """Factory creating a fully configured WorkerRunner instance."""
    repo = repository or InMemoryJobRepository()
    registry = create_default_worker_registry()
    job_runner = runner or SyncJobRunner(repository=repo, registry=registry)
    job_queue = queue or InMemoryJobQueue()

    return WorkerRunner(
        queue=job_queue,
        repository=repo,
        runner=job_runner,
        worker_id=worker_id,
    )
