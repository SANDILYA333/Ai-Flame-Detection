"""ML-009 Final Artifact, Reproducibility & Inference Demonstration Script.

Demonstrates:
1. End-to-end model training on controlled benchmark dataset fixture.
2. Serialization to content-addressable JSON artifact with SHA-256 integrity hash.
3. Secret-scanning audit verification.
4. Reload from disk and pipeline reconstruction.
5. Inference execution via MLInferenceEngine on sample event.
6. Verification of numerical and categorical prediction invariance.
"""

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

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
from services.ml.features.builder import FeatureDatasetBuilder
from services.ml.inference.engine import MLInferenceEngine
from services.ml.labels.dataset import SupervisedDatasetBuilder
from services.ml.models.registry import ModelRegistry
from services.ml.training.pipeline import MLTrainingPipeline


def _create_detection(
    det_id: str,
    t: datetime,
    lat: float,
    lon: float,
    frp: float,
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
    lat: float,
    lon: float,
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


def build_benchmark_dataset(n_events: int = 100) -> SupervisedDataset:
    t0 = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
    event_tuples = []
    labels = []

    coords = [
        (22.48, 70.06, "facility_jamnagar", "VIIRS"),
        (22.84, 69.72, "facility_mundra", "MODIS"),
        (21.71, 72.58, "facility_dahej", "VIIRS"),
        (21.10, 72.65, "facility_hazira", "MODIS"),
    ]

    for i in range(1, n_events + 1):
        c_idx = (i - 1) % 4
        lat, lon, _fac_id, sensor = coords[c_idx]
        eid = f"evt_{i:03d}"
        is_ind = i % 2 == 1
        frp_val = 65.0 if is_ind else 12.0

        t_event = t0 + timedelta(hours=i)
        det = _create_detection(f"d_{i:03d}", t_event, lat, lon, frp_val, sensor)
        evt = _create_event(eid, f"d_{i:03d}", t_event, lat, lon)
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
        dataset_id="ds_supervised_v1.0.0",
        dataset_version="v1.0.0",
        target_id="target_industrial_segregation",
        geographic_scope="IND_MULTI_REGION",
        temporal_start=t0,
        temporal_end=t0 + timedelta(days=10),
        split_strategy=SplitStrategy.GROUPED_EVENT_HOLDOUT,
        event_tuples=event_tuples,
    )

    sup_builder = SupervisedDatasetBuilder()
    sup_ds = sup_builder.build_supervised_dataset(
        feature_dataset=feat_ds,
        label_decisions_by_target={"target_industrial_segregation": labels},
        split_strategy=SplitStrategy.GROUPED_EVENT_HOLDOUT,
    )

    return sup_ds


def main() -> None:
    print("==================================================================")
    print(" SIH26162 Phase 4 — ML-009 Artifact & Inference Demonstration    ")
    print("==================================================================")

    # 1. Build Dataset & Execute Training Pipeline
    print("\n[Step 1/5] Building controlled benchmark dataset & training model...")
    dataset = build_benchmark_dataset(100)
    pipeline = MLTrainingPipeline(random_seed=42)

    training_result = pipeline.run_training_and_evaluation(
        dataset=dataset,
        target_id="target_industrial_segregation",
        model_type="RandomForestClassifier",
        hyperparameters={"n_estimators": 10, "max_depth": 5},
    )

    artifact = training_result["artifact"]
    run_manifest = training_result["run_manifest"]

    print(f" -> Training Run ID:         {run_manifest.run_id}")
    print(f" -> Trained Model ID:        {artifact.metadata.model_id}")
    print(f" -> Model Architecture:      {artifact.metadata.model_type}")
    print(
        f" -> Dataset ID & Version:    {artifact.metadata.dataset_id} "
        f"({artifact.metadata.dataset_version})"
    )
    dim = artifact.metadata.feature_dimensionality
    print(f" -> Feature Dimension:       {dim} inputs")
    print(f" -> Artifact Content Hash:   {artifact.sha256_hash}")

    # 2. Save Artifact to Disk with Security Audit
    print("\n[Step 2/5] Serializing & saving model artifact to disk...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        art_path = Path(tmp_dir) / "rf_model_artifact_v1.0.0.json"
        saved_path = ModelRegistry.save_to_file(artifact, art_path)
        sz = saved_path.stat().st_size
        print(f" -> Artifact persisted to:   {saved_path.name} ({sz} bytes)")

        # 3. Reload Artifact from Disk & Verify Content Integrity
        print("\n[Step 3/5] Reloading model artifact & verifying integrity...")
        reloaded_artifact = ModelRegistry.load_from_file(saved_path)
        assert reloaded_artifact.sha256_hash == artifact.sha256_hash
        assert reloaded_artifact.sha256_hash is not None
        short_hash = reloaded_artifact.sha256_hash[:16]
        print(f" -> SHA-256 Integrity Verified: {short_hash}... OK")

        # 4. Construct Sample Event & Execute Inference Engine
        print("\n[Step 4/5] Executing point-in-time inference via MLInferenceEngine...")
        engine_before = MLInferenceEngine(artifact)
        engine_after = MLInferenceEngine(reloaded_artifact)

        sample_time = datetime(2026, 1, 20, 14, 30, 0, tzinfo=UTC)
        sample_det = _create_detection(
            "demo_det_001", sample_time, lat=22.48, lon=70.06, frp=85.0
        )
        sample_evt = _create_event(
            "demo_evt_jamnagar", "demo_det_001", sample_time, lat=22.48, lon=70.06
        )

        pred_before = engine_before.predict_event(
            event=sample_evt,
            member_detections=[sample_det],
            as_of_time=sample_time + timedelta(minutes=15),
        )

        pred_after = engine_after.predict_event(
            event=sample_evt,
            member_detections=[sample_det],
            as_of_time=sample_time + timedelta(minutes=15),
        )

        # 5. Print Output & Invariance Verification
        print("\n[Step 5/5] Inference Result & Invariance Verification:")
        print("------------------------------------------------------------------")
        print(f"  Entity ID:              {pred_after.entity_id}")
        t_id, t_ver = pred_after.target_id, pred_after.target_version
        print(f"  Target ID (Version):    {t_id} ({t_ver})")
        m_id, m_ver = pred_after.model_id, pred_after.model_version
        print(f"  Model ID (Version):     {m_id} ({m_ver})")
        print(f"  Feature Set Version:    {pred_after.feature_set_version}")
        print(f"  Features Evaluated:     {pred_after.feature_count}")
        print(f"  Predicted Class:        {pred_after.predicted_class.upper()}")
        print(f"  Confidence Score:       {pred_after.confidence:.4f}")
        print(f"  Class Probabilities:    {pred_after.class_probabilities}")
        print(f"  Abstained:              {pred_after.is_abstained}")
        print(f"  Inference Latency:      {pred_after.latency_ms:.3f} ms")
        print("------------------------------------------------------------------")

        assert pred_before.predicted_class == pred_after.predicted_class
        assert pred_before.class_probabilities == pred_after.class_probabilities
        assert pred_before.confidence == pred_after.confidence
        print(" -> PREDICTION RELOAD INVARIANCE: 100% MATCH (SUCCESS)")

    print("\n==================================================================")
    print(" ML-009 Artifact & Inference Verification: PASSED (ALL CHECKS OK)")
    print("==================================================================")


if __name__ == "__main__":
    main()
