"""Tests for SupervisedDatasetBuilder, leakage-safe splits, and showcase isolation."""

from datetime import UTC, datetime, timedelta

from packages.schemas.common import Coordinate
from packages.schemas.detection import Detection
from packages.schemas.enums import DayNight, PersistenceState
from packages.schemas.event import Event
from packages.schemas.ml import (
    DatasetRowStatus,
    ExclusionReason,
    LabelDecision,
    LabelProvenanceType,
    LabelTier,
    SplitPartition,
    SplitStrategy,
)
from packages.schemas.source import PersistentSource
from services.ml.features.builder import FeatureDatasetBuilder
from services.ml.labels.dataset import SupervisedDatasetBuilder
from services.ml.labels.reporting import generate_supervised_dataset_report


def _create_detection(
    det_id: str,
    acq_time: datetime,
    lat: float = 22.48,
    lon: float = 70.06,
    frp: float = 25.0,
) -> Detection:
    return Detection(
        detection_id=det_id,
        source="firms",
        source_snapshot_id="snap_20260101",
        geometry=Coordinate(latitude=lat, longitude=lon),
        acquired_at=acq_time,
        satellite="SNPP",
        instrument="VIIRS",
        product_type="nrt",
        product_version="v1.0",
        raw_hash=f"hash_{det_id}",
        frp_mw=frp,
        brightness_ti4_k=330.0,
        confidence="nominal",
        day_night=DayNight.DAY,
    )


def _create_event(
    event_id: str,
    det_ids: list[str],
    start_time: datetime,
    end_time: datetime,
    lat: float = 22.48,
    lon: float = 70.06,
) -> Event:
    return Event(
        event_id=event_id,
        detection_ids=det_ids,
        detection_count=len(det_ids),
        started_at=start_time,
        ended_at=end_time,
        centroid_geometry=Coordinate(latitude=lat, longitude=lon),
        formation_configuration_id="cfg_event_v1",
        formation_configuration_version="v1.0",
    )


