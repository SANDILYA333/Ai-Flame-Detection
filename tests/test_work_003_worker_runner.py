"""Unit and integration tests for WORK-003 Worker Runner.

Validates:
1. WorkerStatus observable execution metrics and defaults.
2. WorkerRunner.process_one execution flow with authoritative DB state.
3. Idempotency deduplication and terminal state skipping.
4. Pre-execution cancellation finalization.
5. Missing scientific configuration BLOCKED state queue acknowledgment.
6. Retry bounded requeuing and dead-letter routing upon exhaustion.
7. Orphaned message handling and dead-lettering.
8. Deterministic run_until_empty queue draining.
9. Concurrent background thread execution (start/stop/is_running).
10. Integration with canonical domain handlers.
"""

import time
from datetime import UTC, datetime
from typing import Any

from packages.errors.exceptions import MissingConfigurationError
from packages.schemas.job import JobRecord, JobState
from services.worker.jobs.handler import JobRegistry
from services.worker.jobs.handlers import CallableJobHandler
from services.worker.jobs.queue import (
    InMemoryJobQueue,
    JobPriority,
    JobQueueMessage,
    create_queue_message_from_job,
)
from services.worker.jobs.repository import InMemoryJobRepository
from services.worker.jobs.runner import SyncJobRunner
from services.worker.jobs.worker import (
    WorkerRunner,
    WorkerStatus,
    get_default_worker_runner,
)

# ==============================================================================
# 1. WorkerStatus Metrics Tests
# ==============================================================================


class TestWorkerStatus:
    """Test suite for WorkerStatus domain model."""

    def test_worker_status_defaults(self) -> None:
        status = WorkerStatus(worker_id="w_test_01")
        assert status.worker_id == "w_test_01"
        assert status.is_running is False
        assert status.processed_count == 0
        assert status.succeeded_count == 0
        assert status.failed_count == 0
        assert status.blocked_count == 0
        assert status.dead_lettered_count == 0
        assert status.skipped_count == 0
        assert status.last_processed_at is None

    def test_worker_status_serialization(self) -> None:
        now = datetime.now(UTC)
        status = WorkerStatus(
            worker_id="w_test_02",
            is_running=True,
            processed_count=10,
            succeeded_count=8,
            failed_count=2,
            last_processed_at=now,
        )
        json_data = status.model_dump_json()
        restored = WorkerStatus.model_validate_json(json_data)
        assert restored.worker_id == "w_test_02"
        assert restored.succeeded_count == 8
        assert restored.is_running is True


# ==============================================================================
# 2. Worker Execution Flow & State Coordination
# ==============================================================================


