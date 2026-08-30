"""Execution Script for NEXT-004: First Real ML Training.

Ingests the real observational dataset (NASA FIRMS Jamnagar pilot), builds the
canonical SupervisedDataset, evaluates the scientific training gate, and fits the
canonical model ladder (B0, B2, B3, B4-DT, B4-RF) in pilot mode.
"""

import json
from pathlib import Path

from packages.config.scientific import ScientificConfig
from packages.context.pipeline import RealContextLabelingService
from packages.data.firms.activation import FirmsDataActivationService
from packages.events.pipeline import RealEventConstructionService
from packages.feasibility.candidates import JAMNAGAR_KUTCH
from packages.schemas.ml import SplitStrategy
from services.ml.labels.dataset import SupervisedDatasetBuilder
from services.ml.training.real_trainer import RealMLTrainer


def run_real_training() -> None:
    """Execute end-to-end real observational data training pipeline."""
    config = ScientificConfig(
        version="v1.0-real-pilot",
        name="real_pilot_profile",
        description="Standard calibrated profile for real Jamnagar pilot",
        spatial_cluster_radius_meters=1000.0,
        temporal_window_hours=2.0,
        persistence_threshold_days=10.0,
        persistence_min_observations=3,
        attribution_radius_meters=1500.0,
        attribution_confidence_threshold=0.7,
        minimum_event_confidence=0.5,
        abstention_confidence_threshold=0.4,
    )

    # 1. Ingest Real NASA FIRMS Detections
    csv_path = Path("fixtures/firms/firms_real_sample_jamnagar.csv")
    det_ds = FirmsDataActivationService.activate_from_csv(
        csv_input=csv_path,
        study_area=JAMNAGAR_KUTCH,
        requested_start_date="2026-08-01",
        requested_end_date="2026-08-10",
    )

    # 2. Construct Real Physical Events & Sources
    ev_ds = RealEventConstructionService.construct_events_and_sources(
        detection_dataset=det_ds,
        config=config,
    )

    # 3. Contextual Enrichment & Reference Label Adjudication
    ctx_path = Path("fixtures/context/context_sample_jamnagar.json")
    features, hashes = RealContextLabelingService.load_context_features_from_fixture(
        ctx_path
    )
    enriched_ds = RealContextLabelingService.enrich_and_adjudicate_dataset(
        event_dataset=ev_ds,
        candidate_features=features,
        snapshot_hashes=hashes,
        config=config,
    )

    # 4. Assemble SupervisedDataset
    builder = SupervisedDatasetBuilder()
    supervised_ds = builder.build_from_real_enriched_dataset(
        enriched_dataset=enriched_ds,
        detection_dataset=det_ds,
        split_strategy=SplitStrategy.FACILITY_HOLDOUT,
        target_ids=["target_industrial_segregation"],
    )

    # 5. Execute Real ML Trainer with Scientific Gate Evaluation
    trainer = RealMLTrainer(
        random_seed=42,
        artifact_base_dir="artifacts/real/pilot",
    )
    suite_result = trainer.train_real_suite(
        dataset=supervised_ds,
        target_id="target_industrial_segregation",
    )

    gate = suite_result.gate_evaluation

    # 6. Format and Print Report
    print("=" * 60)
    print("REAL ML TRAINING — NEXT-004")
    print("=" * 60)
    print()
    print(f"Dataset:")
    print(f"    {suite_result.dataset_id} (version: {suite_result.dataset_version})")
    print()
    print(f"Eligible records:")
    print(f"    {gate.eligible_events} / {gate.total_events} (Excluded: {gate.excluded_events})")
    print()
    print(f"Class distribution:")
    print(f"    {json.dumps(gate.class_distribution, indent=8)}")
    print()
    print(f"Scientific training gate:")
    print(f"    {gate.gate_status}")
    if gate.rejection_reasons:
        print("    Rejection Reasons:")
        for reason in gate.rejection_reasons:
            print(f"      - {reason}")
    print()
    print("-" * 60)
    print("MODEL LADDER RESULTS:")
    print("-" * 60)

    model_display_names = {
        "MajorityClassClassifier": "B0 (Majority Baseline)",
        "DeterministicContextualClassifier": "B2 (Deterministic Contextual)",
        "LogisticRegressionClassifier": "B3 (Softmax Logistic Regression)",
        "DecisionTreeClassifier": "B4-DT (CART Decision Tree)",
        "RandomForestClassifier": "B4-RF (Random Forest Ensemble)",
    }

    for m_type, res in suite_result.model_results.items():
        name = model_display_names.get(m_type, m_type)
        print(f"{name}:")
        print(f"    Status:        {res.status}")
        print(f"    Artifact Path: {res.artifact_path}")
        print(f"    Reason:        {res.reason}")
        print()

    print("-" * 60)
    print(f"Production validity:")
    print(f"    {'VALID' if suite_result.is_production_ready else 'NOT VALID (PILOT SMOKE-TRAINING ONLY)'}")
    print("=" * 60)


if __name__ == "__main__":
    run_real_training()
