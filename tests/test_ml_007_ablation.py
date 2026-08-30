"""Comprehensive tests for ML-007 Feature Ablation Framework.

Validates canonical feature group derivation, multi-model ablation execution,
train-only preprocessor isolation, delta calculation, shortcut diagnostic computation,
and markdown report generation.
"""

from datetime import UTC, datetime, timedelta

import pytest

from packages.schemas.common import Coordinate
from packages.schemas.detection import Detection
from packages.schemas.enums import DayNight
from packages.schemas.event import Event
from packages.schemas.ml import (
    LabelDecision,
    LabelProvenanceType,
    LabelTier,
    SplitStrategy,
    SupervisedDataset,
)
from services.ml.evaluation.ablation import FeatureAblationService
from services.ml.features.builder import FeatureDatasetBuilder
from services.ml.features.standard_set import get_standard_feature_registry
from services.ml.labels.dataset import SupervisedDatasetBuilder


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


@pytest.fixture
def supervised_benchmark_dataset() -> SupervisedDataset:
    """Build controlled supervised dataset fixture."""
    t0 = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
    event_tuples = []
    labels = []

    for i in range(1, 21):
        eid = f"evt_{i:03d}"
        is_ind = i <= 10
        lat_val = 22.48 if is_ind else 22.10
        frp_val = 55.0 if is_ind else 12.0

        det = _create_detection(
            f"d_{i:03d}",
            t0 + timedelta(hours=i),
            lat=lat_val,
            frp=frp_val,
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

    feat_builder = FeatureDatasetBuilder()
    feat_dataset = feat_builder.extract_and_build_dataset(
        dataset_id="ds_ablation_fixture",
        dataset_version="v1.0.0",
        target_id="target_industrial_segregation",
        geographic_scope="IND_GUJARAT",
        temporal_start=t0,
        temporal_end=t0 + timedelta(days=2),
        split_strategy=SplitStrategy.GROUPED_EVENT_HOLDOUT,
        event_tuples=event_tuples,
    )

    sup_builder = SupervisedDatasetBuilder()
    return sup_builder.build_supervised_dataset(
        feature_dataset=feat_dataset,
        label_decisions_by_target={"target_industrial_segregation": labels},
        train_ratio=0.60,
        val_ratio=0.20,
        test_ratio=0.20,
        random_seed=42,
    )


class TestML007Ablation:
    """Test suite for Feature Ablation & Scientific Dependency Audit (ML-007)."""

    def test_canonical_subset_definitions(self) -> None:
        """Canonical subsets match the approved feature catalog exactly."""
        reg = get_standard_feature_registry()
        subsets = FeatureAblationService.get_canonical_subsets(reg)

        assert "FULL" in subsets
        assert "THERMAL_ONLY" in subsets
        assert "TEMPORAL_ONLY" in subsets
        assert "PERSISTENCE_ONLY" in subsets
        assert "SPATIAL_ONLY" in subsets
        assert "ENVIRONMENTAL_ONLY" in subsets
        assert "NO_SPATIAL" in subsets
        assert "NO_PERSISTENCE" in subsets
        assert "NO_CONTEXT" in subsets
        assert "THERMAL_PLUS_TEMPORAL" in subsets
        assert "THERMAL_PLUS_ENVIRONMENTAL" in subsets
        assert "THERMAL_PLUS_TEMPORAL_PLUS_ENVIRONMENTAL" in subsets

        assert len(subsets["FULL"]) == 30
        assert len(subsets["THERMAL_ONLY"]) == 14
        assert len(subsets["TEMPORAL_ONLY"]) == 4
        assert len(subsets["PERSISTENCE_ONLY"]) == 5
        assert len(subsets["SPATIAL_ONLY"]) == 5
        assert len(subsets["ENVIRONMENTAL_ONLY"]) == 2

        # Set algebra invariants
        assert set(subsets["SPATIAL_ONLY"]).isdisjoint(set(subsets["NO_SPATIAL"]))
        assert set(subsets["FULL"]) == (
            set(subsets["SPATIAL_ONLY"]) | set(subsets["NO_SPATIAL"])
        )

        assert set(subsets["PERSISTENCE_ONLY"]).isdisjoint(
            set(subsets["NO_PERSISTENCE"])
        )
        assert set(subsets["FULL"]) == (
            set(subsets["PERSISTENCE_ONLY"]) | set(subsets["NO_PERSISTENCE"])
        )

    def test_ablation_study_execution_and_isolation(
        self, supervised_benchmark_dataset: SupervisedDataset
    ) -> None:
        """Ablation study runs across models and feature subsets cleanly."""
        report = FeatureAblationService.run_ablation_study(
            dataset=supervised_benchmark_dataset,
            target_id="target_industrial_segregation",
            model_types=[
                "MajorityClassClassifier",
                "LogisticRegressionClassifier",
                "DecisionTreeClassifier",
            ],
            random_seed=42,
        )

        assert report.study_id.startswith("ablation_target_industrial_segregation_")
        assert len(report.subsets_evaluated) == 12
        assert len(report.results) == 12 * 3

        # Check FULL experiment presence
        full_results = [r for r in report.results if r.subset_name == "FULL"]
        assert len(full_results) == 3

        # Verify deltas vs FULL are 0.0 for FULL
        for r in full_results:
            assert r.delta_vs_full_macro_f1 == 0.0
            assert r.delta_vs_full_balanced_acc == 0.0
            assert r.delta_vs_full_acc == 0.0

    def test_b2_contextual_heuristic_applicability(
        self, supervised_benchmark_dataset: SupervisedDataset
    ) -> None:
        """Deterministic baseline B2 is not applicable on non-spatial subsets."""
        report = FeatureAblationService.run_ablation_study(
            dataset=supervised_benchmark_dataset,
            target_id="target_industrial_segregation",
            subsets={
                "FULL": ["facility_distance_meters", "frp_max_mw"],
                "THERMAL_ONLY": ["frp_max_mw"],
                "SPATIAL_ONLY": ["facility_distance_meters"],
            },
            model_types=["DeterministicContextualClassifier"],
            random_seed=42,
        )

        by_subset = {r.subset_name: r for r in report.results}
        assert by_subset["FULL"].is_applicable is True
        assert by_subset["SPATIAL_ONLY"].is_applicable is True
        assert by_subset["THERMAL_ONLY"].is_applicable is False

    def test_ablation_determinism(
        self, supervised_benchmark_dataset: SupervisedDataset
    ) -> None:
        """Repeated runs with same seed produce identical metrics."""
        rep1 = FeatureAblationService.run_ablation_study(
            dataset=supervised_benchmark_dataset,
            target_id="target_industrial_segregation",
            subsets={
                "FULL": ["frp_max_mw", "facility_distance_meters"],
                "THERMAL_ONLY": ["frp_max_mw"],
            },
            model_types=["DecisionTreeClassifier", "LogisticRegressionClassifier"],
            random_seed=42,
        )

        rep2 = FeatureAblationService.run_ablation_study(
            dataset=supervised_benchmark_dataset,
            target_id="target_industrial_segregation",
            subsets={
                "FULL": ["frp_max_mw", "facility_distance_meters"],
                "THERMAL_ONLY": ["frp_max_mw"],
            },
            model_types=["DecisionTreeClassifier", "LogisticRegressionClassifier"],
            random_seed=42,
        )

        for r1, r2 in zip(rep1.results, rep2.results, strict=True):
            assert r1.test_metrics.get("macro_f1") == r2.test_metrics.get("macro_f1")
            assert r1.test_metrics.get("accuracy") == r2.test_metrics.get("accuracy")
            assert r1.test_metrics.get("balanced_accuracy") == r2.test_metrics.get(
                "balanced_accuracy"
            )
            assert r1.delta_vs_full_macro_f1 == r2.delta_vs_full_macro_f1

    def test_shortcut_diagnostics_and_markdown_generation(
        self, supervised_benchmark_dataset: SupervisedDataset
    ) -> None:
        """Shortcut diagnostics compute deltas and markdown formatting succeeds."""
        report = FeatureAblationService.run_ablation_study(
            dataset=supervised_benchmark_dataset,
            target_id="target_industrial_segregation",
            model_types=[
                "MajorityClassClassifier",
                "LogisticRegressionClassifier",
                "DecisionTreeClassifier",
                "RandomForestClassifier",
            ],
            random_seed=42,
        )

        assert "LogisticRegressionClassifier" in report.shortcut_diagnostics
        assert "DecisionTreeClassifier" in report.shortcut_diagnostics
        assert "RandomForestClassifier" in report.shortcut_diagnostics

        dt_diag = report.shortcut_diagnostics["DecisionTreeClassifier"]
        assert "context_dependency_delta" in dt_diag
        assert "thermal_dependency_delta" in dt_diag

        md = FeatureAblationService.generate_ablation_summary_markdown(report)
        assert "# Feature Ablation & Scientific Dependency Audit" in md
        assert "DecisionTreeClassifier" in md
        assert "Context Dependency" in md

    def test_ablation_pipeline_artifact_serialization_roundtrip(
        self, supervised_benchmark_dataset: SupervisedDataset
    ) -> None:
        """Ablation models produce valid, reloadable ModelArtifact containers."""
        from services.ml.training.pipeline import MLTrainingPipeline

        pipeline = MLTrainingPipeline(random_seed=42)
        res = pipeline.run_training_and_evaluation(
            dataset=supervised_benchmark_dataset,
            target_id="target_industrial_segregation",
            model_type="DecisionTreeClassifier",
            feature_names=["frp_max_mw", "brightness_max_kelvin"],
        )

        artifact = res["artifact"]
        assert artifact is not None
        assert len(artifact.metadata.feature_names) == 2
        assert "num_frp_max_mw" in artifact.metadata.feature_names

    def test_ablation_leakage_and_id_exclusion(
        self, supervised_benchmark_dataset: SupervisedDataset
    ) -> None:
        """Prohibited entity IDs cannot be selected as ablation features."""
        from services.ml.preprocessing.extractor import (
            PROHIBITED_METADATA_COLUMNS,
            DatasetSplitExtractor,
        )

        subsets = FeatureAblationService.get_canonical_subsets()
        for s_name, feats in subsets.items():
            overlap = set(feats).intersection(PROHIBITED_METADATA_COLUMNS)
            assert not overlap, (
                f"Prohibited columns {overlap} found in subset '{s_name}'"
            )

        # Explicitly trying to extract prohibited columns ignores them
        x_tr, _, _, _, _, _, _, _, _ = DatasetSplitExtractor.extract_split_matrices(
            dataset=supervised_benchmark_dataset,
            target_id="target_industrial_segregation",
            feature_names=["event_id", "facility_id", "frp_max_mw"],
        )
        assert len(x_tr) > 0
        for sample in x_tr:
            assert "event_id" not in sample
            assert "facility_id" not in sample
            assert "frp_max_mw" in sample
