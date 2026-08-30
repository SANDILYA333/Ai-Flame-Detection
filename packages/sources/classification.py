"""Persistence state classification and recurrence metrics for thermal sources."""

from collections.abc import Sequence
from datetime import datetime

from packages.schemas.enums import PersistenceState


def calculate_active_calendar_days(timestamps: Sequence[datetime]) -> int:
    """Calculate the number of unique calendar dates with observed thermal activity.

    Dates are evaluated in UTC to ensure consistent, timezone-agnostic aggregation.

    Args:
        timestamps: Non-empty sequence of UTC observation/event timestamps.

    Returns:
        int: Count of distinct calendar days (>= 1).

    Raises:
        ValueError: If timestamps sequence is empty.
    """
    if not timestamps:
        raise ValueError("Cannot calculate active calendar days for empty timestamps.")

    unique_dates = {ts.date() for ts in timestamps}
    return len(unique_dates)


def calculate_observation_span_days(
    first_seen_at: datetime,
    last_seen_at: datetime,
) -> float:
    """Calculate the temporal observation span in decimal days.

    Args:
        first_seen_at: Earliest observation timestamp in UTC.
        last_seen_at: Latest observation timestamp in UTC.

    Returns:
        float: Duration in days (>= 0.0).

    Raises:
        ValueError: If last_seen_at precedes first_seen_at.
    """
    if last_seen_at < first_seen_at:
        raise ValueError(
            f"last_seen_at ({last_seen_at}) cannot precede "
            f"first_seen_at ({first_seen_at})."
        )

    delta_seconds = (last_seen_at - first_seen_at).total_seconds()
    return delta_seconds / 86400.0


def calculate_recurrence_ratio(
    active_days_count: int,
    first_seen_at: datetime,
    last_seen_at: datetime,
) -> float:
    """Calculate the observed activity ratio over the observation window.

    Defined as: active_calendar_days / total_calendar_days_in_window.
    For a 1-day window, returns 1.0.

    Args:
        active_days_count: Number of unique calendar days with activity.
        first_seen_at: Earliest observation timestamp in UTC.
        last_seen_at: Latest observation timestamp in UTC.

    Returns:
        float: Recurrence ratio in [0.0, 1.0].
    """
    if active_days_count < 1:
        raise ValueError("active_days_count must be at least 1.")

    total_calendar_days = (last_seen_at.date() - first_seen_at.date()).days + 1
    total_calendar_days = max(1, total_calendar_days)

    ratio = float(active_days_count) / float(total_calendar_days)
    return min(1.0, max(0.0, ratio))


def classify_persistence_state(
    total_event_count: int,
    active_days_count: int,
    observation_span_days: float,
    persistence_threshold_days: float,
    persistence_min_observations: int,
) -> PersistenceState:
    """Classify the persistence state of a thermal source cluster.

    CRITICAL SCIENTIFIC DISTINCTION:
    - PERSISTENT: Activity is observed across multiple independent calendar dates
      AND spans at least persistence_threshold_days.
    - RECURRING: Activity recurs across multiple dates (>= 2 active days) but
      has not yet satisfied the long-term persistence_threshold_days duration.
    - TRANSIENT: Activity is confined to a single calendar date (e.g. one-off
      agricultural burn or daytime/nighttime overpass of the same fire episode).
    - INSUFFICIENT_HISTORY: Single instantaneous observation with zero duration.

    Args:
        total_event_count: Total count of associated thermal events (>= 1).
        active_days_count: Number of unique calendar days with activity (>= 1).
        observation_span_days: Temporal span in days (>= 0.0).
        persistence_threshold_days: Minimum duration threshold for persistence.
        persistence_min_observations: Minimum active days/observations count.

    Returns:
        PersistenceState: Classified persistence state.
    """
    if total_event_count < 1:
        raise ValueError("total_event_count must be at least 1.")
    if active_days_count < 1:
        raise ValueError("active_days_count must be at least 1.")
    if observation_span_days < 0.0:
        raise ValueError("observation_span_days must be non-negative.")

    # 1. Full persistence criteria met
    if (
        active_days_count >= persistence_min_observations
        and observation_span_days >= persistence_threshold_days
    ):
        return PersistenceState.PERSISTENT

    # 2. Multi-day recurring activity below full persistence duration
    if active_days_count >= 2:
        return PersistenceState.RECURRING

    # 3. Single-day activity with multiple events or single extended event
    if total_event_count > 1:
        return PersistenceState.TRANSIENT

    # 4. Single instantaneous event
    if observation_span_days == 0.0:
        return PersistenceState.INSUFFICIENT_HISTORY

    return PersistenceState.TRANSIENT