class TestWorkerRunnerExecution:
    """Test suite for WorkerRunner execution mechanics."""

    def test_empty_queue_returns_none(self) -> None:
        worker = get_default_worker_runner()
        res = worker.process_one()
        assert res is None
        status = worker.get_status()
        assert status.processed_count == 0

    def test_successful_job_execution_lifecycle(self) -> None:
        repo = InMemoryJobRepository()
        queue = InMemoryJobQueue()
        registry = JobRegistry()

        def compute_fn(ctx: Any, inp: Any) -> dict[str, Any]:
            return {"sum": 42}

        registry.register(CallableJobHandler("calc", compute_fn))
        runner = SyncJobRunner(repository=repo, registry=registry)
        worker = WorkerRunner(queue=queue, repository=repo, runner=runner)

        # 1. Authoritative DB job
        job = runner.create_job("calc", input_reference={"val": 42})
        assert job.state == JobState.QUEUED

        # 2. Transient queue message
        queue.enqueue(create_queue_message_from_job(job))
        assert queue.size() == 1

        # 3. Worker process
        res = worker.process_one()
        assert res is not None
        assert res.job_id == job.job_id
        assert res.state == JobState.SUCCEEDED
        assert res.result_summary == {"sum": 42}

        # 4. Queue message acknowledged & removed
        assert queue.size() == 0
        assert queue.in_flight_size() == 0

        # 5. Metrics updated
        status = worker.get_status()
        assert status.processed_count == 1
        assert status.succeeded_count == 1
        assert status.failed_count == 0

    def test_idempotent_duplicate_message_skipped(self) -> None:
        repo = InMemoryJobRepository()
        queue = InMemoryJobQueue()
        worker = WorkerRunner(queue=queue, repository=repo)

        # Job already SUCCEEDED in DB
        db_job = JobRecord(
            job_type="custom",
            state=JobState.SUCCEEDED,
            result_summary={"already": "done"},
        )
        repo.save_job(db_job)

        # Duplicate message arrives in transient queue
        msg = JobQueueMessage(job_id=db_job.job_id, job_type="custom")
        queue.enqueue(msg)

        res = worker.process_one()
        assert res is not None
        assert res.job_id == db_job.job_id
        assert res.state == JobState.SUCCEEDED

        # Acknowledged without re-executing
        assert queue.size() == 0
        assert queue.in_flight_size() == 0
        status = worker.get_status()
        assert status.skipped_count == 1
        assert status.succeeded_count == 0

    def test_pre_execution_cancellation_finalized(self) -> None:
        repo = InMemoryJobRepository()
        queue = InMemoryJobQueue()
        worker = WorkerRunner(queue=queue, repository=repo)

        # Job marked CANCEL_REQUESTED while waiting in queue
        db_job = JobRecord(
            job_type="custom",
            state=JobState.CANCEL_REQUESTED,
        )
        repo.save_job(db_job)

        msg = JobQueueMessage(job_id=db_job.job_id, job_type="custom")
        queue.enqueue(msg)

        res = worker.process_one()
        assert res is not None
        assert res.state == JobState.CANCELLED

        # DB updated to CANCELLED
        updated_db_job = repo.get_job(db_job.job_id)
        assert updated_db_job is not None
        assert updated_db_job.state == JobState.CANCELLED

        # Queue message acknowledged
        assert queue.size() == 0
        assert worker.get_status().skipped_count == 1

    def test_missing_config_blocked_state_acknowledged(self) -> None:
        repo = InMemoryJobRepository()
        queue = InMemoryJobQueue()
        registry = JobRegistry()

        def incomplete_fn(ctx: Any, inp: Any) -> Any:
            raise MissingConfigurationError("Parameter unset: ['spatial_radius']")

        registry.register(CallableJobHandler("scientific_op", incomplete_fn))
        runner = SyncJobRunner(repository=repo, registry=registry)
        worker = WorkerRunner(queue=queue, repository=repo, runner=runner)

        job = runner.create_job("scientific_op")
        queue.enqueue(create_queue_message_from_job(job))

        res = worker.process_one()
        assert res is not None
        assert res.state == JobState.BLOCKED

        # Queue message acknowledged (do not spin-retry unconfigured jobs)
        assert queue.size() == 0
        assert queue.in_flight_size() == 0
        status = worker.get_status()
        assert status.blocked_count == 1
        assert status.failed_count == 0

    def test_orphaned_queue_message_dead_lettered(self) -> None:
        repo = InMemoryJobRepository()
        queue = InMemoryJobQueue()
        worker = WorkerRunner(queue=queue, repository=repo)

        # Enqueue message with no corresponding DB record
        msg = JobQueueMessage(job_id="job_ghost_999", job_type="custom")
        queue.enqueue(msg)

        res = worker.process_one()
        assert res is None

        # Dead-lettered in queue
        assert queue.size() == 0
        assert queue.dead_letter_size() == 1
        dlq = queue.get_dead_letter_messages()
        assert len(dlq) == 1
        assert dlq[0].job_id == "job_ghost_999"
        assert "not found" in dlq[0].metadata["dead_letter_reason"]

        status = worker.get_status()
        assert status.dead_lettered_count == 1


# ==============================================================================
# 3. Retry and Dead-Letter Thresholding
# ==============================================================================