class TestMLSupervisedSplitting:
    """Test suite validating leakage-safe supervised splitting."""

    def test_grouped_event_holdout_splitting_integrity(self) -> None:
        """Grouped event splitting assigns partitions without event leakage."""
        t0 = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)

        # Create 6 distinct events
        event_tuples = []
        label_decisions_t1: list[LabelDecision] = []
        label_decisions_t2: list[LabelDecision] = []

        for i in range(1, 7):
            eid = f"evt_{i:03d}"
            det = _create_detection(
                f"d_{i:03d}", t0 + timedelta(hours=i), lat=22.40 + (i * 0.01)
            )
            evt = _create_event(
                eid,
                [f"d_{i:03d}"],
                t0 + timedelta(hours=i),
                t0 + timedelta(hours=i),
                lat=22.40 + (i * 0.01),
            )
            event_tuples.append(
                (
                    evt,
                    [det],
                    t0 + timedelta(hours=i + 1),
                    None,
                    None,
                    None,
                )
            )

            # Add label decisions
            cls_name = "flare" if i % 2 == 0 else "vegetation_wildfire"
            ind_cls = "industrial" if i % 2 == 0 else "non_industrial"

            label_decisions_t1.append(
                LabelDecision(
                    decision_id=f"dec_t1_{eid}",
                    target_id="target_thermal_phenomenon",
                    entity_id=eid,
                    assigned_class=cls_name,
                    label_tier=LabelTier.TIER_A_AUTHORITATIVE,
                    provenance_type=LabelProvenanceType.GROUND_TRUTH,
                    decision_timestamp=t0,
                )
            )
            label_decisions_t2.append(
                LabelDecision(
                    decision_id=f"dec_t2_{eid}",
                    target_id="target_industrial_segregation",
                    entity_id=eid,
                    assigned_class=ind_cls,
                    label_tier=LabelTier.TIER_A_AUTHORITATIVE,
                    provenance_type=LabelProvenanceType.GROUND_TRUTH,
                    decision_timestamp=t0,
                )
            )

        # Build feature dataset
        feat_builder = FeatureDatasetBuilder()
        feat_dataset = feat_builder.extract_and_build_dataset(
            dataset_id="ds_test_supervised",
            dataset_version="v1.0.0",
            target_id="target_thermal_phenomenon",
            geographic_scope="IND_GUJARAT",
            temporal_start=t0,
            temporal_end=t0 + timedelta(days=1),
            split_strategy=SplitStrategy.GROUPED_EVENT_HOLDOUT,
            event_tuples=event_tuples,
        )

        # Build supervised dataset
        sup_builder = SupervisedDatasetBuilder()
        sup_dataset = sup_builder.build_supervised_dataset(
            feature_dataset=feat_dataset,
            label_decisions_by_target={
                "target_thermal_phenomenon": label_decisions_t1,
                "target_industrial_segregation": label_decisions_t2,
            },
            split_strategy=SplitStrategy.GROUPED_EVENT_HOLDOUT,
            train_ratio=0.50,
            val_ratio=0.25,
            test_ratio=0.25,
            random_seed=123,
        )

        manifest = sup_dataset.split_manifest
        assert manifest.integrity_report is not None
        assert manifest.integrity_report.is_valid is True
        assert len(manifest.integrity_report.event_leakage_violations) == 0

        # Verify disjointness
        train_ids = {
            r.entity_id
            for r in sup_dataset.records
            if r.split_partition == SplitPartition.TRAIN
        }
        val_ids = {
            r.entity_id
            for r in sup_dataset.records
            if r.split_partition == SplitPartition.VALIDATION
        }
        test_ids = {
            r.entity_id
            for r in sup_dataset.records
            if r.split_partition == SplitPartition.TEST
        }

        assert len(train_ids & val_ids) == 0
        assert len(train_ids & test_ids) == 0
        assert len(val_ids & test_ids) == 0
        assert len(train_ids) + len(val_ids) + len(test_ids) == 6

    def test_showcase_isolation_records_are_isolated_from_train_val_test(
        self,
    ) -> None:
        """Showcase events (DATASET-003) are assigned SHOWCASE_ISOLATION."""
        t0 = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)

        d1 = _create_detection("d1", t0)
        d2 = _create_detection("d2", t0 + timedelta(hours=1))

        e_reg = _create_event("evt_regular", ["d1"], t0, t0)
        e_show = _create_event(
            "evt_showcase_jamnagar",
            ["d2"],
            t0 + timedelta(hours=1),
            t0 + timedelta(hours=1),
        )

        event_tuples = [
            (e_reg, [d1], t0, None, None, None),
            (e_show, [d2], t0 + timedelta(hours=1), None, None, None),
        ]

        feat_builder = FeatureDatasetBuilder()
        feat_dataset = feat_builder.extract_and_build_dataset(
            dataset_id="ds_showcase_test",
            dataset_version="v1.0.0",
            target_id="target_industrial_segregation",
            geographic_scope="IND_GUJARAT",
            temporal_start=t0,
            temporal_end=t0 + timedelta(days=1),
            split_strategy=SplitStrategy.GROUPED_EVENT_HOLDOUT,
            event_tuples=event_tuples,
        )

        label_dec = LabelDecision(
            decision_id="dec_show",
            target_id="target_industrial_segregation",
            entity_id="evt_showcase_jamnagar",
            assigned_class="industrial",
            label_tier=LabelTier.TIER_A_AUTHORITATIVE,
            provenance_type=LabelProvenanceType.GROUND_TRUTH,
            decision_timestamp=t0,
        )

        sup_builder = SupervisedDatasetBuilder()
        sup_dataset = sup_builder.build_supervised_dataset(
            feature_dataset=feat_dataset,
            label_decisions_by_target={"target_industrial_segregation": [label_dec]},
            split_strategy=SplitStrategy.GROUPED_EVENT_HOLDOUT,
            isolated_showcase_ids=["evt_showcase_jamnagar"],
        )

        showcase_rec = next(
            r for r in sup_dataset.records if r.entity_id == "evt_showcase_jamnagar"
        )
        assert showcase_rec.split_partition == SplitPartition.SHOWCASE_ISOLATION
        assert showcase_rec.row_status == DatasetRowStatus.SHOWCASE_ISOLATED
        assert showcase_rec.exclusion_reason == ExclusionReason.SHOWCASE_ISOLATION
        assert sup_dataset.split_manifest.showcase_count == 1

    def test_source_holdout_splitting_integrity(self) -> None:
        """Source holdout splitting ensures zero source leakage across partitions."""
        t0 = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)

        d1 = _create_detection("d1", t0)
        d2 = _create_detection("d2", t0)
        e1 = _create_event("evt_s1", ["d1"], t0, t0)
        e2 = _create_event("evt_s2", ["d2"], t0, t0)

        src_1 = PersistentSource(
            source_id="src_refinery_a",
            persistence_state=PersistenceState.PERSISTENT,
            linked_event_ids=["evt_s1"],
            total_event_count=1,
            centroid_geometry=Coordinate(latitude=22.48, longitude=70.06),
            first_seen_at=t0,
            last_seen_at=t0,
            active_days_count=1,
            persistence_configuration_id="cfg_v1",
            persistence_configuration_version="v1.0",
        )

        src_2 = PersistentSource(
            source_id="src_power_b",
            persistence_state=PersistenceState.PERSISTENT,
            linked_event_ids=["evt_s2"],
            total_event_count=1,
            centroid_geometry=Coordinate(latitude=22.55, longitude=70.15),
            first_seen_at=t0,
            last_seen_at=t0,
            active_days_count=1,
            persistence_configuration_id="cfg_v1",
            persistence_configuration_version="v1.0",
        )

        event_tuples = [
            (e1, [d1], t0, None, src_1, None),
            (e2, [d2], t0, None, src_2, None),
        ]

        feat_builder = FeatureDatasetBuilder()
        feat_dataset = feat_builder.extract_and_build_dataset(
            dataset_id="ds_source_test",
            dataset_version="v1.0.0",
            target_id="target_persistent_combustion",
            geographic_scope="IND_GUJARAT",
            temporal_start=t0,
            temporal_end=t0 + timedelta(days=1),
            split_strategy=SplitStrategy.PERSISTENT_SOURCE_HOLDOUT,
            event_tuples=event_tuples,
        )

        sup_builder = SupervisedDatasetBuilder()
        sup_dataset = sup_builder.build_supervised_dataset(
            feature_dataset=feat_dataset,
            label_decisions_by_target={},
            split_strategy=SplitStrategy.PERSISTENT_SOURCE_HOLDOUT,
        )

        assert sup_dataset.split_manifest.integrity_report is not None
        assert sup_dataset.split_manifest.integrity_report.is_valid is True
        assert (
            len(sup_dataset.split_manifest.integrity_report.source_leakage_violations)
            == 0
        )

    def test_supervised_dataset_reporting(self) -> None:
        """Reporting utility generates complete quality diagnostics."""
        t0 = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
        d1 = _create_detection("d1", t0)
        e1 = _create_event("evt_rep_01", ["d1"], t0, t0)

        feat_builder = FeatureDatasetBuilder()
        feat_dataset = feat_builder.extract_and_build_dataset(
            dataset_id="ds_report_test",
            dataset_version="v1.0.0",
            target_id="target_industrial_segregation",
            geographic_scope="IND_GUJARAT",
            temporal_start=t0,
            temporal_end=t0 + timedelta(days=1),
            split_strategy=SplitStrategy.GROUPED_EVENT_HOLDOUT,
            event_tuples=[(e1, [d1], t0, None, None, None)],
        )

        label_dec = LabelDecision(
            decision_id="dec_rep",
            target_id="target_industrial_segregation",
            entity_id="evt_rep_01",
            assigned_class="industrial",
            label_tier=LabelTier.TIER_B_STRONG_EVIDENCE,
            provenance_type=LabelProvenanceType.REFERENCE_LABEL,
            decision_timestamp=t0,
        )

        sup_builder = SupervisedDatasetBuilder()
        sup_dataset = sup_builder.build_supervised_dataset(
            feature_dataset=feat_dataset,
            label_decisions_by_target={"target_industrial_segregation": [label_dec]},
        )

        report = generate_supervised_dataset_report(sup_dataset)
        assert report["dataset_id"] == "ds_report_test"
        assert report["record_counts"]["total"] == 1
        assert "class_distributions" in report
        assert "tier_distributions" in report
