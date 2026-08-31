"""Transient Job Queue Infrastructure (WORK-002 / Section 21).

Provides transient queue abstractions and implementations for dispatching
background jobs to workers.

CRITICAL ARCHITECTURAL INVARIANTS:
1. The queue is strictly transient; the PostgreSQL database remains authoritative.
2. Redis is transient coordination only; it is NOT the source of truth.
3. Offline-first execution: fully operational with InMemoryJobQueue when Redis is
   unavailable or during unit/integration tests.
4. Zero secret leakage: queue message payloads and logs are sanitized.
"""

import json
import logging
import threading
from abc import abstractmethod
from collections import deque
from datetime import UTC, datetime
from enum import IntEnum
from typing import Any, Protocol, runtime_checkable
from uuid import uuid4

from pydantic import Field

from packages.config.settings import AppEnvironment, Settings, get_settings
from packages.logging import get_logger, log_with_context
from packages.logging.sanitizer import sanitize_log_dict, sanitize_log_value
from packages.schemas.common import BaseDomainModel, UtcDatetime
from packages.schemas.job import JobRecord

logger = get_logger("services.worker.jobs.queue")


class JobPriority(IntEnum):
    """Execution priority levels for transient job queueing."""

    HIGH = 1
    NORMAL = 5
    LOW = 10


_STANDARD_PRIORITIES = (
    JobPriority.HIGH.value,
    JobPriority.NORMAL.value,
    JobPriority.LOW.value,
)


class JobQueueMessage(BaseDomainModel):
    """Transient message container representing an enqueued job dispatch."""

    message_id: str = Field(
        default_factory=lambda: f"msg_{uuid4().hex[:12]}",
        description="Unique transient message identifier",
    )
    job_id: str = Field(
        ...,
        min_length=1,
        description="Authoritative JobRecord ID in the database repository",
    )
    job_type: str = Field(
        ...,
        min_length=1,
        description="Canonical job type descriptor",
    )
    priority: int = Field(
        default=JobPriority.NORMAL,
        ge=1,
        le=100,
        description="Queue priority (lower number = higher priority)",
    )
    enqueued_at: UtcDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when message was put into queue",
    )
    attempt_count: int = Field(
        default=0,
        ge=0,
        description="Delivery / dispatch attempt counter",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        description="Max transient queue dispatch retries before dead-lettering",
    )
    pipeline_run_id: str | None = Field(
        default=None,
        description="Optional parent pipeline run ID for lineage tracing",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Transient dispatch metadata (sanitized)",
    )


@runtime_checkable
class JobQueueProtocol(Protocol):
    """Protocol contract for transient job dispatch queues."""

    @abstractmethod
    def enqueue(self, message: JobQueueMessage) -> str:
        """Enqueue a job dispatch message. Returns the message_id."""
        ...

    @abstractmethod
    def dequeue(self, timeout_seconds: float = 0.0) -> JobQueueMessage | None:
        """Dequeue the next highest-priority message, or None if queue is empty."""
        ...

    @abstractmethod
    def peek(self) -> JobQueueMessage | None:
        """Inspect the next message without dequeuing it."""
        ...

    @abstractmethod
    def acknowledge(self, message_id: str) -> bool:
        """Mark an in-flight message as successfully processed."""
        ...

    @abstractmethod
    def reject(
        self,
        message_id: str,
        requeue: bool = False,
        reason: str | None = None,
    ) -> bool:
        """Reject an in-flight message.

        If requeue is True and attempts < max_retries, re-enqueues message.
        Otherwise moves message to the dead-letter queue.
        """
        ...

    @abstractmethod
    def size(self) -> int:
        """Return the current number of queued messages."""
        ...

    @abstractmethod
    def dead_letter_size(self) -> int:
        """Return the number of dead-lettered messages."""
        ...

    @abstractmethod
    def get_dead_letter_messages(self) -> list[JobQueueMessage]:
        """Retrieve all dead-lettered messages for inspection."""
        ...

    @abstractmethod
    def purge(self) -> int:
        """Clear all queued and in-flight messages. Returns purged count."""
        ...


