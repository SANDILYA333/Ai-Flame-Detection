"""Rolling 90-day spatiotemporal baseline engine and recurrence analysis (INTEL-004).

Implements rolling 90-day historical window analysis around detected thermal events:
1. Spatial filtering via Haversine distance within configurable radius (default 1.0 km).
2. Temporal filtering within [T_current - 90 days, T_current) strictly in UTC.
3. Recurrence index R90 = (unique active calendar days) / 90.
4. Historical FRP mean (mu90) and sample standard deviation (sigma90) with sigma floor.
5. Anomaly detection metrics: FRP Z-score and FRP Surge Ratio.
6. Robust cold-start handling when 0 historical observations are present.
7. Operational status labeling (ROUTINE_PERSISTENT_FLARING, ABNORMAL_INDUSTRIAL_SURGE, etc.).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from packages.geospatial.distance import haversine_distance_meters

if TYPE_CHECKING:
    from collections.abc import Sequence
    from packages.schemas.detection import Detection
    from packages.schemas.event import Event


@dataclass(frozen=True)
class TemporalBaselineResult:
    """Telemetry and anomaly metrics from 90-day historical baseline evaluation."""

    recurrence_90d: float
    historical_mean_frp: float
    historical_std_frp: float
    sample_count: int
    active_calendar_days: int
    frp_z_score: float
    frp_surge_ratio: float
    operational_status: str
    is_critical_anomaly: bool
    window_days: int = 90
    radius_km: float = 1.0
    is_cold_start: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert result to clean serialization dict."""
        return {
            "recurrence_90d": round(self.recurrence_90d, 4),
            "historical_mean_frp": round(self.historical_mean_frp, 2),
            "historical_std_frp": round(self.historical_std_frp, 2),
            "sample_count": self.sample_count,
            "active_calendar_days": self.active_calendar_days,
            "frp_z_score": round(self.frp_z_score, 2),
            "frp_surge_ratio": round(self.frp_surge_ratio, 2),
            "operational_status": self.operational_status,
            "is_critical_anomaly": self.is_critical_anomaly,
            "window_days": self.window_days,
            "radius_km": round(self.radius_km, 2),
            "is_cold_start": self.is_cold_start,
        }


