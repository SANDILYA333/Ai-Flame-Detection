"""Comprehensive unit and integration tests for ML-008 Generalization Benchmark.

Validates:
- Event Holdout (GROUPED_EVENT_HOLDOUT)
- Persistent-Source Holdout (PERSISTENT_SOURCE_HOLDOUT)
- Facility Holdout (FACILITY_HOLDOUT)
- Spatial Geographic Block Holdout (SPATIAL_GEOGRAPHIC_HOLDOUT)
- Chronological Temporal Holdout (TEMPORAL_HOLDOUT)
- Source / Sensor Platform Holdout (SOURCE_SENSOR_HOLDOUT)
- Showcase Quarantine (DATASET-003)
- Split Determinism and Preprocessing Isolation
- End-to-End Generalization Matrix Execution
"""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import pytest

from packages.schemas.common import Coordinate
from packages.schemas.detection import Detection
from packages.schemas.enums import DayNight
from packages.schemas.event import Event
from packages.schemas.ml import (
    FeatureDataset,
    LabelDecision,
    LabelProvenanceType,
    LabelTier,
    SplitPartition,
    SplitStrategy,
)
from services.ml.evaluation.generalization import GeneralizationBenchmarkService
from services.ml.features.builder import FeatureDatasetBuilder
from services.ml.labels.dataset import SupervisedDatasetBuilder
from services.ml.training.splits import (
    SplitAssignmentService,
    SplitIntegrityValidator,
)


def _create_detection(
    det_id: str,
    t: datetime,
    lat: float = 22.48,
    lon: float = 70.06,
    frp: float = 35.0,
    sensor: str = "VIIRS",
) -> Detection:
    return Detection(
        detection_id=det_id,
        source="firms",
        source_snapshot_id="snap_1",
        geometry=Coordinate(latitude=lat, longitude=lon),
        acquired_at=t,
        satellite="SNPP" if sensor == "VIIRS" else "AQUA",
        instrument=sensor,
        product_type="nrt",
        product_version="v1.0",
        raw_hash=f"hash_{det_id}",
        frp_mw=frp,
        brightness_ti4_k=350.0,
        confidence="nominal",
        day_night=DayNight.NIGHT,
    )


def _create_event(
    event_id: str,
    det_id: str,
    t: datetime,
    lat: float = 22.48,
    lon: float = 70.06,
) -> Event:
    return Event(
        event_id=event_id,
        detection_ids=[det_id],
        detection_count=1,
        started_at=t,
        ended_at=t,
        centroid_geometry=Coordinate(latitude=lat, longitude=lon),
        formation_configuration_id="cfg_v1",
        formation_configuration_version="v1.0",
    )


@pytest.fixture
def multi_region_feature_dataset() -> tuple[
    FeatureDataset, dict[str, Sequence[LabelDecision]]
]:
    """Create multi-region, multi-source, multi-temporal feature dataset fixture."""
    t0 = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
    event_tuples = []
    labels: list[LabelDecision] = []

    coords = [
        (22.48, 70.06, "facility_jamnagar", "VIIRS"),
        (22.84, 69.72, "facility_mundra", "MODIS"),
        (21.71, 72.58, "facility_dahej", "VIIRS"),
        (21.10, 72.65, "facility_hazira", "MODIS"),
    ]

    for i in range(1, 41):
        c_idx = (i - 1) % 4
        lat, lon, _fac_id, sensor = coords[c_idx]
        eid = f"evt_{i:03d}"
        is_ind = i % 2 == 1
        frp_val = 65.0 if is_ind else 12.0

        t_event = t0 + timedelta(hours=i * 2)
        det = _create_detection(
            f"d_{i:03d}",
            t_event,
            lat=lat,
            lon=lon,
            frp=frp_val,
            sensor=sensor,
        )
        evt = _create_event(eid, f"d_{i:03d}", t_event, lat=lat, lon=lon)
        event_tuples.append(
            (evt, [det], t_event + timedelta(hours=1), None, None, None)
        )

        cls_name = "industrial" if is_ind else "non_industrial"
        labels.append(
            LabelDecision(
                decision_id=f"dec_{eid}",
                target_id="target_industrial_segregation",
                entity_id=eid,
                assigned_class=cls_name,
                label_tier=LabelTier.TIER_A_AUTHORITATIVE,
                provenance_type=LabelProvenanceType.GROUND_TRUTH,
                decision_timestamp=t0,
            )
        )

    builder = FeatureDatasetBuilder()
    feat_ds = builder.extract_and_build_dataset(
        dataset_id="ds_generalization_test",
        dataset_version="v1.0.0",
        target_id="target_industrial_segregation",
        geographic_scope="IND_MULTI_REGION",
        temporal_start=t0,
        temporal_end=t0 + timedelta(days=5),
        split_strategy=SplitStrategy.GROUPED_EVENT_HOLDOUT,
        event_tuples=event_tuples,
    )

    return feat_ds, {"target_industrial_segregation": labels}


