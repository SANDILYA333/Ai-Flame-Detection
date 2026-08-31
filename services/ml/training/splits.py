"""Split assignment service and split integrity validator for Phase 4 ML (ML-008).

Implements grouped event, persistent-source, facility, spatial block, temporal,
and source/sensor holdout strategies, preventing cross-partition leakage and
ensuring honest generalization benchmarks.
"""

import hashlib
import math
from datetime import datetime
from typing import Any

from packages.schemas.ml import (
    SplitAssignment,
    SplitIntegrityReport,
    SplitPartition,
    SplitStrategy,
)


class SplitAssignmentService:
    """Service providing grouped, temporal, spatial, and sensor split assignment."""

    @staticmethod
    def assign_grouped_event_split(
        records: list[dict[str, Any]],
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        random_seed: int = 42,
        isolated_showcase_ids: list[str] | None = None,
    ) -> list[SplitAssignment]:
        """Assign samples to partitions grouped strictly by event_id."""
        isolated_set = set(isolated_showcase_ids or [])
        assignments: list[SplitAssignment] = []

        events_to_records: dict[str, list[dict[str, Any]]] = {}
        for r in records:
            eid = str(r.get("entity_id") or r.get("id", ""))
            if eid in isolated_set:
                assignments.append(
                    SplitAssignment(
                        entity_id=eid,
                        partition=SplitPartition.SHOWCASE_ISOLATION,
                        event_id=r.get("event_id"),
                        source_id=r.get("source_id"),
                        facility_id=r.get("facility_id"),
                        split_key="showcase_isolation",
                        assignment_reason="Quarantined showcase entity (DATASET-003)",
                    )
                )
                continue

            event_id = str(r.get("event_id") or eid)
            events_to_records.setdefault(event_id, []).append(r)

        for event_id, event_records in sorted(events_to_records.items()):
            hash_input = f"{random_seed}:event:{event_id}".encode()
            hash_val = int(hashlib.sha256(hash_input).hexdigest()[:8], 16)
            score = hash_val / 0xFFFFFFFF

            if score < train_ratio:
                partition = SplitPartition.TRAIN
            elif score < train_ratio + val_ratio:
                partition = SplitPartition.VALIDATION
            else:
                partition = SplitPartition.TEST

            for r in event_records:
                eid = str(r.get("entity_id") or r.get("id", ""))
                assignments.append(
                    SplitAssignment(
                        entity_id=eid,
                        partition=partition,
                        event_id=r.get("event_id"),
                        source_id=r.get("source_id"),
                        facility_id=r.get("facility_id"),
                        split_key=f"event:{event_id}",
                        assignment_reason=f"Grouped event hash score={score:.4f}",
                    )
                )

        return assignments

    @staticmethod
    def assign_grouped_source_split(
        records: list[dict[str, Any]],
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        random_seed: int = 42,
        isolated_showcase_ids: list[str] | None = None,
    ) -> list[SplitAssignment]:
        """Assign samples to partitions grouped strictly by source_id."""
        isolated_set = set(isolated_showcase_ids or [])
        assignments: list[SplitAssignment] = []

        sources_to_records: dict[str, list[dict[str, Any]]] = {}
        for r in records:
            eid = str(r.get("entity_id") or r.get("id", ""))
            if eid in isolated_set:
                assignments.append(
                    SplitAssignment(
                        entity_id=eid,
                        partition=SplitPartition.SHOWCASE_ISOLATION,
                        event_id=r.get("event_id"),
                        source_id=r.get("source_id"),
                        facility_id=r.get("facility_id"),
                        split_key="showcase_isolation",
                        assignment_reason="Quarantined showcase entity (DATASET-003)",
                    )
                )
                continue

            source_id = str(r.get("source_id") or r.get("event_id") or eid)
            sources_to_records.setdefault(source_id, []).append(r)

        for source_id, source_records in sorted(sources_to_records.items()):
            hash_input = f"{random_seed}:source:{source_id}".encode()
            hash_val = int(hashlib.sha256(hash_input).hexdigest()[:8], 16)
            score = hash_val / 0xFFFFFFFF

            if score < train_ratio:
                partition = SplitPartition.TRAIN
            elif score < train_ratio + val_ratio:
                partition = SplitPartition.VALIDATION
            else:
                partition = SplitPartition.TEST

            for r in source_records:
                eid = str(r.get("entity_id") or r.get("id", ""))
                assignments.append(
                    SplitAssignment(
                        entity_id=eid,
                        partition=partition,
                        event_id=r.get("event_id"),
                        source_id=r.get("source_id"),
                        facility_id=r.get("facility_id"),
                        split_key=f"source:{source_id}",
                        assignment_reason=f"Grouped source hash score={score:.4f}",
                    )
                )

        return assignments

    @staticmethod
    def assign_facility_holdout_split(
        records: list[dict[str, Any]],
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        random_seed: int = 42,
        isolated_showcase_ids: list[str] | None = None,
    ) -> list[SplitAssignment]:
        """Assign samples grouped strictly by facility_id."""
        isolated_set = set(isolated_showcase_ids or [])
        assignments: list[SplitAssignment] = []

        facilities_to_records: dict[str, list[dict[str, Any]]] = {}
        for r in records:
            eid = str(r.get("entity_id") or r.get("id", ""))
            if eid in isolated_set:
                assignments.append(
                    SplitAssignment(
                        entity_id=eid,
                        partition=SplitPartition.SHOWCASE_ISOLATION,
                        event_id=r.get("event_id"),
                        source_id=r.get("source_id"),
                        facility_id=r.get("facility_id"),
                        split_key="showcase_isolation",
                        assignment_reason="Quarantined showcase entity (DATASET-003)",
                    )
                )
                continue

            facility_id = str(
                r.get("facility_id")
                or r.get("facility_context_type")
                or r.get("source_id")
                or r.get("event_id")
                or eid
            )
            facilities_to_records.setdefault(facility_id, []).append(r)

        for facility_id, facility_records in sorted(facilities_to_records.items()):
            hash_input = f"{random_seed}:facility:{facility_id}".encode()
            hash_val = int(hashlib.sha256(hash_input).hexdigest()[:8], 16)
            score = hash_val / 0xFFFFFFFF

            if score < train_ratio:
                partition = SplitPartition.TRAIN
            elif score < train_ratio + val_ratio:
                partition = SplitPartition.VALIDATION
            else:
                partition = SplitPartition.TEST

            for r in facility_records:
                eid = str(r.get("entity_id") or r.get("id", ""))
                assignments.append(
                    SplitAssignment(
                        entity_id=eid,
                        partition=partition,
                        event_id=r.get("event_id"),
                        source_id=r.get("source_id"),
                        facility_id=r.get("facility_id") or facility_id,
                        split_key=f"facility:{facility_id}",
                        assignment_reason=f"Grouped facility hash score={score:.4f}",
                    )
                )

        return assignments

    @staticmethod
    def assign_spatial_block_split(
        records: list[dict[str, Any]],
        block_size_degrees: float = 0.25,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        random_seed: int = 42,
        isolated_showcase_ids: list[str] | None = None,
    ) -> list[SplitAssignment]:
        """Assign samples to partitions grouped strictly by geographic grid blocks."""
        isolated_set = set(isolated_showcase_ids or [])
        assignments: list[SplitAssignment] = []

        blocks_to_records: dict[str, list[dict[str, Any]]] = {}
        for r in records:
            eid = str(r.get("entity_id") or r.get("id", ""))
            if eid in isolated_set:
                assignments.append(
                    SplitAssignment(
                        entity_id=eid,
                        partition=SplitPartition.SHOWCASE_ISOLATION,
                        event_id=r.get("event_id"),
                        source_id=r.get("source_id"),
                        facility_id=r.get("facility_id"),
                        split_key="showcase_isolation",
                        assignment_reason="Quarantined showcase entity (DATASET-003)",
                    )
                )
                continue

            lat = float(r.get("latitude", 22.0))
            lon = float(r.get("longitude", 70.0))

            b_lat = math.floor(lat / block_size_degrees) * block_size_degrees
            b_lon = math.floor(lon / block_size_degrees) * block_size_degrees
            block_id = f"block_{b_lat:.3f}_{b_lon:.3f}"

            blocks_to_records.setdefault(block_id, []).append(r)

        for block_id, block_records in sorted(blocks_to_records.items()):
            hash_input = f"{random_seed}:spatial_block:{block_id}".encode()
            hash_val = int(hashlib.sha256(hash_input).hexdigest()[:8], 16)
            score = hash_val / 0xFFFFFFFF

            if score < train_ratio:
                partition = SplitPartition.TRAIN
            elif score < train_ratio + val_ratio:
                partition = SplitPartition.VALIDATION
            else:
                partition = SplitPartition.TEST

            for r in block_records:
                eid = str(r.get("entity_id") or r.get("id", ""))
                assignments.append(
                    SplitAssignment(
                        entity_id=eid,
                        partition=partition,
                        event_id=r.get("event_id"),
                        source_id=r.get("source_id"),
                        facility_id=r.get("facility_id"),
                        spatial_block_id=block_id,
                        split_key=f"spatial_block:{block_id}",
                        assignment_reason=f"Spatial block hash score={score:.4f}",
                    )
                )

        return assignments

    @staticmethod
    def assign_temporal_holdout_split(
        records: list[dict[str, Any]],
        val_cutoff: datetime,
        test_cutoff: datetime,
        isolated_showcase_ids: list[str] | None = None,
    ) -> list[SplitAssignment]:
        """Assign samples chronologically into train, val, and test partitions."""
        isolated_set = set(isolated_showcase_ids or [])
        assignments: list[SplitAssignment] = []

        for r in records:
            eid = str(r.get("entity_id") or r.get("id", ""))
            if eid in isolated_set:
                assignments.append(
                    SplitAssignment(
                        entity_id=eid,
                        partition=SplitPartition.SHOWCASE_ISOLATION,
                        event_id=r.get("event_id"),
                        source_id=r.get("source_id"),
                        facility_id=r.get("facility_id"),
                        split_key="showcase_isolation",
                        assignment_reason="Quarantined showcase entity (DATASET-003)",
                    )
                )
                continue

            ts = r.get("acquisition_time") or r.get("timestamp") or r.get("created_at")
            if ts is None:
                raise ValueError(
                    f"Record '{eid}' lacks a valid timestamp for temporal split."
                )

            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts)

            if ts < val_cutoff:
                partition = SplitPartition.TRAIN
                split_key = f"temporal:train:<{val_cutoff.isoformat()}"
                reason = f"Timestamp ({ts.isoformat()}) before val cutoff"
            elif ts < test_cutoff:
                partition = SplitPartition.VALIDATION
                split_key = (
                    f"temporal:val:{val_cutoff.isoformat()}-{test_cutoff.isoformat()}"
                )
                reason = f"Timestamp ({ts.isoformat()}) in validation interval"
            else:
                partition = SplitPartition.TEST
                split_key = f"temporal:test:>={test_cutoff.isoformat()}"
                reason = f"Timestamp ({ts.isoformat()}) after test cutoff"

            assignments.append(
                SplitAssignment(
                    entity_id=eid,
                    partition=partition,
                    event_id=r.get("event_id"),
                    source_id=r.get("source_id"),
                    facility_id=r.get("facility_id"),
                    split_key=split_key,
                    assignment_reason=reason,
                )
            )

        return assignments

    @staticmethod
    def assign_source_sensor_split(
        records: list[dict[str, Any]],
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        random_seed: int = 42,
        isolated_showcase_ids: list[str] | None = None,
    ) -> list[SplitAssignment]:
        """Assign samples to partitions grouped by sensor/satellite platform."""
        isolated_set = set(isolated_showcase_ids or [])
        assignments: list[SplitAssignment] = []

        sensors_to_records: dict[str, list[dict[str, Any]]] = {}
        for r in records:
            eid = str(r.get("entity_id") or r.get("id", ""))
            if eid in isolated_set:
                assignments.append(
                    SplitAssignment(
                        entity_id=eid,
                        partition=SplitPartition.SHOWCASE_ISOLATION,
                        event_id=r.get("event_id"),
                        source_id=r.get("source_id"),
                        facility_id=r.get("facility_id"),
                        split_key="showcase_isolation",
                        assignment_reason="Quarantined showcase entity (DATASET-003)",
                    )
                )
                continue

            sensor_id = str(
                r.get("sensor_id")
                or r.get("sensor_instrument")
                or r.get("satellite")
                or "VIIRS"
            )
            sensors_to_records.setdefault(sensor_id, []).append(r)

        for sensor_id, sensor_records in sorted(sensors_to_records.items()):
            hash_input = f"{random_seed}:sensor:{sensor_id}".encode()
            hash_val = int(hashlib.sha256(hash_input).hexdigest()[:8], 16)
            score = hash_val / 0xFFFFFFFF

            if score < train_ratio:
                partition = SplitPartition.TRAIN
            elif score < train_ratio + val_ratio:
                partition = SplitPartition.VALIDATION
            else:
                partition = SplitPartition.TEST

            for r in sensor_records:
                eid = str(r.get("entity_id") or r.get("id", ""))
                assignments.append(
                    SplitAssignment(
                        entity_id=eid,
                        partition=partition,
                        event_id=r.get("event_id"),
                        source_id=r.get("source_id"),
                        facility_id=r.get("facility_id"),
                        sensor_id=sensor_id,
                        split_key=f"sensor:{sensor_id}",
                        assignment_reason=f"Grouped sensor hash score={score:.4f}",
                    )
                )

        return assignments


