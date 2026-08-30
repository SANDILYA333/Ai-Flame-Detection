"""Leakage-safe feature extraction engine for SIH26162 Phase 4 ML.

Extracts approved numerical, categorical, temporal, and spatial context features
from canonical Event, Detection, Source, and Context entities strictly as of
an explicit prediction cutoff timestamp (T_prediction), enforcing temporal
invariants and scientific missingness contracts.
"""

import math
from collections.abc import Sequence
from datetime import timedelta

from packages.geospatial.distance import haversine_distance_meters
from packages.schemas.common import ProvenanceReference, UtcDatetime
from packages.schemas.context import ContextEvidence
from packages.schemas.detection import Detection
from packages.schemas.enums import ContextType, DayNight, PersistenceState
from packages.schemas.event import Event
from packages.schemas.ml import (
    FeatureRecord,
    TargetUnit,
)
from packages.schemas.source import PersistentSource
from services.ml.features.registry import FeatureRegistry
from services.ml.features.standard_set import get_standard_feature_registry


class FeatureExtractor:
    """Extractor computing leakage-safe feature records as of prediction time."""

    def __init__(self, registry: FeatureRegistry | None = None) -> None:
        self.registry = registry or get_standard_feature_registry()

    def extract_features_for_event(
        self,
        event: Event,
        member_detections: Sequence[Detection],
        as_of_time: UtcDatetime,
        preceding_events: Sequence[Event] | None = None,
        source: PersistentSource | None = None,
        context_evidence: Sequence[ContextEvidence] | None = None,
        allowed_feature_names: Sequence[str] | None = None,
        provenance: ProvenanceReference | None = None,
    ) -> FeatureRecord:
        """Extract a single FeatureRecord for an event as of as_of_time.

        CRITICAL LEAKAGE INVARIANTS:
        1. Only detections with acquired_at <= as_of_time are included.
        2. Only preceding events with ended_at < as_of_time are counted.
        3. Missing values are preserved as None (missing != 0) with explicit flags.
        4. Identifiers and reference labels are strictly excluded from features dict.

        Args:
            event: Canonical Event domain model.
            member_detections: Sequence of member Detection objects.
            as_of_time: UTC prediction cutoff timestamp.
            preceding_events: Optional sequence of historical events in vicinity.
            source: Optional associated PersistentSource record.
            context_evidence: Optional sequence of matched ContextEvidence records.
            allowed_feature_names: Optional filter of approved feature names.
            provenance: Optional provenance lineage reference.

        Returns:
            FeatureRecord: Structured, type-safe feature row.

        Raises:
            ValueError: If no member detections occurred on or before as_of_time.
        """
        # 1. Temporal Cutoff Filtering
        valid_detections = [d for d in member_detections if d.acquired_at <= as_of_time]
        if not valid_detections:
            raise ValueError(
                f"Event '{event.event_id}' has 0 detections on or before "
                f"prediction time {as_of_time.isoformat()}."
            )

        valid_preceding = [
            e
            for e in (preceding_events or [])
            if e.ended_at < as_of_time and e.event_id != event.event_id
        ]

        valid_context = list(context_evidence or [])

        # 2. Extract Feature Dictionary
        features_dict: dict[str, float | int | str | bool | None] = {}

        # --- Group: THERMAL_CORE ---
        det_count = len(valid_detections)
        features_dict["detection_count"] = det_count

        frps = [d.frp_mw for d in valid_detections if d.frp_mw is not None]
        if frps:
            features_dict["frp_mean_mw"] = float(sum(frps) / len(frps))
            features_dict["frp_max_mw"] = float(max(frps))
            features_dict["frp_min_mw"] = float(min(frps))
            features_dict["frp_sum_mw"] = float(sum(frps))
            if len(frps) > 1:
                mean_val = sum(frps) / len(frps)
                variance = sum((x - mean_val) ** 2 for x in frps) / (len(frps) - 1)
                features_dict["frp_std_mw"] = float(math.sqrt(variance))
            else:
                features_dict["frp_std_mw"] = 0.0
        else:
            features_dict["frp_mean_mw"] = None
            features_dict["frp_max_mw"] = None
            features_dict["frp_min_mw"] = None
            features_dict["frp_sum_mw"] = None
            features_dict["frp_std_mw"] = None

        timestamps = [d.acquired_at for d in valid_detections]
        first_time = min(timestamps)
        last_time = max(timestamps)
        duration_hrs = (last_time - first_time).total_seconds() / 3600.0
        features_dict["duration_hours"] = float(duration_hrs)
        features_dict["temporal_density"] = float(det_count / max(duration_hrs, 1.0))

        bts = [
            d.brightness_ti4_k
            for d in valid_detections
            if d.brightness_ti4_k is not None
        ]
        features_dict["brightness_mean_kelvin"] = (
            float(sum(bts) / len(bts)) if bts else None
        )
        features_dict["brightness_max_kelvin"] = float(max(bts)) if bts else None

        # Spatial extent radius in meters from event centroid
        c_lat = event.centroid_geometry.latitude
        c_lon = event.centroid_geometry.longitude
        distances = [
            haversine_distance_meters(
                c_lat,
                c_lon,
                d.geometry.latitude,
                d.geometry.longitude,
            )
            for d in valid_detections
        ]
        features_dict["spatial_extent_radius_meters"] = (
            float(max(distances)) if distances else 0.0
        )

        day_count = sum(1 for d in valid_detections if d.day_night == DayNight.DAY)
        features_dict["daynight_ratio"] = float(day_count / det_count)

        platforms = {d.satellite for d in valid_detections if d.satellite}
        features_dict["satellite_platform_diversity"] = len(platforms)

        instruments = {d.instrument for d in valid_detections if d.instrument}
        if len(instruments) == 1:
            features_dict["sensor_instrument"] = next(iter(instruments))
        elif len(instruments) > 1:
            features_dict["sensor_instrument"] = "HYBRID"
        else:
            features_dict["sensor_instrument"] = "UNKNOWN"

        # --- Group: TEMPORAL_HISTORY ---
        t_24h = as_of_time - timedelta(hours=24)
        t_7d = as_of_time - timedelta(days=7)
        t_30d = as_of_time - timedelta(days=30)

        features_dict["prior_event_count_24h"] = sum(
            1 for e in valid_preceding if e.ended_at >= t_24h
        )
        features_dict["prior_event_count_7d"] = sum(
            1 for e in valid_preceding if e.ended_at >= t_7d
        )
        features_dict["prior_event_count_30d"] = sum(
            1 for e in valid_preceding if e.ended_at >= t_30d
        )

        if valid_preceding:
            latest_prev = max(e.ended_at for e in valid_preceding)
            elapsed_hrs = (as_of_time - latest_prev).total_seconds() / 3600.0
            features_dict["time_since_previous_event_hours"] = float(
                max(0.0, elapsed_hrs)
            )
        else:
            features_dict["time_since_previous_event_hours"] = None

        # --- Group: PERSISTENCE_SOURCE ---
        if source and source.first_seen_at <= as_of_time:
            features_dict["persistence_active_days"] = source.active_days_count
            features_dict["persistence_total_events"] = source.total_event_count
            features_dict["persistence_recurrence_ratio"] = source.recurrence_ratio
            features_dict["is_persistent_source"] = source.persistence_state in (
                PersistenceState.PERSISTENT,
                PersistenceState.RECURRING,
            )
            features_dict["persistence_state"] = source.persistence_state.value
        else:
            features_dict["persistence_active_days"] = 0
            features_dict["persistence_total_events"] = 0
            features_dict["persistence_recurrence_ratio"] = None
            features_dict["is_persistent_source"] = False
            features_dict["persistence_state"] = PersistenceState.TRANSIENT.value

        # --- Group: SPATIAL_CONTEXT ---
        industrial_types = (
            ContextType.INDUSTRIAL,
            ContextType.OIL_GAS,
            ContextType.MINING,
        )
        facility_ev = next(
            (c for c in valid_context if c.context_type in industrial_types),
            None,
        )
        if facility_ev:
            features_dict["facility_distance_meters"] = (
                facility_ev.distance_to_event_meters
            )
            features_dict["facility_context_type"] = facility_ev.context_type.value
            features_dict["is_near_industrial_facility"] = (
                facility_ev.distance_to_event_meters is not None
                and facility_ev.distance_to_event_meters <= 2500.0
            )
        else:
            features_dict["facility_distance_meters"] = None
            features_dict["facility_context_type"] = "NONE"
            features_dict["is_near_industrial_facility"] = False

        power_ev = next(
            (c for c in valid_context if c.context_type == ContextType.POWER),
            None,
        )
        features_dict["power_plant_distance_meters"] = (
            power_ev.distance_to_event_meters if power_ev else None
        )

        land_ev = next(
            (
                c
                for c in valid_context
                if c.context_type
                in (ContextType.FOREST_VEGETATION, ContextType.AGRICULTURAL)
            ),
            None,
        )
        if land_ev and land_ev.raw_metadata:
            features_dict["landcover_class"] = land_ev.raw_metadata.get(
                "class", land_ev.context_type.value
            )
        elif land_ev:
            features_dict["landcover_class"] = land_ev.context_type.value
        else:
            features_dict["landcover_class"] = "UNKNOWN"

        features_dict["is_protected_area"] = any(
            c.context_type == ContextType.FOREST_VEGETATION for c in valid_context
        )

        water_ev = next(
            (
                c
                for c in valid_context
                if c.context_type == ContextType.OTHER and c.source_type == "water"
            ),
            None,
        )
        features_dict["water_distance_meters"] = (
            water_ev.distance_to_event_meters if water_ev else None
        )

        # 3. Filter by allowed_feature_names if specified
        if allowed_feature_names is not None:
            allowed_set = set(allowed_feature_names)
            filtered_dict = {k: v for k, v in features_dict.items() if k in allowed_set}
        else:
            filtered_dict = features_dict

        # 4. Generate Missingness Indicator Flags
        missingness_flags: dict[str, bool] = {
            f"{k}_is_missing": (v is None) for k, v in filtered_dict.items()
        }

        # 5. Build FeatureRecord
        return FeatureRecord(
            entity_id=event.event_id,
            prediction_unit=TargetUnit.EVENT,
            as_of_time=as_of_time,
            event_id=event.event_id,
            source_id=source.source_id if source else None,
            features=filtered_dict,
            missingness_flags=missingness_flags,
            provenance=provenance,
        )
