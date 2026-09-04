"""Comprehensive unit and regression tests for 90-Day Rolling Temporal Baseline Engine."""

from datetime import UTC, datetime, timedelta

import pytest
from packages.intelligence.baseline import TemporalBaselineEngine, TemporalBaselineResult
from packages.schemas.common import Coordinate
from packages.schemas.detection import Detection
from packages.schemas.event import Event


def _make_dummy_event(
    event_id: str,
    lat: float,
    lon: float,
    started_at: datetime,
    mean_frp_mw: float = 25.0,
) -> Event:
    """Helper to create minimal valid Event domain model for testing."""
    return Event(
        event_id=event_id,
        detection_ids=[f"det_{event_id}"],
        detection_count=1,
        started_at=started_at,
        ended_at=started_at + timedelta(minutes=15),
        centroid_geometry=Coordinate(latitude=lat, longitude=lon),
        formation_configuration_id="cfg_test_v1",
        formation_configuration_version="1.0.0",
        mean_frp_mw=mean_frp_mw,
        max_frp_mw=mean_frp_mw,
        duration_seconds=900.0,
    )


def _make_dummy_detection(
    det_id: str,
    lat: float,
    lon: float,
    acquired_at: datetime,
    frp_mw: float = 20.0,
) -> Detection:
    """Helper to create minimal valid Detection domain model for testing."""
    return Detection(
        detection_id=det_id,
        source="firms",
        source_snapshot_id="snap_001",
        acquired_at=acquired_at,
        geometry=Coordinate(latitude=lat, longitude=lon),
        satellite="NOAA-20",
        instrument="VIIRS",
        product_type="nrt",
        product_version="v1",
        frp_mw=frp_mw,
    )


def test_baseline_cold_start_zero_history():
    """Test 1: Cold start with 0 historical observations."""
    target_time = datetime(2026, 6, 15, 12, 0, 0, tzinfo=UTC)
    current_event = _make_dummy_event("ev_target", 22.47, 70.06, target_time, mean_frp_mw=50.0)

    result = TemporalBaselineEngine.calculate_baseline(
        current_event=current_event,
        historical_events=[],
        historical_detections=[],
        window_days=90,
        radius_km=1.0,
    )

    assert result.is_cold_start is True
    assert result.recurrence_90d == 0.0
    assert result.historical_mean_frp == 0.0
    assert result.sample_count == 0
    assert result.active_calendar_days == 0
    assert result.historical_std_frp == 1.0
    assert result.frp_z_score == 50.0
    assert result.frp_surge_ratio == 50.0
    assert result.operational_status == "ACUTE_UNPRECEDENTED_SURGE"
    assert result.is_critical_anomaly is True


def test_baseline_persistent_routine_emitter():
    """Test 2: Persistent operational source active across 75 of 90 days."""
    target_time = datetime(2026, 6, 15, 12, 0, 0, tzinfo=UTC)
    current_event = _make_dummy_event("ev_target", 22.47, 70.06, target_time, mean_frp_mw=22.0)

    # Generate observations across 75 distinct days in the past 90 days
    hist_events = []
    for day_offset in range(1, 76):
        hist_time = target_time - timedelta(days=day_offset, hours=2)
        hist_events.append(
            _make_dummy_event(f"ev_hist_{day_offset}", 22.4702, 70.0601, hist_time, mean_frp_mw=20.0)
        )

    result = TemporalBaselineEngine.calculate_baseline(
        current_event=current_event,
        historical_events=hist_events,
        window_days=90,
        radius_km=1.0,
    )

    assert result.is_cold_start is False
    assert result.sample_count == 75
    assert result.active_calendar_days == 75
    assert pytest.approx(result.recurrence_90d, abs=0.01) == 75 / 90.0  # ~0.833
    assert result.recurrence_90d >= 0.70
    assert pytest.approx(result.historical_mean_frp, abs=0.1) == 20.0
    assert result.frp_z_score <= 2.5
    assert result.operational_status == "ROUTINE_PERSISTENT_FLARING"
    assert result.is_critical_anomaly is False


def test_baseline_abnormal_industrial_surge():
    """Test 3: Persistent site with historical mean ~20MW experiencing huge 120MW surge."""
    target_time = datetime(2026, 6, 15, 12, 0, 0, tzinfo=UTC)
    current_event = _make_dummy_event("ev_target", 22.47, 70.06, target_time, mean_frp_mw=120.0)

    # 60 active days with mean ~20MW, std ~3MW
    hist_events = []
    for day_offset in range(1, 61):
        frp = 20.0 + (3.0 if day_offset % 2 == 0 else -3.0)
        hist_time = target_time - timedelta(days=day_offset)
        hist_events.append(
            _make_dummy_event(f"ev_hist_{day_offset}", 22.4701, 70.0602, hist_time, mean_frp_mw=frp)
        )

    result = TemporalBaselineEngine.calculate_baseline(
        current_event=current_event,
        historical_events=hist_events,
        window_days=90,
        radius_km=1.0,
    )

    assert result.recurrence_90d >= 0.60
    assert result.frp_z_score > 3.0
    assert result.frp_surge_ratio > 4.0
    assert result.operational_status == "ABNORMAL_INDUSTRIAL_SURGE"
    assert result.is_critical_anomaly is True


def test_baseline_spatial_exclusion():
    """Test 4: Historical events outside 1.0 km radius must be excluded."""
    target_time = datetime(2026, 6, 15, 12, 0, 0, tzinfo=UTC)
    current_event = _make_dummy_event("ev_target", 22.4700, 70.0600, target_time, mean_frp_mw=25.0)

    # Event 1: 400m away (lat ~ +0.0036 deg) -> INCLUDED
    ev_near = _make_dummy_event("ev_near", 22.4736, 70.0600, target_time - timedelta(days=5), 15.0)
    # Event 2: 5km away (lat ~ +0.045 deg) -> EXCLUDED
    ev_far = _make_dummy_event("ev_far", 22.5200, 70.0600, target_time - timedelta(days=10), 100.0)

    result = TemporalBaselineEngine.calculate_baseline(
        current_event=current_event,
        historical_events=[ev_near, ev_far],
        window_days=90,
        radius_km=1.0,
    )

    assert result.sample_count == 1
    assert result.active_calendar_days == 1
    assert result.historical_mean_frp == 15.0


def test_baseline_temporal_exclusion():
    """Test 5: Observations older than 90 days or in the future must be excluded."""
    target_time = datetime(2026, 6, 15, 12, 0, 0, tzinfo=UTC)
    current_event = _make_dummy_event("ev_target", 22.4700, 70.0600, target_time, mean_frp_mw=25.0)

    # Event within window (45 days ago) -> INCLUDED
    ev_valid = _make_dummy_event("ev_valid", 22.4700, 70.0600, target_time - timedelta(days=45), 18.0)
    # Event too old (95 days ago) -> EXCLUDED
    ev_old = _make_dummy_event("ev_old", 22.4700, 70.0600, target_time - timedelta(days=95), 80.0)
    # Future event (+1 day) -> EXCLUDED
    ev_future = _make_dummy_event("ev_future", 22.4700, 70.0600, target_time + timedelta(days=1), 90.0)

    result = TemporalBaselineEngine.calculate_baseline(
        current_event=current_event,
        historical_events=[ev_valid, ev_old, ev_future],
        window_days=90,
        radius_km=1.0,
    )

    assert result.sample_count == 1
    assert result.historical_mean_frp == 18.0
