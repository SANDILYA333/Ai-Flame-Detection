"""Base job handler abstraction and registry (WORK-001).

Defines the contract for synchronous job execution and handler discovery.
"""

from abc import ABC, abstractmethod
from typing import Any

from packages.errors.exceptions import NotFoundError
from services.worker.jobs.context import JobContext


class BaseJobHandler(ABC):
    """Abstract base contract for discrete job execution handlers."""

    @property
    @abstractmethod
    def job_type(self) -> str:
        """The canonical job type handled by this class."""
        ...

    @abstractmethod
    def execute(self, context: JobContext, input_reference: Any) -> Any:
        """Execute the job workload synchronously.

        Args:
            context: The runtime JobContext.
            input_reference: Serialized inputs or pointers to source data.

        Returns:
            Execution result data / output summary dict.

        Raises:
            Exception: Any exception encountered during execution.
        """
        ...


class JobRegistry:
    """Central registry mapping job_type identifiers to handler instances."""

    def __init__(self) -> None:
        self._handlers: dict[str, BaseJobHandler] = {}

    def register(self, handler: BaseJobHandler) -> None:
        """Register a job handler instance."""
        self._handlers[handler.job_type] = handler

    def get(self, job_type: str) -> BaseJobHandler:
        """Retrieve the handler for a job type.

        Raises:
            NotFoundError: If no handler is registered for job_type.
        """
        handler = self._handlers.get(job_type)
        if handler is None:
            raise NotFoundError(
                f"No job handler registered for job type '{job_type}'."
            )
        return handler

    def has(self, job_type: str) -> bool:
        """Check whether a handler is registered for job_type."""
        return job_type in self._handlers

    def list_job_types(self) -> list[str]:
        """List all registered job type strings."""
        return sorted(self._handlers.keys())
