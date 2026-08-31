"""Job execution context and progress tracking (WORK-001).

Provides runtime metadata, logging context, cancellation checking, and progress
reporting to executing job handlers.
"""

from collections.abc import Callable
from typing import Any

from packages.errors.exceptions import JobCancelledError
from packages.logging import get_logger, log_with_context


class JobContext:
    """Execution context passed to synchronous job handlers."""

    def __init__(
        self,
        job_id: str,
        job_type: str,
        attempt_count: int = 1,
        pipeline_run_id: str | None = None,
        cancellation_checker: Callable[[], bool] | None = None,
        progress_callback: Callable[[float, str], None] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.job_id = job_id
        self.job_type = job_type
        self.attempt_count = attempt_count
        self.pipeline_run_id = pipeline_run_id
        self._cancellation_checker = cancellation_checker
        self._progress_callback = progress_callback
        self.metadata = metadata or {}
        self.logger = get_logger(f"services.worker.jobs.{job_type}")

    def is_cancellation_requested(self) -> bool:
        """Check if cancellation has been flagged for this job."""
        if self._cancellation_checker is not None:
            return self._cancellation_checker()
        return False

    def check_cancellation(self) -> None:
        """Verify job has not been cancelled, raising JobCancelledError if it has."""
        if self.is_cancellation_requested():
            raise JobCancelledError(
                f"Job '{self.job_id}' execution cancelled by request."
            )

    def report_progress(self, percentage: float, stage_description: str = "") -> None:
        """Report progress percentage (0.0 - 100.0) and current operational stage."""
        clamped_pct = max(0.0, min(100.0, float(percentage)))
        if self._progress_callback is not None:
            self._progress_callback(clamped_pct, stage_description)
        log_with_context(
            self.logger,
            20,  # INFO
            f"Job '{self.job_id}' progress: {clamped_pct:.1f}% - {stage_description}",
            context={
                "job_id": self.job_id,
                "job_type": self.job_type,
                "pipeline_run_id": self.pipeline_run_id,
                "progress_pct": clamped_pct,
                "stage": stage_description,
            },
        )