class TemporalBaselineEngine:
    """Engine computing rolling 90-day spatiotemporal baselines and anomaly metrics."""

    DEFAULT_WINDOW_DAYS: int = 90
    DEFAULT_RADIUS_KM: float = 1.0
    DEFAULT_SIGMA_FLOOR_MW: float = 1.0

    @classmethod
    def calculate_baseline(
        cls,
        current_event: Event,
        historical_events: Sequence[Event] | None = None,
        historical_detections: Sequence[Detection] | None = None,
        window_days: int = DEFAULT_WINDOW_DAYS,
        radius_km: float = DEFAULT_RADIUS_KM,
        sigma_floor_mw: float = DEFAULT_SIGMA_FLOOR_MW,
    ) -> TemporalBaselineResult:
        """Compute rolling historical baseline for a target event.

        Args:
            current_event: Canonical Event under evaluation.
            historical_events: Sequence of historical Event records.
            historical_detections: Optional raw member detections for granular FRP.
            window_days: Historical temporal window size in days (default 90).
            radius_km: Geospatial search radius in km (default 1.0).
            sigma_floor_mw: Minimum standard deviation floor in MW (default 1.0).

        Returns:
            TemporalBaselineResult containing recurrence, statistics, and anomaly status.
        """
        # Ensure UTC-aware timestamp for current event
        current_time = current_event.started_at
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=UTC)

        cutoff_start = current_time - timedelta(days=window_days)
        target_lat = current_event.centroid_geometry.latitude
        target_lon = current_event.centroid_geometry.longitude
        radius_m = radius_km * 1000.0

        current_frp = (
            current_event.mean_frp_mw
            if current_event.mean_frp_mw is not None
            else 0.0
        )

        # 1. Gather historical observation points (prefer detections if available, else events)
        matched_frps: list[float] = []
        active_dates: set[str] = set()

        if historical_detections:
            for det in historical_detections:
                det_time = det.acquired_at
                if det_time.tzinfo is None:
                    det_time = det_time.replace(tzinfo=UTC)

                # Strictly preceding within [current_time - 90d, current_time)
                if not (cutoff_start <= det_time < current_time):
                    continue

                # Geospatial distance check
                dist_m = haversine_distance_meters(
                    target_lat,
                    target_lon,
                    det.geometry.latitude,
                    det.geometry.longitude,
                )
                if dist_m <= radius_m:
                    frp_val = det.frp_mw if det.frp_mw is not None else 0.0
                    matched_frps.append(frp_val)
                    active_dates.add(det_time.strftime("%Y-%m-%d"))

        elif historical_events:
            for ev in historical_events:
                if ev.event_id == current_event.event_id:
                    continue

                ev_time = ev.ended_at
                if ev_time.tzinfo is None:
                    ev_time = ev_time.replace(tzinfo=UTC)

                # Strictly preceding within [current_time - 90d, current_time)
                if not (cutoff_start <= ev_time < current_time):
                    continue

                # Geospatial distance check
                dist_m = haversine_distance_meters(
                    target_lat,
                    target_lon,
                    ev.centroid_geometry.latitude,
                    ev.centroid_geometry.longitude,
                )
                if dist_m <= radius_m:
                    frp_val = ev.mean_frp_mw if ev.mean_frp_mw is not None else 0.0
                    matched_frps.append(frp_val)
                    active_dates.add(ev_time.strftime("%Y-%m-%d"))

        sample_count = len(matched_frps)
        active_calendar_days = len(active_dates)

        # 2. Cold-start handling
        if sample_count == 0:
            recurrence_90d = 0.0
            hist_mean = 0.0
            hist_std = 1.0
            z_score = current_frp / max(hist_std, sigma_floor_mw)
            surge_ratio = current_frp / 1.0

            # Classification logic for cold-start
            if recurrence_90d < 0.15 and current_frp >= 25.0:
                operational_status = "ACUTE_UNPRECEDENTED_SURGE"
                is_critical = True
            else:
                operational_status = "TRANSIENT_BACKGROUND"
                is_critical = False

            return TemporalBaselineResult(
                recurrence_90d=recurrence_90d,
                historical_mean_frp=hist_mean,
                historical_std_frp=hist_std,
                sample_count=0,
                active_calendar_days=0,
                frp_z_score=z_score,
                frp_surge_ratio=surge_ratio,
                operational_status=operational_status,
                is_critical_anomaly=is_critical,
                window_days=window_days,
                radius_km=radius_km,
                is_cold_start=True,
            )

        # 3. Compute recurrence index R90 in [0.0, 1.0]
        recurrence_90d = min(1.0, max(0.0, active_calendar_days / float(window_days)))

        # 4. Compute historical mean and sample standard deviation
        hist_mean = sum(matched_frps) / float(sample_count)
        if sample_count >= 2:
            variance = sum((x - hist_mean) ** 2 for x in matched_frps) / float(
                sample_count - 1
            )
            hist_std = math.sqrt(variance)
        else:
            hist_std = sigma_floor_mw

        effective_std = max(hist_std, sigma_floor_mw)

        # 5. Compute FRP Z-score and Surge Ratio
        z_score = (current_frp - hist_mean) / effective_std
        surge_ratio = current_frp / max(hist_mean, 1.0)

        # 6. Operational Status Classification
        is_critical = False
        if recurrence_90d >= 0.70 and z_score <= 2.5:
            operational_status = "ROUTINE_PERSISTENT_FLARING"
        elif recurrence_90d >= 0.60 and z_score > 3.0 and current_frp > 30.0:
            operational_status = "ABNORMAL_INDUSTRIAL_SURGE"
            is_critical = True
        elif recurrence_90d < 0.15 and current_frp >= 25.0:
            operational_status = "ACUTE_UNPRECEDENTED_SURGE"
            is_critical = True
        else:
            operational_status = "TRANSIENT_BACKGROUND"

        return TemporalBaselineResult(
            recurrence_90d=recurrence_90d,
            historical_mean_frp=hist_mean,
            historical_std_frp=hist_std,
            sample_count=sample_count,
            active_calendar_days=active_calendar_days,
            frp_z_score=z_score,
            frp_surge_ratio=surge_ratio,
            operational_status=operational_status,
            is_critical_anomaly=is_critical,
            window_days=window_days,
            radius_km=radius_km,
            is_cold_start=False,
        )
