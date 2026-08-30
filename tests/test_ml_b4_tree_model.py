"""Formal tests for B4 Tree-Based ML Models (ML-006).

Validates Decision Tree and Random Forest classifiers:
- Determinism and reproducibility
- Gini impurity splitting and MDI feature importance
- Probability validity (bounds [0, 1], sums to 1.0)
- Shape validation and edge-case handling
- Save/reload artifact invariance via ModelRegistry
- Label-shuffle sanity collapse
- End-to-end integration with MLTrainingPipeline and baseline comparison.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from packages.schemas.common import Coordinate
from packages.schemas.detection import Detection
from packages.schemas.enums import DayNight
from packages.schemas.event import Event
from packages.schemas.ml import (
    LabelDecision,
    LabelProvenanceType,
    LabelTier,
    ModelArtifact,
    ModelMetadata,
    SplitStrategy,
)
from services.ml.features.builder import FeatureDatasetBuilder
from services.ml.labels.dataset import SupervisedDatasetBuilder
from services.ml.models.registry import ModelRegistry
from services.ml.models.tree import DecisionTreeClassifier, RandomForestClassifier
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


class TestMLB4TreeModel:
    """Test suite formalizing B4 Tree-Based ML Models (ML-006)."""

    def test_b4_decision_tree_determinism(self) -> None:
        """Same dataset and seed produce identical tree structures and predictions."""
        x_train = [
            [10.0, 50.0],
            [12.0, 45.0],
            [1.0, 5.0],
            [2.0, 8.0],
        ]
        y_train = ["industrial", "industrial", "non_industrial", "non_industrial"]

        tree1 = DecisionTreeClassifier(max_depth=3, random_seed=42)
        tree1.fit(x_train, y_train)

        tree2 = DecisionTreeClassifier(max_depth=3, random_seed=42)
        tree2.fit(x_train, y_train)

        x_test = [[11.0, 48.0], [1.5, 6.0]]
        assert tree1.predict(x_test) == tree2.predict(x_test)
        assert tree1.predict_proba(x_test) == tree2.predict_proba(x_test)
        assert tree1.feature_importances_ == tree2.feature_importances_
        assert tree1.get_parameters() == tree2.get_parameters()

    def test_b4_decision_tree_shape_and_type_validation(self) -> None:
        """Validate input types, dimension checks, and empty inputs."""
        tree = DecisionTreeClassifier(max_depth=3, random_seed=42)

        with pytest.raises(ValueError, match="cannot be empty"):
            tree.fit([], [])

        with pytest.raises(TypeError, match="requires preprocessed 2D float matrix"):
            tree.fit([{"feat1": 1.0}], ["industrial"])

        with pytest.raises(ValueError, match="Length mismatch"):
            tree.fit([[1.0, 2.0]], ["industrial", "non_industrial"])

        # Fit valid data
        tree.fit([[1.0, 2.0], [3.0, 4.0]], ["industrial", "non_industrial"])

        # Predict with wrong feature dimension
        with pytest.raises(ValueError, match="Feature dimension mismatch"):
            tree.predict_proba([[1.0, 2.0, 3.0]])

    def test_b4_decision_tree_probability_validity(self) -> None:
        """Leaf probabilities must be in [0, 1] and sum strictly to 1.0."""
        x_train = [
            [5.0, 100.0],
            [4.5, 90.0],
            [1.0, 10.0],
            [0.5, 5.0],
            [0.8, 8.0],
        ]
        y_train = [
            "industrial",
            "industrial",
            "non_industrial",
            "non_industrial",
            "non_industrial",
        ]

        tree = DecisionTreeClassifier(max_depth=4, random_seed=42)
        tree.fit(x_train, y_train)

        probs = tree.predict_proba([[4.8, 95.0], [0.9, 7.0], [10.0, 200.0]])
        assert len(probs) == 3

        for p_row in probs:
            assert pytest.approx(sum(p_row.values()), 1e-6) == 1.0
            for val in p_row.values():
                assert 0.0 <= val <= 1.0

    def test_b4_decision_tree_depth_and_leaf_constraints(self) -> None:
        """Depth constraints and min samples leaf limits are enforced."""
        x_train = [
            [1.0],
            [2.0],
            [3.0],
            [4.0],
            [5.0],
            [6.0],
        ]
        y_train = ["a", "a", "b", "b", "c", "c"]

        # max_depth=1 (decision stump)
        stump = DecisionTreeClassifier(max_depth=1, random_seed=42)
        stump.fit(x_train, y_train)
        assert stump.root is not None
        assert stump.root.left is not None and stump.root.left.is_leaf
        assert stump.root.right is not None and stump.root.right.is_leaf

        # max_depth=0 (root leaf only)
        root_only = DecisionTreeClassifier(max_depth=0, random_seed=42)
        root_only.fit(x_train, y_train)
        assert root_only.root is not None
        assert root_only.root.is_leaf

    def test_b4_decision_tree_feature_importances(self) -> None:
        """MDI correctly attributes importance to the predictive feature."""
        # Feature 0 is perfectly predictive, Feature 1 is uniform constant noise
        x_train = [
            [10.0, 1.0],
            [12.0, 1.0],
            [0.0, 1.0],
            [-2.0, 1.0],
        ]
        y_train = ["industrial", "industrial", "non_industrial", "non_industrial"]
        f_names = ["discriminative_frp", "constant_noise"]

        tree = DecisionTreeClassifier(max_depth=2, random_seed=42)
        tree.fit(x_train, y_train)

        importances = tree.get_feature_importances(f_names)
        assert importances["discriminative_frp"] > 0.95
        assert importances["constant_noise"] == 0.0
        assert pytest.approx(sum(importances.values()), 1e-6) == 1.0

    def test_b4_decision_tree_serialization_and_reload(self, tmp_path: Path) -> None:
        """ModelArtifact roundtrip preserves exact tree structure and predictions."""
        x_train = [
            [10.0, 2.0],
            [8.0, 3.0],
            [1.0, 0.5],
            [0.5, 0.2],
        ]
        y_train = ["industrial", "industrial", "non_industrial", "non_industrial"]

        tree = DecisionTreeClassifier(max_depth=3, random_seed=42)
        tree.fit(x_train, y_train)

        x_eval = [[9.0, 2.5], [0.8, 0.3]]
        orig_preds = tree.predict(x_eval)
        orig_probs = tree.predict_proba(x_eval)

        # Construct ModelArtifact
        now = datetime.now(UTC)
        meta = ModelMetadata(
            model_id="model_dt_test",
            model_type="DecisionTreeClassifier",
            model_version="v1.0.0",
            target_id="target_industrial_segregation",
            dataset_version="ds_v1.0.0",
            feature_set_version="feat_v1.0.0",
            label_set_version="label_v1.0.0",
            split_version="GROUPED_EVENT_HOLDOUT",
            random_seed=42,
            training_timestamp=now,
            train_record_count=len(x_train),
            feature_names=["f1", "f2"],
        )

        artifact = ModelArtifact(
            metadata=meta,
            preprocessor_state={},
            model_parameters=tree.get_parameters(),
            class_vocabulary=tree.class_vocabulary,
        )

        # Save and Reload via ModelRegistry
        art_path = tmp_path / "model_dt.json"
        ModelRegistry.save_to_file(artifact, art_path)
        loaded_art = ModelRegistry.load_from_file(art_path)

        _, reloaded_model = ModelRegistry.reconstruct_pipeline(loaded_art)
        assert isinstance(reloaded_model, DecisionTreeClassifier)
        assert reloaded_model.class_vocabulary == tree.class_vocabulary
        assert reloaded_model.predict(x_eval) == orig_preds
        assert reloaded_model.predict_proba(x_eval) == orig_probs

    def test_b4_random_forest_determinism_and_prediction(self) -> None:
        """Random forest ensemble is deterministic and produces valid probabilities."""
        x_train = [
            [10.0, 20.0, 30.0],
            [12.0, 22.0, 32.0],
            [1.0, 2.0, 3.0],
            [0.5, 1.5, 2.5],
        ]
        y_train = ["industrial", "industrial", "non_industrial", "non_industrial"]

        rf1 = RandomForestClassifier(n_estimators=5, max_depth=3, random_seed=42)
        rf1.fit(x_train, y_train)

        rf2 = RandomForestClassifier(n_estimators=5, max_depth=3, random_seed=42)
        rf2.fit(x_train, y_train)

        x_test = [[11.0, 21.0, 31.0], [0.8, 1.8, 2.8]]
        assert rf1.predict(x_test) == rf2.predict(x_test)
        assert rf1.predict_proba(x_test) == rf2.predict_proba(x_test)

        probs = rf1.predict_proba(x_test)
        for p_row in probs:
            assert pytest.approx(sum(p_row.values()), 1e-6) == 1.0

    def test_b4_random_forest_serialization_and_reload(self, tmp_path: Path) -> None:
        """RandomForestClassifier serializes and reloads cleanly via ModelRegistry."""
        x_train = [
            [5.0, 1.0],
            [6.0, 2.0],
            [-5.0, -1.0],
            [-6.0, -2.0],
        ]
        y_train = ["industrial", "industrial", "non_industrial", "non_industrial"]

        rf = RandomForestClassifier(n_estimators=3, max_depth=2, random_seed=42)
        rf.fit(x_train, y_train)

        x_eval = [[5.5, 1.5], [-5.5, -1.5]]
        orig_preds = rf.predict(x_eval)
        orig_probs = rf.predict_proba(x_eval)

        meta = ModelMetadata(
            model_id="model_rf_test",
            model_type="RandomForestClassifier",
            model_version="v1.0.0",
            target_id="target_industrial_segregation",
            dataset_version="ds_v1.0.0",
            feature_set_version="feat_v1.0.0",
            label_set_version="label_v1.0.0",
            split_version="GROUPED_EVENT_HOLDOUT",
            random_seed=42,
            training_timestamp=datetime.now(UTC),
            train_record_count=len(x_train),
            feature_names=["f1", "f2"],
        )

        artifact = ModelArtifact(
            metadata=meta,
            preprocessor_state={},
            model_parameters=rf.get_parameters(),
            class_vocabulary=rf.class_vocabulary,
        )

        art_path = tmp_path / "model_rf.json"
        ModelRegistry.save_to_file(artifact, art_path)
        loaded_art = ModelRegistry.load_from_file(art_path)

        _, reloaded_model = ModelRegistry.reconstruct_pipeline(loaded_art)
        assert isinstance(reloaded_model, RandomForestClassifier)
        assert reloaded_model.predict(x_eval) == orig_preds
        assert reloaded_model.predict_proba(x_eval) == orig_probs

    def test_b4_end_to_end_training_pipeline(self) -> None:
        """MLTrainingPipeline runs cleanly for DecisionTreeClassifier B4."""
        t0 = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)

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

        feat_builder = FeatureDatasetBuilder()
        feat_dataset = feat_builder.extract_and_build_dataset(
            dataset_id="ds_pipe_tree_test",
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

        pipeline = MLTrainingPipeline(random_seed=42)
        report = pipeline.run_training_and_evaluation(
            dataset=sup_dataset,
            target_id="target_industrial_segregation",
            model_type="DecisionTreeClassifier",
            hyperparameters={
                "max_depth": 3,
                "min_samples_split": 2,
                "min_samples_leaf": 1,
            },
        )

        assert report["target_id"] == "target_industrial_segregation"
        assert report["model_type"] == "DecisionTreeClassifier"
        assert report["partition_counts"]["train"] > 0
        assert report["trivial_baseline_val"] is not None
        assert report["contextual_baseline_val"] is not None
        assert report["ml_model_val"] is not None
        assert report["ml_model_test"] is not None
        assert report["label_shuffle_sanity_test"]["status"] == "PASSED"
        assert report["feature_importances"] is not None
        assert report["artifact"] is not None
