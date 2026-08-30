"""Worker background job definitions and synchronous runner (WORK-001).

Provides authoritative job state management, synchronous pipeline runner,
idempotency tracking, and canonical domain handlers.
"""

from packages.schemas.job import (
    JobRecord,
    JobState,
    JobType,
    PipelineRun,
    PipelineRunStatus,
)
from services.worker.jobs.context import JobContext
from services.worker.jobs.handler import BaseJobHandler, JobRegistry
from services.worker.jobs.handlers import (
    CallableJobHandler,
    ContextEnrichJobHandler,
    EndToEndPipelineJobHandler,
    EventConstructJobHandler,
    FIRMSIngestJobHandler,
    IntelligenceClassifyJobHandler,
)
from services.worker.jobs.queue import (
    InMemoryJobQueue,
    JobPriority,
    JobQueueMessage,
    JobQueueProtocol,
    RedisJobQueue,
    create_queue_message_from_job,
    get_default_job_queue,
)
from services.worker.jobs.repository import (
    InMemoryJobRepository,
    JobRepositoryProtocol,
)
from services.worker.jobs.runner import SyncJobRunner
from services.worker.jobs.state_machine import JobStateMachine


def create_default_job_registry() -> JobRegistry:
    """Create a JobRegistry populated with all canonical domain handlers."""
    registry = JobRegistry()
    registry.register(FIRMSIngestJobHandler())
    registry.register(EventConstructJobHandler())
    registry.register(ContextEnrichJobHandler())
    registry.register(IntelligenceClassifyJobHandler())
    registry.register(EndToEndPipelineJobHandler())
    return registry


def get_default_job_runner(
    repository: JobRepositoryProtocol | None = None,
) -> SyncJobRunner:
    """Provide a SyncJobRunner pre-configured with canonical domain handlers."""
    registry = create_default_job_registry()
    repo = repository or InMemoryJobRepository()
    return SyncJobRunner(repository=repo, registry=registry)


__all__ = [
    "BaseJobHandler",
    "CallableJobHandler",
    "ContextEnrichJobHandler",
    "EndToEndPipelineJobHandler",
    "EventConstructJobHandler",
    "FIRMSIngestJobHandler",
    "InMemoryJobQueue",
    "InMemoryJobRepository",
    "IntelligenceClassifyJobHandler",
    "JobContext",
    "JobPriority",
    "JobQueueMessage",
    "JobQueueProtocol",
    "JobRecord",
    "JobRegistry",
    "JobRepositoryProtocol",
    "JobState",
    "JobStateMachine",
    "JobType",
    "PipelineRun",
    "PipelineRunStatus",
    "RedisJobQueue",
    "SyncJobRunner",
    "create_default_job_registry",
    "create_queue_message_from_job",
    "get_default_job_queue",
    "get_default_job_runner",
]
