"""Split assignment service and split integrity validator for Phase 4 ML.

Implements grouped, temporal, spatial, and persistent-source holdout strategies,
preventing cross-partition event leakage and ensuring honest evaluation.
"""

import hashlib
from datetime import datetime
from typing import Any

from packages.schemas.ml import (
    SplitAssignment,
    SplitIntegrityReport,
    SplitPartition,
    SplitStrategy,
)


class SplitAssignmentService:
    """Service providing grouped, temporal, and spatial partition assignment."""

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
                        split_key="showcase_isolation",
                    )
                )
                continue

            event_id = str(r.get("event_id") or eid)
            if event_id not in events_to_records:
                events_to_records[event_id] = []
            events_to_records[event_id].append(r)

        for event_id, event_records in sorted(events_to_records.items()):
            hash_input = f"{random_seed}:{event_id}".encode()
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
                        split_key=f"event:{event_id}",
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
                        split_key="showcase_isolation",
                    )
                )
                continue

            source_id = str(r.get("source_id") or r.get("event_id") or eid)
            if source_id not in sources_to_records:
                sources_to_records[source_id] = []
            sources_to_records[source_id].append(r)

        for source_id, source_records in sorted(sources_to_records.items()):
            hash_input = f"{random_seed}:{source_id}".encode()
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
                        split_key=f"source:{source_id}",
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
        """Assign samples into past (train), intermediate (val), and future (test)."""
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
                        split_key="showcase_isolation",
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
            elif ts < test_cutoff:
                partition = SplitPartition.VALIDATION
                split_key = (
                    f"temporal:val:{val_cutoff.isoformat()}-{test_cutoff.isoformat()}"
                )
            else:
                partition = SplitPartition.TEST
                split_key = f"temporal:test:>={test_cutoff.isoformat()}"

            assignments.append(
                SplitAssignment(
                    entity_id=eid,
                    partition=partition,
                    event_id=r.get("event_id"),
                    source_id=r.get("source_id"),
                    split_key=split_key,
                )
            )

        return assignments


class SplitIntegrityValidator:
    """Validator auditing partition assignments for group/spatial/temporal leakage."""

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
                if a.event_id not in event_partitions:
                    event_partitions[a.event_id] = set()
                event_partitions[a.event_id].add(a.partition)

            if a.source_id:
                if a.source_id not in source_partitions:
                    source_partitions[a.source_id] = set()
                source_partitions[a.source_id].add(a.partition)

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

        # 3. Temporal inversion violations
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
            temporal_inversion_violations=temporal_violations,
        )