class SplitIntegrityValidator:
    """Validator auditing partition assignments for group and temporal leakage."""

    @classmethod
    def validate_split_integrity(
        cls,
        assignments: list[SplitAssignment],
        split_strategy: SplitStrategy,
        record_timestamps: dict[str, datetime] | None = None,
    ) -> SplitIntegrityReport:
        """Verify partition independence and produce an audit report."""
        train_count = 0
        val_count = 0
        test_count = 0
        cal_count = 0
        showcase_count = 0

        event_partitions: dict[str, set[SplitPartition]] = {}
        source_partitions: dict[str, set[SplitPartition]] = {}
        facility_partitions: dict[str, set[SplitPartition]] = {}
        spatial_partitions: dict[str, set[SplitPartition]] = {}
        sensor_partitions: dict[str, set[SplitPartition]] = {}

        for a in assignments:
            if a.partition == SplitPartition.TRAIN:
                train_count += 1
            elif a.partition == SplitPartition.VALIDATION:
                val_count += 1
            elif a.partition == SplitPartition.TEST:
                test_count += 1
            elif a.partition == SplitPartition.CALIBRATION:
                cal_count += 1
            elif a.partition == SplitPartition.SHOWCASE_ISOLATION:
                showcase_count += 1

            if a.partition == SplitPartition.SHOWCASE_ISOLATION:
                continue

            if a.event_id:
                event_partitions.setdefault(a.event_id, set()).add(a.partition)

            if a.source_id:
                source_partitions.setdefault(a.source_id, set()).add(a.partition)

            if a.facility_id:
                facility_partitions.setdefault(a.facility_id, set()).add(a.partition)

            if a.spatial_block_id:
                spatial_partitions.setdefault(a.spatial_block_id, set()).add(
                    a.partition
                )

            if a.sensor_id:
                sensor_partitions.setdefault(a.sensor_id, set()).add(a.partition)

        # 1. Event leakage violations
        event_violations = [
            (
                f"Event '{eid}' present in multiple partitions: "
                f"{sorted(p.value for p in parts)}"
            )
            for eid, parts in event_partitions.items()
            if len(parts) > 1
        ]

        # 2. Source leakage violations
        source_violations = [
            f"Source '{sid}' present in both TRAIN and TEST partitions."
            for sid, parts in source_partitions.items()
            if SplitPartition.TRAIN in parts and SplitPartition.TEST in parts
        ]

        # 3. Facility leakage violations
        facility_violations = [
            (
                f"Facility '{fid}' present in multiple partitions: "
                f"{sorted(p.value for p in parts)}"
            )
            for fid, parts in facility_partitions.items()
            if len(parts) > 1
        ]

        # 4. Spatial block leakage violations
        spatial_violations = [
            (
                f"Spatial block '{bid}' present in multiple partitions: "
                f"{sorted(p.value for p in parts)}"
            )
            for bid, parts in spatial_partitions.items()
            if len(parts) > 1
        ]

        # 5. Sensor leakage violations
        sensor_violations = [
            (
                f"Sensor '{sid}' present in multiple partitions: "
                f"{sorted(p.value for p in parts)}"
            )
            for sid, parts in sensor_partitions.items()
            if len(parts) > 1
        ]

        # 6. Temporal inversion violations
        temporal_violations: list[str] = []
        if record_timestamps and split_strategy == SplitStrategy.TEMPORAL_HOLDOUT:
            train_times = [
                record_timestamps[a.entity_id]
                for a in assignments
                if a.partition == SplitPartition.TRAIN
                and a.entity_id in record_timestamps
            ]
            test_times = [
                record_timestamps[a.entity_id]
                for a in assignments
                if a.partition == SplitPartition.TEST
                and a.entity_id in record_timestamps
            ]
            if train_times and test_times:
                max_train = max(train_times)
                min_test = min(test_times)
                if max_train > min_test:
                    temporal_violations.append(
                        f"Temporal inversion: latest train ({max_train.isoformat()}) "
                        f"is after earliest test ({min_test.isoformat()})."
                    )

        # Invariant checks per strategy
        is_valid = len(event_violations) == 0 and len(temporal_violations) == 0

        if (
            split_strategy
            in (
                SplitStrategy.PERSISTENT_SOURCE_HOLDOUT,
                SplitStrategy.SPATIO_TEMPORAL_SOURCE_GROUPED,
            )
            and len(source_violations) > 0
        ):
            is_valid = False

        if (
            split_strategy == SplitStrategy.FACILITY_HOLDOUT
            and len(facility_violations) > 0
        ):
            is_valid = False

        if (
            split_strategy == SplitStrategy.SPATIAL_GEOGRAPHIC_HOLDOUT
            and len(spatial_violations) > 0
        ):
            is_valid = False

        if (
            split_strategy == SplitStrategy.SOURCE_SENSOR_HOLDOUT
            and len(sensor_violations) > 0
        ):
            is_valid = False

        return SplitIntegrityReport(
            is_valid=is_valid,
            split_strategy=split_strategy,
            train_count=train_count,
            validation_count=val_count,
            test_count=test_count,
            calibration_count=cal_count,
            isolated_showcase_count=showcase_count,
            event_leakage_violations=event_violations,
            source_leakage_violations=source_violations,
            facility_leakage_violations=facility_violations,
            spatial_leakage_violations=spatial_violations,
            sensor_leakage_violations=sensor_violations,
            temporal_inversion_violations=temporal_violations,
        )