class TestML008Generalization:
    """Test suite for ML-008 Holdout Generalization Benchmark."""

    def test_grouped_event_holdout_isolation(
        self,
        multi_region_feature_dataset: tuple[
            FeatureDataset, dict[str, Sequence[LabelDecision]]
        ],
    ) -> None:
        """Event holdout strictly guarantees no event ID crosses partitions."""
        feat_ds, label_map = multi_region_feature_dataset
        builder = SupervisedDatasetBuilder()
        sup_ds = builder.build_supervised_dataset(
            feature_dataset=feat_ds,
            label_decisions_by_target=label_map,
            split_strategy=SplitStrategy.GROUPED_EVENT_HOLDOUT,
            isolated_showcase_ids=["evt_001"],
        )

        tr_events = {
            r.feature_record.event_id
            for r in sup_ds.records
            if r.split_partition == SplitPartition.TRAIN
        }
        va_events = {
            r.feature_record.event_id
            for r in sup_ds.records
            if r.split_partition == SplitPartition.VALIDATION
        }
        te_events = {
            r.feature_record.event_id
            for r in sup_ds.records
            if r.split_partition == SplitPartition.TEST
        }

        assert tr_events.isdisjoint(va_events)
        assert tr_events.isdisjoint(te_events)
        assert va_events.isdisjoint(te_events)
        assert (
            sup_ds.split_manifest.split_strategy == SplitStrategy.GROUPED_EVENT_HOLDOUT
        )

    def test_persistent_source_holdout_isolation(
        self,
        multi_region_feature_dataset: tuple[
            FeatureDataset, dict[str, Sequence[LabelDecision]]
        ],
    ) -> None:
        """Source holdout guarantees no persistent source crosses partitions."""
        feat_ds, label_map = multi_region_feature_dataset
        builder = SupervisedDatasetBuilder()
        sup_ds = builder.build_supervised_dataset(
            feature_dataset=feat_ds,
            label_decisions_by_target=label_map,
            split_strategy=SplitStrategy.PERSISTENT_SOURCE_HOLDOUT,
            isolated_showcase_ids=["evt_001"],
        )

        tr_sources = {
            r.feature_record.source_id
            for r in sup_ds.records
            if r.split_partition == SplitPartition.TRAIN and r.feature_record.source_id
        }
        te_sources = {
            r.feature_record.source_id
            for r in sup_ds.records
            if r.split_partition == SplitPartition.TEST and r.feature_record.source_id
        }

        assert tr_sources.isdisjoint(te_sources)

    def test_facility_holdout_isolation(self) -> None:
        """Facility holdout guarantees no facility ID crosses partitions."""
        records = [
            {
                "entity_id": f"e_{i}",
                "facility_id": f"fac_{i % 3}",
                "event_id": f"e_{i}",
            }
            for i in range(15)
        ]
        assignments = SplitAssignmentService.assign_facility_holdout_split(
            records=records,
            train_ratio=0.60,
            val_ratio=0.20,
            test_ratio=0.20,
            random_seed=42,
        )

        report = SplitIntegrityValidator.validate_split_integrity(
            assignments=assignments,
            split_strategy=SplitStrategy.FACILITY_HOLDOUT,
        )
        assert report.is_valid is True
        assert len(report.facility_leakage_violations) == 0

    def test_spatial_block_holdout_isolation(
        self,
        multi_region_feature_dataset: tuple[
            FeatureDataset, dict[str, Sequence[LabelDecision]]
        ],
    ) -> None:
        """Spatial geographic block holdout guarantees disjoint spatial blocks."""
        feat_ds, label_map = multi_region_feature_dataset
        builder = SupervisedDatasetBuilder()
        sup_ds = builder.build_supervised_dataset(
            feature_dataset=feat_ds,
            label_decisions_by_target=label_map,
            split_strategy=SplitStrategy.SPATIAL_GEOGRAPHIC_HOLDOUT,
            isolated_showcase_ids=["evt_001"],
        )

        assert sup_ds.split_manifest.integrity_report is not None
        assert sup_ds.split_manifest.integrity_report.is_valid is True
        assert (
            sup_ds.split_manifest.split_strategy
            == SplitStrategy.SPATIAL_GEOGRAPHIC_HOLDOUT
        )

    def test_temporal_holdout_chronological_ordering(
        self,
        multi_region_feature_dataset: tuple[
            FeatureDataset, dict[str, Sequence[LabelDecision]]
        ],
    ) -> None:
        """Temporal holdout strictly guarantees max(TRAIN) <= min(TEST)."""
        feat_ds, label_map = multi_region_feature_dataset
        builder = SupervisedDatasetBuilder()
        sup_ds = builder.build_supervised_dataset(
            feature_dataset=feat_ds,
            label_decisions_by_target=label_map,
            split_strategy=SplitStrategy.TEMPORAL_HOLDOUT,
            train_ratio=0.60,
            val_ratio=0.20,
            test_ratio=0.20,
            isolated_showcase_ids=["evt_001"],
        )

        tr_times = [
            r.feature_record.as_of_time
            for r in sup_ds.records
            if r.split_partition == SplitPartition.TRAIN
        ]
        te_times = [
            r.feature_record.as_of_time
            for r in sup_ds.records
            if r.split_partition == SplitPartition.TEST
        ]

        assert max(tr_times) < min(te_times)
        assert sup_ds.split_manifest.integrity_report is not None
        assert sup_ds.split_manifest.integrity_report.is_valid is True

    def test_showcase_quarantine_across_all_strategies(
        self,
        multi_region_feature_dataset: tuple[
            FeatureDataset, dict[str, Sequence[LabelDecision]]
        ],
    ) -> None:
        """Showcase isolated entities (DATASET-003) remain quarantined."""
        feat_ds, label_map = multi_region_feature_dataset
        builder = SupervisedDatasetBuilder()

        strategies = [
            SplitStrategy.GROUPED_EVENT_HOLDOUT,
            SplitStrategy.PERSISTENT_SOURCE_HOLDOUT,
            SplitStrategy.FACILITY_HOLDOUT,
            SplitStrategy.SPATIAL_GEOGRAPHIC_HOLDOUT,
            SplitStrategy.TEMPORAL_HOLDOUT,
            SplitStrategy.SOURCE_SENSOR_HOLDOUT,
        ]

        for strat in strategies:
            sup_ds = builder.build_supervised_dataset(
                feature_dataset=feat_ds,
                label_decisions_by_target=label_map,
                split_strategy=strat,
                isolated_showcase_ids=["evt_001"],
            )

            showcase_rec = next(
                (r for r in sup_ds.records if r.entity_id == "evt_001"), None
            )
            assert showcase_rec is not None
            assert showcase_rec.split_partition == SplitPartition.SHOWCASE_ISOLATION

    def test_end_to_end_generalization_benchmark_execution(
        self,
        multi_region_feature_dataset: tuple[
            FeatureDataset, dict[str, Sequence[LabelDecision]]
        ],
    ) -> None:
        """Benchmark executes cleanly across all strategies and models."""
        feat_ds, label_map = multi_region_feature_dataset

        report = GeneralizationBenchmarkService.run_generalization_benchmark(
            feature_dataset=feat_ds,
            label_decisions_by_target=label_map,
            target_id="target_industrial_segregation",
            model_types=[
                "MajorityClassClassifier",
                "LogisticRegressionClassifier",
                "DecisionTreeClassifier",
                "RandomForestClassifier",
            ],
            random_seed=42,
        )

        assert report.study_id.startswith(
            "generalization_target_industrial_segregation_"
        )
        assert len(report.strategies_evaluated) == 6
        assert len(report.models_evaluated) == 4
        assert len(report.results) == 6 * 4

        # Verify Markdown report generation
        md = GeneralizationBenchmarkService.generate_generalization_summary_markdown(
            report
        )
        assert "# Generalization & Holdout Independence Benchmark" in md
        assert "GROUPED_EVENT_HOLDOUT" in md
        assert "SPATIAL_GEOGRAPHIC_HOLDOUT" in md
        assert "Generalization Gaps" in md
