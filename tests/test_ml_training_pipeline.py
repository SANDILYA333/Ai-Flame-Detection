"""End-to-end tests for MLTrainingPipeline and reproducible evaluation."""

from datetime import UTC, datetime, timedelta

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
from services.ml.training.pipeline import MLTrainingPipeline


def _create_detection(
    det_id: str, t: datetime, lat: float = 22.48, frp: float = 35.0
) -> Detection:
    return Detection(
        detection_id=det_id,
        source="firms",
        source_snapshot_id="snap_1",
        geometry=Coordinate(latitude=lat, longitude=70.06),
        acquired_at=t,
        satellite="SNPP",
        instrument="VIIRS",
        product_type="nrt",
        product_version="v1.0",
        raw_hash=f"hash_{det_id}",
        frp_mw=frp,
        brightness_ti4_k=350.0,
        confidence="nominal",
        day_night=DayNight.NIGHT,
    )


def _create_event(event_id: str, det_id: str, t: datetime, lat: float = 22.48) -> Event:
    return Event(
        event_id=event_id,
        detection_ids=[det_id],
        detection_count=1,
        started_at=t,
        ended_at=t,
        centroid_geometry=Coordinate(latitude=lat, longitude=70.06),
        formation_configuration_id="cfg_v1",
        formation_configuration_version="v1.0",
    )


class TestMLTrainingPipeline:
    """Test suite validating end-to-end ML training, evaluation, and sanity checks."""

    def test_pipeline_execution_and_baseline_comparison(self) -> None:
        """MLTrainingPipeline runs cleanly and executes baseline comparison."""
        t0 = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)

        # Build 10 event tuples with balanced classes
        event_tuples = []
        labels = []

        for i in range(1, 11):
            eid = f"evt_{i:03d}"
            lat_val = 22.48 if i <= 5 else 22.10
            det = _create_detection(
                f"d_{i:03d}",
                t0 + timedelta(hours=i),
                lat=lat_val,
                frp=50.0 if i <= 5 else 10.0,
            )
            evt = _create_event(eid, f"d_{i:03d}", t0 + timedelta(hours=i), lat=lat_val)
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

            cls_name = "industrial" if i <= 5 else "non_industrial"
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

        # Build feature dataset and supervised dataset
        feat_builder = FeatureDatasetBuilder()
        feat_dataset = feat_builder.extract_and_build_dataset(
            dataset_id="ds_pipe_test",
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
            label_decisions_by_target={"target_industrial_segregation": labels},
            train_ratio=0.60,
            val_ratio=0.20,
            test_ratio=0.20,
            random_seed=42,
        )

        # Run pipeline
        pipeline = MLTrainingPipeline(random_seed=42)
        report = pipeline.run_training_and_evaluation(
            dataset=sup_dataset,
            target_id="target_industrial_segregation",
            model_type="LogisticRegressionClassifier",
            hyperparameters={
                "learning_rate": 0.05,
                "max_epochs": 50,
                "l2_lambda": 0.01,
            },
        )

        assert report["target_id"] == "target_industrial_segregation"
        assert report["model_type"] == "LogisticRegressionClassifier"
        assert report["partition_counts"]["train"] > 0
        assert report["trivial_baseline_val"] is not None
        assert report["ml_model_val"] is not None
        assert report["ml_model_test"] is not None
        assert report["label_shuffle_sanity_test"]["status"] == "PASSED"
        assert report["artifact"] is not None