class InMemoryJobQueue(JobQueueProtocol):
    """Thread-safe, in-memory deterministic priority job queue.

    Used as the default offline-first and test queue backend.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        # Multi-priority buckets: priority_int -> deque of messages
        self._buckets: dict[int, deque[JobQueueMessage]] = {}
        self._in_flight: dict[str, JobQueueMessage] = {}
        self._dead_letter: list[JobQueueMessage] = []

    def enqueue(self, message: JobQueueMessage) -> str:
        with self._lock:
            sanitized_meta = sanitize_log_dict(message.metadata)
            clean_msg = message.model_copy(
                update={"metadata": sanitized_meta},
                deep=True,
            )
            p = clean_msg.priority
            if p not in self._buckets:
                self._buckets[p] = deque()
            self._buckets[p].append(clean_msg)
            return clean_msg.message_id

    def dequeue(self, timeout_seconds: float = 0.0) -> JobQueueMessage | None:
        with self._lock:
            sorted_priorities = sorted(self._buckets.keys())
            for p in sorted_priorities:
                bucket = self._buckets[p]
                if bucket:
                    msg = bucket.popleft()
                    updated_msg = msg.model_copy(
                        update={"attempt_count": msg.attempt_count + 1},
                        deep=True,
                    )
                    self._in_flight[updated_msg.message_id] = updated_msg
                    return updated_msg
            return None

    def peek(self) -> JobQueueMessage | None:
        with self._lock:
            sorted_priorities = sorted(self._buckets.keys())
            for p in sorted_priorities:
                bucket = self._buckets[p]
                if bucket:
                    return bucket[0]
            return None

    def acknowledge(self, message_id: str) -> bool:
        with self._lock:
            if message_id in self._in_flight:
                del self._in_flight[message_id]
                return True
            return False

    def reject(
        self,
        message_id: str,
        requeue: bool = False,
        reason: str | None = None,
    ) -> bool:
        with self._lock:
            if message_id not in self._in_flight:
                return False

            msg = self._in_flight.pop(message_id)
            safe_reason = sanitize_log_value(reason or "Rejected")

            if requeue and msg.attempt_count < msg.max_retries:
                p = msg.priority
                if p not in self._buckets:
                    self._buckets[p] = deque()
                self._buckets[p].append(msg)
                return True
            else:
                dead_letter_msg = msg.model_copy(
                    update={
                        "metadata": {
                            **msg.metadata,
                            "dead_letter_reason": safe_reason,
                            "dead_lettered_at": datetime.now(UTC).isoformat(),
                        }
                    },
                    deep=True,
                )
                self._dead_letter.append(dead_letter_msg)
                return True

    def size(self) -> int:
        with self._lock:
            return sum(len(b) for b in self._buckets.values())

    def in_flight_size(self) -> int:
        with self._lock:
            return len(self._in_flight)

    def dead_letter_size(self) -> int:
        with self._lock:
            return len(self._dead_letter)

    def get_dead_letter_messages(self) -> list[JobQueueMessage]:
        with self._lock:
            return list(self._dead_letter)

    def purge(self) -> int:
        with self._lock:
            total = self.size() + len(self._in_flight)
            self._buckets.clear()
            self._in_flight.clear()
            self._dead_letter.clear()
            return total


class RedisJobQueue(JobQueueProtocol):
    """Redis-backed transient job queue with automatic offline-fallback.

    Adheres strictly to the invariant: 'Redis is not the source of truth.
    Queue is transient coordination only.'
    """

    def __init__(
        self,
        settings: Settings | None = None,
        fallback_queue: JobQueueProtocol | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._fallback = fallback_queue or InMemoryJobQueue()
        self._redis_client: Any = None
        self._is_redis_active = False
        self._init_redis()

    def _init_redis(self) -> None:
        """Attempt connection to Redis instance if configured."""
        if self.settings.ENVIRONMENT == AppEnvironment.TEST:
            # Under test environment, default to in-memory mode
            self._is_redis_active = False
            return

        try:
            import redis  # type: ignore[import-not-found]

            redis_url = self.settings.get_redis_url()
            client = redis.Redis.from_url(
                redis_url,
                socket_timeout=self.settings.REDIS_TIMEOUT_SECONDS,
                decode_responses=True,
            )
            client.ping()
            self._redis_client = client
            self._is_redis_active = True
            log_with_context(
                logger,
                logging.INFO,
                "Connected to Redis transient job queue.",
                context={"redis_host": self.settings.REDIS_HOST},
            )
        except Exception as e:
            self._is_redis_active = False
            self._redis_client = None
            log_with_context(
                logger,
                logging.DEBUG,
                f"Redis unavailable ({e}); using InMemoryJobQueue fallback.",
                context={"fallback": "InMemoryJobQueue"},
            )

    @property
    def is_redis_active(self) -> bool:
        """Return True if connected to a live Redis instance."""
        return self._is_redis_active

    def _get_queue_key(self, priority: int) -> str:
        prefix = self.settings.REDIS_QUEUE_KEY_PREFIX
        return f"{prefix}:p{priority}"

    def _get_in_flight_key(self) -> str:
        prefix = self.settings.REDIS_QUEUE_KEY_PREFIX
        return f"{prefix}:in_flight"

    def _get_dead_letter_key(self) -> str:
        prefix = self.settings.REDIS_QUEUE_KEY_PREFIX
        return f"{prefix}:dead_letter"

    def enqueue(self, message: JobQueueMessage) -> str:
        if not self._is_redis_active or self._redis_client is None:
            return self._fallback.enqueue(message)

        try:
            sanitized_meta = sanitize_log_dict(message.metadata)
            clean_msg = message.model_copy(
                update={"metadata": sanitized_meta},
                deep=True,
            )
            payload = clean_msg.model_dump_json()
            queue_key = self._get_queue_key(clean_msg.priority)
            self._redis_client.lpush(queue_key, payload)
            return clean_msg.message_id
        except Exception as e:
            log_with_context(
                logger,
                logging.WARNING,
                f"Redis enqueue failed ({e}); failing over to in-memory fallback.",
            )
            return self._fallback.enqueue(message)

    def dequeue(self, timeout_seconds: float = 0.0) -> JobQueueMessage | None:
        if not self._is_redis_active or self._redis_client is None:
            return self._fallback.dequeue(timeout_seconds)

        try:
            # Check priorities in order (1 -> 10)
            for p in sorted(_STANDARD_PRIORITIES):
                key = self._get_queue_key(p)
                raw = self._redis_client.rpop(key)
                if raw:
                    data = json.loads(raw)
                    msg = JobQueueMessage.model_validate(data)
                    updated_msg = msg.model_copy(
                        update={"attempt_count": msg.attempt_count + 1},
                        deep=True,
                    )
                    # Track in-flight
                    self._redis_client.hset(
                        self._get_in_flight_key(),
                        updated_msg.message_id,
                        updated_msg.model_dump_json(),
                    )
                    return updated_msg
            return None
        except Exception as e:
            log_with_context(
                logger,
                logging.WARNING,
                f"Redis dequeue failed ({e}); failing over to in-memory fallback.",
            )
            return self._fallback.dequeue(timeout_seconds)

    def peek(self) -> JobQueueMessage | None:
        if not self._is_redis_active or self._redis_client is None:
            return self._fallback.peek()

        try:
            for p in sorted(_STANDARD_PRIORITIES):
                key = self._get_queue_key(p)
                raw = self._redis_client.lindex(key, -1)
                if raw:
                    return JobQueueMessage.model_validate_json(raw)
            return None
        except Exception:
            return self._fallback.peek()

    def acknowledge(self, message_id: str) -> bool:
        if not self._is_redis_active or self._redis_client is None:
            return self._fallback.acknowledge(message_id)

        try:
            res = self._redis_client.hdel(self._get_in_flight_key(), message_id)
            return bool(res > 0)
        except Exception:
            return self._fallback.acknowledge(message_id)

    def reject(
        self,
        message_id: str,
        requeue: bool = False,
        reason: str | None = None,
    ) -> bool:
        if not self._is_redis_active or self._redis_client is None:
            return self._fallback.reject(message_id, requeue, reason)

        try:
            raw = self._redis_client.hget(self._get_in_flight_key(), message_id)
            if not raw:
                return False

            self._redis_client.hdel(self._get_in_flight_key(), message_id)
            msg = JobQueueMessage.model_validate_json(raw)
            safe_reason = sanitize_log_value(reason or "Rejected")

            if requeue and msg.attempt_count < msg.max_retries:
                queue_key = self._get_queue_key(msg.priority)
                self._redis_client.lpush(queue_key, msg.model_dump_json())
                return True
            else:
                dead_letter_msg = msg.model_copy(
                    update={
                        "metadata": {
                            **msg.metadata,
                            "dead_letter_reason": safe_reason,
                            "dead_lettered_at": datetime.now(UTC).isoformat(),
                        }
                    },
                    deep=True,
                )
                self._redis_client.lpush(
                    self._get_dead_letter_key(),
                    dead_letter_msg.model_dump_json(),
                )
                return True
        except Exception:
            return self._fallback.reject(message_id, requeue, reason)

    def size(self) -> int:
        if not self._is_redis_active or self._redis_client is None:
            return self._fallback.size()

        try:
            total = 0
            for p in _STANDARD_PRIORITIES:
                total += int(self._redis_client.llen(self._get_queue_key(p)))
            return total
        except Exception:
            return self._fallback.size()

    def dead_letter_size(self) -> int:
        if not self._is_redis_active or self._redis_client is None:
            return self._fallback.dead_letter_size()

        try:
            return int(self._redis_client.llen(self._get_dead_letter_key()))
        except Exception:
            return self._fallback.dead_letter_size()

    def get_dead_letter_messages(self) -> list[JobQueueMessage]:
        if not self._is_redis_active or self._redis_client is None:
            return self._fallback.get_dead_letter_messages()

        try:
            raw_list = self._redis_client.lrange(self._get_dead_letter_key(), 0, -1)
            return [JobQueueMessage.model_validate_json(r) for r in raw_list]
        except Exception:
            return self._fallback.get_dead_letter_messages()

    def purge(self) -> int:
        if not self._is_redis_active or self._redis_client is None:
            return self._fallback.purge()

        try:
            count = self.size()
            keys = [self._get_queue_key(p) for p in _STANDARD_PRIORITIES]
            keys.extend([self._get_in_flight_key(), self._get_dead_letter_key()])
            self._redis_client.delete(*keys)
            self._fallback.purge()
            return count
        except Exception:
            return self._fallback.purge()


def create_queue_message_from_job(
    job: JobRecord,
    priority: int = JobPriority.NORMAL,
    max_retries: int = 3,
) -> JobQueueMessage:
    """Construct a transient JobQueueMessage reference from an authoritative JobRecord.

    Preserves the fundamental invariant:
    The JobRecord in the database is authoritative; the queue message is
    merely a transient execution pointer.
    """
    return JobQueueMessage(
        job_id=job.job_id,
        job_type=job.job_type,
        priority=priority,
        attempt_count=job.attempt_count,
        max_retries=max_retries,
        pipeline_run_id=job.pipeline_run_id,
        metadata={
            "created_state": job.state.value,
            "idempotency_key": job.idempotency_key,
        },
    )


def get_default_job_queue(settings: Settings | None = None) -> JobQueueProtocol:
    """Return default job queue instance (RedisJobQueue with in-memory fallback)."""
    return RedisJobQueue(settings=settings)
