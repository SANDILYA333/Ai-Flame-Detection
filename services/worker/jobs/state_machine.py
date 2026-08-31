"""Pure Job State Machine and Transition Rules (WORK-001).

Implements authoritative state transition logic for discrete processing jobs
as specified in Section 21 and Section 3.26 of the canonical execution plan.
"""

from datetime import UTC, datetime
from typing import Any

from packages.errors.exceptions import InvalidJobStateTransitionError
from packages.logging.sanitizer import sanitize_log_dict
from packages.schemas.job import JobRecord, JobState

# Explicit table of permitted directed state transitions
_VALID_TRANSITIONS: dict[JobState, set[JobState]] = {
    JobState.QUEUED: {
        JobState.RUNNING,
        JobState.CANCEL_REQUESTED,
        JobState.CANCELLED,
    },
    JobState.RUNNING: {
        JobState.SUCCEEDED,
        JobState.FAILED,
        JobState.BLOCKED,
        JobState.CANCEL_REQUESTED,
    },
    JobState.CANCEL_REQUESTED: {
        JobState.CANCELLED,
        JobState.FAILED,
        # In case execution finished before cancellation was registered
        JobState.SUCCEEDED,
    },
    JobState.FAILED: {
        JobState.QUEUED,  # Retrying a failed job
    },
    JobState.BLOCKED: {
        JobState.QUEUED,  # Unblocking / retrying once prerequisite is resolved
    },
    JobState.SUCCEEDED: set(),  # Terminal state
    JobState.CANCELLED: set(),  # Terminal state
}

_TERMINAL_STATES: frozenset[JobState] = frozenset(
    {JobState.SUCCEEDED, JobState.CANCELLED}
)


class JobStateMachine:
    """Deterministic, pure state machine governing JobRecord state transitions."""

    @classmethod
    def is_valid_transition(cls, from_state: JobState, to_state: JobState) -> bool:
        """Check whether transitioning from from_state to to_state is valid.

        Args:
            from_state: Current job state.
            to_state: Proposed target job state.

        Returns:
            True if transition is allowed, False otherwise.
        """
        return to_state in _VALID_TRANSITIONS.get(from_state, set())

    @classmethod
    def is_terminal_state(cls, state: JobState) -> bool:
        """Check whether a state is terminal and immutable."""
        return state in _TERMINAL_STATES

    @classmethod
    def transition(
        cls,
        job: JobRecord,
        target_state: JobState,
        *,
        error_code: str | None = None,
        error_message_safe: str | None = None,
        result_summary: dict[str, Any] | None = None,
        extra_metadata: dict[str, Any] | None = None,
    ) -> JobRecord:
        """Apply a validated state transition to a JobRecord, returning an updated copy.

        Args:
            job: The current JobRecord.
            target_state: Target JobState.
            error_code: Optional error code if failing or blocking.
            error_message_safe: Optional sanitized error message.
            result_summary: Optional result payload if succeeding.
            extra_metadata: Optional additional metadata to append.

        Returns:
            New immutable JobRecord instance reflecting the transition.

        Raises:
            InvalidJobStateTransitionError: If the transition is illegal.
        """
        current_state = job.state

        if not cls.is_valid_transition(current_state, target_state):
            raise InvalidJobStateTransitionError(
                f"Illegal job state transition from {current_state.value} "
                f"to {target_state.value} for job '{job.job_id}'."
            )

        now = datetime.now(UTC)
        started_at = job.started_at
        completed_at = job.completed_at
        attempt_count = job.attempt_count

        if target_state == JobState.RUNNING:
            if started_at is None:
                started_at = now
            attempt_count += 1
        elif target_state in (
            JobState.SUCCEEDED,
            JobState.FAILED,
            JobState.BLOCKED,
            JobState.CANCELLED,
        ):
            completed_at = now

        # Update metadata safely
        merged_metadata = dict(job.metadata)
        if extra_metadata:
            merged_metadata.update(sanitize_log_dict(extra_metadata))

        # Record state transition history in metadata
        history = list(merged_metadata.get("state_history", []))
        history.append(
            {
                "from_state": current_state.value,
                "to_state": target_state.value,
                "timestamp": now.isoformat(),
            }
        )
        merged_metadata["state_history"] = history

        # Sanitize result summary if provided
        sanitized_summary = (
            sanitize_log_dict(result_summary) if result_summary is not None else None
        )

        return JobRecord(
            job_id=job.job_id,
            job_type=job.job_type,
            pipeline_run_id=job.pipeline_run_id,
            idempotency_key=job.idempotency_key,
            state=target_state,
            attempt_count=attempt_count,
            max_attempts=job.max_attempts,
            created_at=job.created_at,
            started_at=started_at,
            completed_at=completed_at,
            error_code=error_code or job.error_code,
            error_message_safe=error_message_safe or job.error_message_safe,
            input_reference=job.input_reference,
            result_summary=sanitized_summary or job.result_summary,
            metadata=merged_metadata,
        )
