"""Unit tests for dataset manifest building, determinism, and split integrity."""

import random
from datetime import UTC, datetime, timedelta

from packages.schemas.ml import (
    SplitAssignment,
    SplitPartition,
    SplitStrategy,
)
from services.ml.training.dataset import DatasetBuilder
from services.ml.training.splits import (
    SplitAssignmentService,
    SplitIntegrityValidator,
)


class TestMLSplitsAndDataset:
    """Test suite validating dataset manifest hashing and split integrity."""

    def test_dataset_manifest_hash_determinism_across_reordering(self) -> None:
        """Hash generation is deterministic and invariant to input record order."""
        t_base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        records = [
            {
                "entity_id": f"rec_{i:03d}",
                "val": i * 1.5,
                "timestamp": t_base + timedelta(hours=i),
            }
            for i in range(50)
        ]

        hash_1 = DatasetBuilder.compute_records_hash(records)

        # Shuffle records
        shuffled = list(records)
        random.seed(12345)
        random.shuffle(shuffled)

        hash_2 = DatasetBuilder.compute_records_hash(shuffled)

        assert hash_1 == hash_2
        assert len(hash_1) == 64

    def test_duplicate_auditing(self) -> None:
        """DatasetBuilder detects duplicate entity IDs and space-time collisions."""
        t1 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        records = [
            {
                "entity_id": "rec_001",
                "latitude": 22.45,
                "longitude": 69.80,
                "timestamp": t1,
            },
            {
                "entity_id": "rec_002",
                "latitude": 22.50,
                "longitude": 69.85,
                "timestamp": t1,
            },
            {
                "entity_id": "rec_001",
                "latitude": 22.45,
                "longitude": 69.80,
                "timestamp": t1,
            },  # Dup ID
            {
                "entity_id": "rec_003",
                "latitude": 22.50,
                "longitude": 69.85,
                "timestamp": t1,
            },  # Dup spacetime
        ]

        violations = DatasetBuilder.audit_duplicates(records)
        assert len(violations) >= 2
        dup_types = [v.duplicate_type for v in violations]
        assert "DUPLICATE_ENTITY_ID" in dup_types
        assert "SPACETIME_COLLISION" in dup_types

    def test_showcase_isolation_in_dataset_manifest(self) -> None:
        """Showcase events are excluded from training dataset manifest."""
        t_start = datetime(2026, 1, 1, tzinfo=UTC)
        t_end = datetime(2026, 6, 1, tzinfo=UTC)
        records = [
            {"entity_id": "rec_001", "val": 1.0},
            {"entity_id": "rec_002", "val": 2.0},
            {"entity_id": "showcase_001", "val": 99.0},
        ]

        manifest = DatasetBuilder.build_manifest(
            dataset_id="ds_jamnagar_v1",
            dataset_version="v1.0.0",
            target_id="target_phenomenon_v1",
            feature_set_version="feat_v1",
            label_set_version="lbl_v1",
            geographic_scope="jamnagar_kutch",
            temporal_start=t_start,
            temporal_end=t_end,
            split_strategy=SplitStrategy.GROUPED_EVENT_HOLDOUT,
            records=records,
            isolated_showcase_ids=["showcase_001"],
        )

        assert manifest.record_count == 2

    def test_grouped_event_split_prevents_event_leakage(self) -> None:
        """Grouped event splitting assigns event records to single partition."""
        records = []
        for event_idx in range(20):
            for rec_idx in range(4):
                records.append(
                    {
                        "entity_id": f"det_e{event_idx:02d}_r{rec_idx}",
                        "event_id": f"evt_{event_idx:02d}",
                        "source_id": f"src_{event_idx // 2:02d}",
                    }
                )

        assignments = SplitAssignmentService.assign_grouped_event_split(
            records=records,
            train_ratio=0.70,
            val_ratio=0.15,
            test_ratio=0.15,
            random_seed=42,
        )

        report = SplitIntegrityValidator.validate_split_integrity(
            assignments=assignments,
            split_strategy=SplitStrategy.GROUPED_EVENT_HOLDOUT,
        )

        assert report.is_valid is True
        assert len(report.event_leakage_violations) == 0
        assert report.train_count > 0
        assert report.validation_count > 0
        assert report.test_count > 0

    def test_split_integrity_detects_leakage_violations(self) -> None:
        """SplitIntegrityValidator detects cross-partition event contamination."""
        bad_assignments = [
            # Event 1 leaked between TRAIN and TEST
            SplitAssignment(
                entity_id="det_1",
                partition=SplitPartition.TRAIN,
                event_id="evt_01",
                source_id="src_01",
                split_key="bad",
            ),
            SplitAssignment(
                entity_id="det_2",
                partition=SplitPartition.TEST,
                event_id="evt_01",  # Same event in TEST
                source_id="src_01",
                split_key="bad",
            ),
            # Event 2 clean in TRAIN
            SplitAssignment(
                entity_id="det_3",
                partition=SplitPartition.TRAIN,
                event_id="evt_02",
                source_id="src_02",
                split_key="bad",
            ),
        ]

        report = SplitIntegrityValidator.validate_split_integrity(
            assignments=bad_assignments,
            split_strategy=SplitStrategy.GROUPED_EVENT_HOLDOUT,
        )

        assert report.is_valid is False
        assert len(report.event_leakage_violations) == 1
        assert "evt_01" in report.event_leakage_violations[0]
