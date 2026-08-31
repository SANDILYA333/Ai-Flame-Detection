"""Tests for DatasetSplitExtractor and FeaturePreprocessor."""

from datetime import UTC, datetime, timedelta
from typing import Any

from packages.schemas.common import Coordinate
from packages.schemas.detection import Detection
from packages.schemas.enums import DayNight
from packages.schemas.event import Event
from packages.schemas.ml import (
    LabelDecision,
    LabelProvenanceType,
    LabelTier,
    SplitStrategy,
)
from services.ml.features.builder import FeatureDatasetBuilder
from services.ml.labels.dataset import SupervisedDatasetBuilder
from services.ml.preprocessing.extractor import (
    PROHIBITED_METADATA_COLUMNS,
    DatasetSplitExtractor,
)
from services.ml.preprocessing.transformer import FeaturePreprocessor


def _create_detection(det_id: str, t: datetime) -> Detection:
    return Detection(
        detection_id=det_id,
        source="firms",
        source_snapshot_id="snap_1",
        geometry=Coordinate(latitude=22.48, longitude=70.06),
        acquired_at=t,
        satellite="SNPP",
        instrument="VIIRS",
        product_type="nrt",
        product_version="v1.0",
        raw_hash=f"hash_{det_id}",
        frp_mw=30.0,
        brightness_ti4_k=340.0,
        confidence="nominal",
        day_night=DayNight.DAY,
    )


def _create_event(event_id: str, det_id: str, t: datetime) -> Event:
    return Event(
        event_id=event_id,
        detection_ids=[det_id],
        detection_count=1,
        started_at=t,
        ended_at=t,
        centroid_geometry=Coordinate(latitude=22.48, longitude=70.06),
        formation_configuration_id="cfg_v1",
        formation_configuration_version="v1.0",
    )


class TestMLPreprocessing:
    """Test suite validating leakage-free dataset extraction and preprocessing."""

    def test_dataset_split_extractor_partitions_and_anti_leakage(self) -> None:
        """DatasetSplitExtractor cleanly partitions records and strips IDs."""
        t0 = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)

        event_tuples = []
        label_decisions = []

        for i in range(1, 13):
            eid = f"evt_{i:03d}"
            det = _create_detection(f"d_{i:03d}", t0 + timedelta(hours=i))
            evt = _create_event(eid, f"d_{i:03d}", t0 + timedelta(hours=i))
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

            cls_name = "industrial" if i % 2 == 0 else "non_industrial"
            label_decisions.append(
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

        # Build feature dataset & supervised dataset
        feat_builder = FeatureDatasetBuilder()
        feat_dataset = feat_builder.extract_and_build_dataset(
            dataset_id="ds_prep_test",
            dataset_version="v1.0.0",
            target_id="target_industrial_segregation",
            geographic_scope="IND_GUJARAT",
            temporal_start=t0,
            temporal_end=t0 + timedelta(days=1),
            split_strategy=SplitStrategy.GROUPED_EVENT_HOLDOUT,
            event_tuples=event_tuples,
        )

        sup_builder = SupervisedDatasetBuilder()
        sup_dataset = sup_builder.build_supervised_dataset(
            feature_dataset=feat_dataset,
            label_decisions_by_target={
                "target_industrial_segregation": label_decisions
            },
            train_ratio=0.50,
            val_ratio=0.25,
            test_ratio=0.25,
            random_seed=42,
        )

        # Extract matrices
        (
            x_train,
            _y_train,
            _ids_train,
            x_val,
            _y_val,
            _ids_val,
            x_test,
            _y_test,
            _ids_test,
        ) = DatasetSplitExtractor.extract_split_matrices(
            dataset=sup_dataset,
            target_id="target_industrial_segregation",
        )

        assert len(x_train) > 0
        assert len(x_val) > 0
        assert len(x_test) > 0
        assert len(x_train) + len(x_val) + len(x_test) == 12

        # Verify NO prohibited columns entered feature dicts
        for x_row in x_train + x_val + x_test:
            for prohibited in PROHIBITED_METADATA_COLUMNS:
                assert prohibited not in x_row

    def test_feature_preprocessor_fits_train_only(self) -> None:
        """FeaturePreprocessor computes stats on TRAIN and transforms cleanly."""
        train_data: list[dict[str, Any]] = [
            {"feat_num": 10.0, "feat_cat": "A", "feat_bool": True},
            {"feat_num": 20.0, "feat_cat": "B", "feat_bool": False},
            {"feat_num": 30.0, "feat_cat": "A", "feat_bool": True},
        ]
        val_data: list[dict[str, Any]] = [
            {"feat_num": 20.0, "feat_cat": "A", "feat_bool": True},
            # Missing feat_num and unseen category 'C'
            {"feat_num": None, "feat_cat": "C", "feat_bool": False},
        ]

        prep = FeaturePreprocessor()
        x_train_vec = prep.fit_transform(train_data)

        # Verify fitted statistics
        assert prep.is_fitted is True
        assert prep.numeric_means["feat_num"] == 20.0
        assert prep.numeric_medians["feat_num"] == 20.0
        assert set(prep.category_maps["feat_cat"]) == {"A", "B"}

        # Transform validation data
        x_val_vec = prep.transform(val_data)
        assert len(x_val_vec) == 2
        assert len(x_val_vec[0]) == len(x_train_vec[0])

        # Impute missing feat_num in row 2 with train median (20.0 -> 0.0)
        assert x_val_vec[1][0] == 0.0

    def test_feature_preprocessor_serialization(self) -> None:
        """FeaturePreprocessor serializes/deserializes with identical transforms."""
        train_data = [
            {"feat_a": 100.0, "feat_b": "urban"},
            {"feat_a": 200.0, "feat_b": "rural"},
        ]

        prep = FeaturePreprocessor().fit(train_data)
        serialized = prep.to_dict()

        prep_loaded = FeaturePreprocessor.from_dict(serialized)
        assert prep_loaded.is_fitted is True
        assert prep_loaded.numeric_means == prep.numeric_means
        assert prep_loaded.category_maps == prep.category_maps

        test_data = [{"feat_a": 150.0, "feat_b": "urban"}]
        assert prep.transform(test_data) == prep_loaded.transform(test_data)