class TestWorkerRetryAndDeadLetter:
    """Test suite for retry bounds and dead-letter queue routing."""

    def test_transient_failure_requeued_under_retry_limit(self) -> None:
        repo = InMemoryJobRepository()
        queue = InMemoryJobQueue()
        registry = JobRegistry()

        attempt_counter = 0

        def flaky_fn(ctx: Any, inp: Any) -> Any:
            nonlocal attempt_counter
            attempt_counter += 1
            if attempt_counter < 2:
                raise ValueError("Transient upstream connection glitch")
            return {"status": "recovered"}

        registry.register(CallableJobHandler("flaky", flaky_fn))
        runner = SyncJobRunner(repository=repo, registry=registry)
        worker = WorkerRunner(queue=queue, repository=repo, runner=runner)

        job = runner.create_job("flaky", max_attempts=3)
        queue.enqueue(create_queue_message_from_job(job, max_retries=3))

        # First execution attempt -> Fails and requeues
        res1 = worker.process_one()
        assert res1 is not None
        assert res1.state == JobState.QUEUED
        assert res1.attempt_count == 1

        # Message is back in queue for retry
        assert queue.size() == 1
        assert queue.dead_letter_size() == 0

        # Second execution attempt -> Succeeds
        res2 = worker.process_one()
        assert res2 is not None
        assert res2.state == JobState.SUCCEEDED
        assert res2.attempt_count == 2
        assert queue.size() == 0

    def test_exhausted_retries_dead_lettered(self) -> None:
        repo = InMemoryJobRepository()
        queue = InMemoryJobQueue()
        registry = JobRegistry()

        def always_fails_fn(ctx: Any, inp: Any) -> Any:
            raise RuntimeError("Permanent schema incompatibility")

        registry.register(CallableJobHandler("fatal", always_fails_fn))
        runner = SyncJobRunner(repository=repo, registry=registry)
        worker = WorkerRunner(queue=queue, repository=repo, runner=runner)

        job = runner.create_job("fatal", max_attempts=2)
        queue.enqueue(create_queue_message_from_job(job, max_retries=2))

        # Attempt 1 -> Fails & requeues
        r1 = worker.process_one()
        assert r1 is not None
        assert r1.state == JobState.QUEUED
        assert queue.size() == 1

        # Attempt 2 -> Fails & dead-letters (exhausts max_attempts=2)
        r2 = worker.process_one()
        assert r2 is not None
        assert r2.state == JobState.FAILED
        assert queue.size() == 0
        assert queue.dead_letter_size() == 1

        dlq = queue.get_dead_letter_messages()
        assert len(dlq) == 1
        assert dlq[0].job_id == job.job_id
        assert "Permanent schema incompatibility" in str(
            dlq[0].metadata["dead_letter_reason"]
        )

        status = worker.get_status()
        assert status.failed_count == 2
        assert status.dead_lettered_count == 1


# ==============================================================================
# 4. Batch & Background Thread Operations
# ==============================================================================


class TestWorkerBatchAndBackgroundExecution:
    """Test suite for run_until_empty and background daemon thread execution."""

    def test_run_until_empty_drains_queue(self) -> None:
        repo = InMemoryJobRepository()
        queue = InMemoryJobQueue()
        registry = JobRegistry()

        def task_fn(ctx: Any, inp: Any) -> dict[str, Any]:
            return {"index": inp.get("i", 0)}

        registry.register(CallableJobHandler("batch_task", task_fn))
        runner = SyncJobRunner(repository=repo, registry=registry)
        worker = WorkerRunner(queue=queue, repository=repo, runner=runner)

        # Enqueue 5 jobs with varied priorities
        for i in range(5):
            p = JobPriority.HIGH if i % 2 == 0 else JobPriority.NORMAL
            j = runner.create_job("batch_task", input_reference={"i": i})
            queue.enqueue(create_queue_message_from_job(j, priority=p))

        assert queue.size() == 5

        # Drain until empty
        drained = worker.run_until_empty(max_jobs=10)
        assert len(drained) == 5
        assert queue.size() == 0
        assert all(j.state == JobState.SUCCEEDED for j in drained)

        status = worker.get_status()
        assert status.processed_count == 5
        assert status.succeeded_count == 5

    def test_background_thread_lifecycle(self) -> None:
        repo = InMemoryJobRepository()
        queue = InMemoryJobQueue()
        registry = JobRegistry()

        def delayed_task(ctx: Any, inp: Any) -> dict[str, Any]:
            return {"done": True}

        registry.register(CallableJobHandler("async_work", delayed_task))
        runner = SyncJobRunner(repository=repo, registry=registry)
        worker = WorkerRunner(queue=queue, repository=repo, runner=runner)

        # 1. Start background thread
        assert not worker.get_status().is_running
        worker.start(poll_interval_seconds=0.05)
        assert worker.get_status().is_running

        # 2. Push work while running
        job = runner.create_job("async_work")
        queue.enqueue(create_queue_message_from_job(job))

        # Wait for worker to consume
        time.sleep(0.2)
        assert queue.size() == 0

        final_job = repo.get_job(job.job_id)
        assert final_job is not None
        assert final_job.state == JobState.SUCCEEDED

        # 3. Stop background thread
        worker.stop()
        assert not worker.get_status().is_running

    def test_default_worker_runner_factory(self) -> None:
        worker = get_default_worker_runner()
        assert isinstance(worker, WorkerRunner)
        assert worker.worker_id.startswith("worker_")
        assert worker.is_running is False
