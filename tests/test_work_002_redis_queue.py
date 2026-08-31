"""Unit and integration tests for WORK-002 Transient Job Queue Infrastructure.

Validates:
1. JobQueueMessage schema, priorities, and serialization.
2. InMemoryJobQueue FIFO, priority scheduling, in-flight tracking, ack/reject.
3. Dead-letter queue routing and retry thresholding.
4. RedisJobQueue interface compliance, mocked Redis integration, and fallback.
5. Invariant: Database is authoritative; queue is transient coordination only.
6. Secret sanitization on message metadata and rejection reasons.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

from packages.config.settings import AppEnvironment, Settings
from packages.schemas.job import JobRecord, JobState, JobType
from services.worker.jobs.handler import JobRegistry
from services.worker.jobs.handlers import CallableJobHandler
from services.worker.jobs.queue import (
    InMemoryJobQueue,
    JobPriority,
    JobQueueMessage,
    JobQueueProtocol,
    RedisJobQueue,
    create_queue_message_from_job,
    get_default_job_queue,
)
from services.worker.jobs.repository import InMemoryJobRepository
from services.worker.jobs.runner import SyncJobRunner

# ==============================================================================
# 1. JobQueueMessage Schema Tests
# ==============================================================================


class TestJobQueueMessageSchema:
    """Test suite for JobQueueMessage attributes and validation."""

    def test_message_creation_defaults(self) -> None:
        msg = JobQueueMessage(
            job_id="job_001",
            job_type=JobType.INGEST.value,
        )
        assert msg.message_id.startswith("msg_")
        assert msg.job_id == "job_001"
        assert msg.job_type == "ingest"
        assert msg.priority == JobPriority.NORMAL
        assert msg.attempt_count == 0
        assert msg.max_retries == 3
        assert isinstance(msg.enqueued_at, datetime)

    def test_message_priority_customization(self) -> None:
        msg = JobQueueMessage(
            job_id="job_urgent",
            job_type=JobType.CLASSIFY.value,
            priority=JobPriority.HIGH,
            max_retries=5,
            pipeline_run_id="run_alpha",
        )
        assert msg.priority == 1
        assert msg.max_retries == 5
        assert msg.pipeline_run_id == "run_alpha"

    def test_message_json_roundtrip(self) -> None:
        original = JobQueueMessage(
            job_id="job_serialize",
            job_type=JobType.EVENT_CONSTRUCTION.value,
            priority=JobPriority.LOW,
            metadata={"batch_size": 500},
        )
        raw_json = original.model_dump_json()
        restored = JobQueueMessage.model_validate_json(raw_json)

        assert restored.message_id == original.message_id
        assert restored.job_id == original.job_id
        assert restored.job_type == original.job_type
        assert restored.priority == original.priority
        assert restored.metadata == {"batch_size": 500}


# ==============================================================================
# 2. InMemoryJobQueue Mechanics
# ==============================================================================


class TestInMemoryJobQueue:
    """Test suite for InMemoryJobQueue operations."""

    def test_enqueue_and_fifo_dequeue(self) -> None:
        queue = InMemoryJobQueue()
        assert queue.size() == 0

        m1 = JobQueueMessage(job_id="job_1", job_type="ingest")
        m2 = JobQueueMessage(job_id="job_2", job_type="enrich")

        id1 = queue.enqueue(m1)
        id2 = queue.enqueue(m2)
        assert id1 == m1.message_id
        assert id2 == m2.message_id
        assert queue.size() == 2

        # Peek does not remove
        peeked = queue.peek()
        assert peeked is not None
        assert peeked.job_id == "job_1"
        assert queue.size() == 2

        # Dequeue in FIFO order
        d1 = queue.dequeue()
        assert d1 is not None
        assert d1.job_id == "job_1"
        assert d1.attempt_count == 1
        assert queue.size() == 1
        assert queue.in_flight_size() == 1

        d2 = queue.dequeue()
        assert d2 is not None
        assert d2.job_id == "job_2"
        assert d2.attempt_count == 1
        assert queue.size() == 0
        assert queue.in_flight_size() == 2

        # Queue empty
        assert queue.dequeue() is None

    def test_priority_scheduling(self) -> None:
        queue = InMemoryJobQueue()

        m_low = JobQueueMessage(
            job_id="job_low", job_type="custom", priority=JobPriority.LOW
        )
        m_norm = JobQueueMessage(
            job_id="job_norm", job_type="custom", priority=JobPriority.NORMAL
        )
        m_high = JobQueueMessage(
            job_id="job_high", job_type="custom", priority=JobPriority.HIGH
        )

        # Enqueue in reverse priority order
        queue.enqueue(m_low)
        queue.enqueue(m_norm)
        queue.enqueue(m_high)

        # High priority dequeued first, then Normal, then Low
        r1 = queue.dequeue()
        assert r1 is not None
        assert r1.job_id == "job_high"

        r2 = queue.dequeue()
        assert r2 is not None
        assert r2.job_id == "job_norm"

        r3 = queue.dequeue()
        assert r3 is not None
        assert r3.job_id == "job_low"

    def test_acknowledgment_lifecycle(self) -> None:
        queue = InMemoryJobQueue()
        m = JobQueueMessage(job_id="job_ack", job_type="ingest")
        queue.enqueue(m)

        msg = queue.dequeue()
        assert msg is not None
        assert queue.in_flight_size() == 1

        # Acknowledge
        ack_res = queue.acknowledge(msg.message_id)
        assert ack_res is True
        assert queue.in_flight_size() == 0

        # Second ack fails gracefully
        assert queue.acknowledge(msg.message_id) is False

    def test_rejection_with_requeue(self) -> None:
        queue = InMemoryJobQueue()
        m = JobQueueMessage(
            job_id="job_retry",
            job_type="ingest",
            max_retries=3,
        )
        queue.enqueue(m)

        # First dequeue (attempt 1)
        msg = queue.dequeue()
        assert msg is not None
        assert msg.attempt_count == 1

        # Reject with requeue
        rej_res = queue.reject(msg.message_id, requeue=True, reason="Network timeout")
        assert rej_res is True
        assert queue.size() == 1
        assert queue.in_flight_size() == 0
        assert queue.dead_letter_size() == 0

        # Second dequeue (attempt 2)
        msg2 = queue.dequeue()
        assert msg2 is not None
        assert msg2.attempt_count == 2

    def test_dead_letter_on_exhausted_retries(self) -> None:
        queue = InMemoryJobQueue()
        m = JobQueueMessage(
            job_id="job_dlq",
            job_type="classify",
            max_retries=2,
        )
        queue.enqueue(m)

        # Attempt 1
        msg1 = queue.dequeue()
        assert msg1 is not None
        queue.reject(msg1.message_id, requeue=True)

        # Attempt 2 (exhausts max_retries=2)
        msg2 = queue.dequeue()
        assert msg2 is not None
        assert msg2.attempt_count == 2
        queue.reject(msg2.message_id, requeue=True, reason="Permanent database error")

        # Now dead-lettered
        assert queue.size() == 0
        assert queue.dead_letter_size() == 1
        dlq_msgs = queue.get_dead_letter_messages()
        assert len(dlq_msgs) == 1
        assert dlq_msgs[0].job_id == "job_dlq"
        assert dlq_msgs[0].metadata["dead_letter_reason"] == "Permanent database error"
        assert "dead_lettered_at" in dlq_msgs[0].metadata

    def test_direct_dead_letter_without_requeue(self) -> None:
        queue = InMemoryJobQueue()
        m = JobQueueMessage(job_id="job_abort", job_type="e2e_pipeline")
        queue.enqueue(m)

        msg = queue.dequeue()
        assert msg is not None
        queue.reject(msg.message_id, requeue=False, reason="Invalid schema payload")

        assert queue.size() == 0
        assert queue.dead_letter_size() == 1
        assert (
            queue.get_dead_letter_messages()[0].metadata["dead_letter_reason"]
            == "Invalid schema payload"
        )

    def test_purge_clears_all(self) -> None:
        queue = InMemoryJobQueue()
        queue.enqueue(JobQueueMessage(job_id="j1", job_type="t1"))
        queue.enqueue(JobQueueMessage(job_id="j2", job_type="t2"))
        msg = queue.dequeue()
        assert msg is not None
        queue.reject(msg.message_id, requeue=False)

        queue.enqueue(JobQueueMessage(job_id="j3", job_type="t3"))
        assert queue.size() == 2
        assert queue.dead_letter_size() == 1

        purged = queue.purge()
        assert purged >= 2
        assert queue.size() == 0
        assert queue.dead_letter_size() == 0

    def test_thread_safe_concurrent_producers_consumers(self) -> None:
        queue = InMemoryJobQueue()
        item_count = 50

        def producer(start_idx: int) -> None:
            for i in range(item_count):
                msg = JobQueueMessage(
                    job_id=f"job_{start_idx}_{i}",
                    job_type="concurrent_task",
                )
                queue.enqueue(msg)

        def consumer() -> list[str]:
            consumed: list[str] = []
            while len(consumed) < item_count:
                m = queue.dequeue()
                if m:
                    queue.acknowledge(m.message_id)
                    consumed.append(m.job_id)
            return consumed

        with ThreadPoolExecutor(max_workers=4) as executor:
            p1 = executor.submit(producer, 1)
            p2 = executor.submit(producer, 2)
            c1 = executor.submit(consumer)
            c2 = executor.submit(consumer)

            p1.result()
            p2.result()
            r1 = c1.result()
            r2 = c2.result()

        assert len(r1) + len(r2) == item_count * 2
        assert queue.size() == 0
        assert queue.in_flight_size() == 0


# ==============================================================================
# 3. RedisJobQueue Fallback and Mocked Integration
# ==============================================================================


class TestRedisJobQueue:
    """Test suite for RedisJobQueue with mocked Redis client and fallback."""

    def test_test_environment_falls_back_to_in_memory(self) -> None:
        settings = Settings(ENVIRONMENT=AppEnvironment.TEST)
        queue = RedisJobQueue(settings=settings)
        assert queue.is_redis_active is False

        # Queue operations still function seamlessly in-memory
        msg = JobQueueMessage(job_id="job_fallback", job_type="ingest")
        msg_id = queue.enqueue(msg)
        assert msg_id == msg.message_id
        assert queue.size() == 1

        deq = queue.dequeue()
        assert deq is not None
        assert deq.job_id == "job_fallback"
        assert queue.acknowledge(deq.message_id) is True

    def test_redis_queue_mocked_live_operations(self) -> None:
        mock_redis = MagicMock()
        storage: dict[str, list[str]] = {}
        in_flight_h: dict[str, str] = {}

        def mock_lpush(key: str, val: str) -> int:
            if key not in storage:
                storage[key] = []
            storage[key].insert(0, val)
            return len(storage[key])

        def mock_rpop(key: str) -> str | None:
            if storage.get(key):
                return storage[key].pop()
            return None

        def mock_llen(key: str) -> int:
            return len(storage.get(key, []))

        def mock_hset(name: str, key: str, val: str) -> int:
            in_flight_h[key] = val
            return 1

        def mock_hdel(name: str, key: str) -> int:
            if key in in_flight_h:
                del in_flight_h[key]
                return 1
            return 0

        def mock_hget(name: str, key: str) -> str | None:
            return in_flight_h.get(key)

        mock_redis.lpush.side_effect = mock_lpush
        mock_redis.rpop.side_effect = mock_rpop
        mock_redis.llen.side_effect = mock_llen
        mock_redis.hset.side_effect = mock_hset
        mock_redis.hdel.side_effect = mock_hdel
        mock_redis.hget.side_effect = mock_hget
        mock_redis.ping.return_value = True

        queue = RedisJobQueue(settings=Settings())
        queue._redis_client = mock_redis
        queue._is_redis_active = True

        # 1. Enqueue
        msg = JobQueueMessage(
            job_id="job_redis_live",
            job_type="classify",
            priority=JobPriority.HIGH,
        )
        msg_id = queue.enqueue(msg)
        assert msg_id == msg.message_id
        assert queue.size() == 1

        # 2. Dequeue
        deq = queue.dequeue()
        assert deq is not None
        assert deq.job_id == "job_redis_live"
        assert deq.attempt_count == 1
        assert queue.size() == 0

        # 3. Acknowledge
        assert queue.acknowledge(deq.message_id) is True

    def test_default_job_queue_factory(self) -> None:
        queue = get_default_job_queue()
        assert isinstance(queue, JobQueueProtocol)


# ==============================================================================
# 4. Invariant: Database is Authoritative / Queue is Transient
# ==============================================================================


class TestDatabaseAuthorityInvariant:
    """Validate that the DB is the source of truth and queue is purely transient."""

    def test_queue_message_references_db_job_without_mutating_db(self) -> None:
        repo = InMemoryJobRepository()
        queue = InMemoryJobQueue()

        # 1. Create authoritative DB record
        db_job = JobRecord(
            job_type=JobType.INGEST.value,
            idempotency_key="firms:jamnagar:2026-08-20",
            state=JobState.QUEUED,
        )
        repo.save_job(db_job)

        # 2. Create transient queue message pointer
        q_msg = create_queue_message_from_job(db_job, priority=JobPriority.HIGH)
        queue.enqueue(q_msg)

        assert q_msg.job_id == db_job.job_id
        assert q_msg.job_type == db_job.job_type
        assert q_msg.priority == 1

        # DB job remains in original QUEUED state untouched
        fetched_db_job = repo.get_job(db_job.job_id)
        assert fetched_db_job is not None
        assert fetched_db_job.state == JobState.QUEUED

    def test_transient_queue_worker_execution_flow(self) -> None:
        """Simulate end-to-end decoupled dispatch -> queue -> worker execution."""
        repo = InMemoryJobRepository()
        queue = InMemoryJobQueue()
        registry = JobRegistry()

        def custom_ingest_fn(ctx: Any, inp: Any) -> dict[str, Any]:
            return {"ingested_count": 100, "status": "ok"}

        registry.register(CallableJobHandler("async_ingest", custom_ingest_fn))
        runner = SyncJobRunner(repository=repo, registry=registry)

        # Step 1: API creates authoritative JobRecord
        job = runner.create_job(
            job_type="async_ingest",
            input_reference={"source": "firms"},
        )
        assert job.state == JobState.QUEUED

        # Step 2: API pushes transient reference into queue
        q_msg = create_queue_message_from_job(job)
        queue.enqueue(q_msg)
        assert queue.size() == 1

        # Step 3: Background worker pops message from transient queue
        work_msg = queue.dequeue()
        assert work_msg is not None
        assert work_msg.job_id == job.job_id

        # Step 4: Worker fetches authoritative JobRecord from DB and runs it
        executed_job = runner.run_job(work_msg.job_id)
        assert executed_job.state == JobState.SUCCEEDED
        assert executed_job.result_summary == {
            "ingested_count": 100,
            "status": "ok",
        }

        # Step 5: Worker acknowledges queue message
        queue.acknowledge(work_msg.message_id)
        assert queue.size() == 0
        assert queue.in_flight_size() == 0

        # Step 6: Verify authoritative DB contains final state
        final_db_job = repo.get_job(job.job_id)
        assert final_db_job is not None
        assert final_db_job.state == JobState.SUCCEEDED


# ==============================================================================
# 5. Security & Secret Sanitization
# ==============================================================================


class TestQueueSecuritySanitization:
    """Validate that credentials and sensitive tokens are scrubbed from queues."""

    def test_sensitive_tokens_scrubbed_from_queue_message_metadata(self) -> None:
        queue = InMemoryJobQueue()
        msg = JobQueueMessage(
            job_id="job_secure",
            job_type="custom",
            metadata={
                "api_key": "SECRET_API_TOKEN_12345",
                "map_key": "SECRET_MAP_KEY_9999",
                "normal_field": "public_data",
            },
        )

        queue.enqueue(msg)
        deq = queue.dequeue()
        assert deq is not None

        assert "SECRET_API_TOKEN_12345" not in str(deq.metadata)
        assert "SECRET_MAP_KEY_9999" not in str(deq.metadata)
        assert deq.metadata["api_key"] == "[REDACTED]"
        assert deq.metadata["map_key"] == "[REDACTED]"
        assert deq.metadata["normal_field"] == "public_data"

    def test_secrets_scrubbed_from_dead_letter_reason(self) -> None:
        queue = InMemoryJobQueue()
        msg = JobQueueMessage(job_id="job_dlq_sec", job_type="custom")
        queue.enqueue(msg)

        deq = queue.dequeue()
        assert deq is not None
        queue.reject(
            deq.message_id,
            requeue=False,
            reason="Failed with map_key=FIRMS_SECRET_XYZ and api_key=SECRET_TOKEN",
        )

        dlq_msg = queue.get_dead_letter_messages()[0]
        reason = dlq_msg.metadata["dead_letter_reason"]
        assert "FIRMS_SECRET_XYZ" not in reason
        assert "SECRET_TOKEN" not in reason
