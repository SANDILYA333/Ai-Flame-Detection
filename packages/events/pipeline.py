"""Real-World Thermal Event Construction & Persistent Source Tracking Service (ML-011).

Provides a deterministic pipeline converting canonical remote-sensing Detection
datasets (from ML-010) into spatiotemporally clustered Event domain objects,
tracks longitudinal Persistent Thermal Sources, and guarantees point-in-time
temporal integrity without future leakage.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from packages.config.scientific import ScientificConfig
from packages.events.service import derive_thermal_events
from packages.schemas.common import BoundingBox
from packages.schemas.event import Event, RealThermalEventDataset
from packages.sources.service import derive_persistent_sources

if TYPE_CHECKING:
    from collections.abc import Sequence

    from packages.data.firms.schemas import RealDetectionDataset
    from packages.feasibility.models import StudyArea
    from packages.schemas.detection import Detection
    from packages.schemas.source import PersistentSource

SENSITIVE_KEY_PATTERNS = (
    "map_key",
    "token",
    "secret",
    "password",
    "api_key",
    "credential",
    "private_key",
    "authorization",
)


def _audit_no_secrets(obj: Any, path: str = "") -> None:
    """Recursively verify no credentials or map keys exist in metadata."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            k_lower = str(k).lower()
            for pattern in SENSITIVE_KEY_PATTERNS:
                if pattern in k_lower:
                    raise ValueError(
                        f"Prohibited sensitive key '{k}' found at path '{path}.{k}'"
                    )
            _audit_no_secrets(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _audit_no_secrets(item, f"{path}[{i}]")
    elif isinstance(obj, str):
        lower_str = obj.lower()
        if "bearer " in lower_str or "firms_map_key" in lower_str:
            raise ValueError(
                f"Prohibited credential token detected in value at '{path}'"
            )


def get_default_calibrated_scientific_config(
    version: str = "v1.0.0-pilot",
    name: str = "pilot_jamnagar_flaring",
) -> ScientificConfig:
    """Provide standard calibrated ScientificConfig profile for pilot execution."""
    return ScientificConfig(
        version=version,
        name=name,
        description="Calibrated pilot configuration for industrial fire segregation",
        spatial_cluster_radius_meters=1000.0,  # 1.0 km spatial clustering
        temporal_window_hours=2.0,  # 2.0 hour episode clustering
        persistence_threshold_days=30.0,  # 30 day longitudinal threshold
        persistence_min_observations=5,  # 5 active days / events for persistence
        attribution_radius_meters=1500.0,
        attribution_confidence_threshold=0.7,
        minimum_event_confidence=0.5,
        abstention_confidence_threshold=0.4,
    )


class RealEventConstructionService:
    """Service orchestrating real event clustering and persistent source tracking."""

    @classmethod
    def construct_events_and_sources(
        cls,
        detection_dataset: RealDetectionDataset | None = None,
        detections: Sequence[Detection] | None = None,
        config: ScientificConfig | None = None,
        study_area: StudyArea | None = None,
        dataset_id: str = "ds_real_events_v1.0.0",
        dataset_version: str = "v1.0.0",
    ) -> RealThermalEventDataset:
        """Derive thermal events and persistent sources from canonical detections."""
        now = datetime.now(UTC)
        active_config = config or get_default_calibrated_scientific_config()
        active_config.validate_completeness()

        # 1. Resolve detections and metadata
        input_detections: list[Detection]
        det_dataset_id: str
        det_dataset_hash: str
        study_area_id: str
        study_area_name: str
        bounding_box: BoundingBox

        if detection_dataset is not None:
            input_detections = list(detection_dataset.detections)
            det_dataset_id = detection_dataset.manifest.dataset_id
            det_dataset_hash = detection_dataset.manifest.canonical_dataset_hash
            study_area_id = detection_dataset.manifest.study_area_id
            study_area_name = detection_dataset.manifest.study_area_name
            bounding_box = detection_dataset.manifest.bounding_box
        elif detections is not None:
            input_detections = list(detections)
            det_dataset_id = "ds_detection_input"
            det_dataset_hash = "0" * 64
            if study_area is not None:
                study_area_id = study_area.area_id
                study_area_name = study_area.name
                bounding_box = study_area.bounding_box
            else:
                study_area_id = "custom_area"
                study_area_name = "Custom Area"
                lats = [d.geometry.latitude for d in input_detections] or [0.0]
                lons = [d.geometry.longitude for d in input_detections] or [0.0]
                bounding_box = BoundingBox(
                    min_latitude=min(lats),
                    max_latitude=max(lats),
                    min_longitude=min(lons),
                    max_longitude=max(lons),
                )
        else:
            raise ValueError(
                "Either detection_dataset or detections sequence must be provided."
            )

        # 2. Derive canonical thermal events
        events = derive_thermal_events(
            detections=input_detections,
            config=active_config,
            formation_run_id=f"run_{dataset_id}",
        )

        # Sort events deterministically
        events.sort(
            key=lambda e: (
                e.started_at.isoformat(),
                e.centroid_geometry.latitude,
                e.centroid_geometry.longitude,
                e.event_id,
            )
        )

        # 3. Derive canonical persistent sources
        sources = derive_persistent_sources(
            events=events,
            config=active_config,
            persistence_run_id=f"run_{dataset_id}",
        )

        # Sort sources deterministically
        sources.sort(
            key=lambda s: (
                s.first_seen_at.isoformat(),
                s.centroid_geometry.latitude,
                s.centroid_geometry.longitude,
                s.source_id,
            )
        )

        # 4. Construct dataset container
        assert active_config.spatial_cluster_radius_meters is not None
        assert active_config.temporal_window_hours is not None

        temp_dataset = RealThermalEventDataset(
            dataset_id=dataset_id,
            dataset_version=dataset_version,
            detection_dataset_id=det_dataset_id,
            detection_dataset_hash=det_dataset_hash,
            study_area_id=study_area_id,
            study_area_name=study_area_name,
            bounding_box=bounding_box,
            events=events,
            persistent_sources=sources,
            config_fingerprint=active_config.compute_fingerprint(),
            spatial_cluster_radius_meters=active_config.spatial_cluster_radius_meters,
            temporal_window_hours=active_config.temporal_window_hours,
            persistent_source_radius_meters=active_config.spatial_cluster_radius_meters,
            event_count=len(events),
            persistent_source_count=len(sources),
            canonical_dataset_hash="0" * 64,
            created_at=now,
        )

        canonical_hash = temp_dataset.compute_canonical_hash()
        final_dataset = temp_dataset.model_copy(
            update={"canonical_dataset_hash": canonical_hash}
        )

        # 5. Audit against secrets
        _audit_no_secrets(final_dataset.model_dump(mode="json"))

        return final_dataset

    @classmethod
    def construct_point_in_time_events(
        cls,
        detections: Sequence[Detection],
        as_of_time: datetime,
        config: ScientificConfig | None = None,
    ) -> list[Event]:
        """Derive thermal events known strictly as of a cutoff timestamp (anti-leakage).

        Detections with acquired_at > as_of_time are strictly excluded from event
        membership, duration, centroid calculations, and FRP aggregations.
        """
        active_config = config or get_default_calibrated_scientific_config()
        active_config.validate_completeness()

        # Strict point-in-time filtering: t_detection <= as_of_time
        available_detections = [d for d in detections if d.acquired_at <= as_of_time]

        return derive_thermal_events(
            detections=available_detections,
            config=active_config,
            formation_run_id=f"pit_{as_of_time.isoformat()}",
        )

    @classmethod
    def get_point_in_time_source_history(
        cls,
        events: Sequence[Event],
        as_of_time: datetime,
        config: ScientificConfig | None = None,
    ) -> list[PersistentSource]:
        """Derive persistent source state strictly known as of a cutoff timestamp.

        Events with ended_at > as_of_time are strictly excluded from source
        recurrence metrics, active calendar day counts, and persistence state.
        """
        active_config = config or get_default_calibrated_scientific_config()
        active_config.validate_completeness()

        # Strict point-in-time filtering: event.ended_at <= as_of_time
        available_events = [e for e in events if e.ended_at <= as_of_time]

        return derive_persistent_sources(
            events=available_events,
            config=active_config,
            persistence_run_id=f"pit_src_{as_of_time.isoformat()}",
        )

    @classmethod
    def save_dataset(
        cls,
        dataset: RealThermalEventDataset,
        output_dir: Path | str,
    ) -> Path:
        """Save canonical thermal event dataset to filesystem with secret auditing."""
        dir_path = Path(output_dir)
        dir_path.mkdir(parents=True, exist_ok=True)

        data = dataset.model_dump(mode="json")
        _audit_no_secrets(data)

        out_file = dir_path / f"{dataset.dataset_id}.json"
        json_str = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=True)
        out_file.write_text(json_str, encoding="utf-8")
        return out_file

    @classmethod
    def load_dataset(
        cls,
        file_path: Path | str,
    ) -> RealThermalEventDataset:
        """Load and verify canonical thermal event dataset from filesystem."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Thermal event dataset not found at {path}")

        json_str = path.read_text(encoding="utf-8")
        data = json.loads(json_str)
        _audit_no_secrets(data)

        dataset = RealThermalEventDataset.model_validate(data)

        # Verify canonical hash integrity
        computed_hash = dataset.compute_canonical_hash()
        if dataset.canonical_dataset_hash != computed_hash:
            raise ValueError(
                f"Thermal event dataset hash mismatch: "
                f"stored={dataset.canonical_dataset_hash}, "
                f"computed={computed_hash}."
            )

        return dataset
