"""Execution Script for NEXT-005: Real-World ML Evaluation Campaign.

Loads the real SupervisedDataset (NASA FIRMS Jamnagar pilot), loads trained real
model artifacts from artifacts/real/pilot/, executes the multi-strategy real-world
evaluation framework, and outputs the structured scientific evaluation report.
"""

from pathlib import Path

from packages.config.scientific import ScientificConfig
from packages.context.pipeline import RealContextLabelingService
from packages.data.firms.activation import FirmsDataActivationService
from packages.events.pipeline import RealEventConstructionService
from packages.feasibility.candidates import JAMNAGAR_KUTCH
from packages.schemas.ml import SplitStrategy
from services.ml.evaluation.real_evaluator import RealEvaluationService
from services.ml.labels.dataset import SupervisedDatasetBuilder
from services.ml.models.registry import ModelRegistry


def run_real_evaluation() -> None:
    """Execute real-world evaluation campaign on pilot models and dataset."""
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

    # 5. Load Real Pilot Model Artifact
    artifact_path = Path(
        "artifacts/real/pilot/real_logisticregressionclassifier_target_industrial_segregation_v1.0.0.json"
    )
    if not artifact_path.exists():
        # Fallback to B0 if B3 is not found
        artifact_path = Path(
            "artifacts/real/pilot/real_majorityclassclassifier_target_industrial_segregation_v1.0.0.json"
        )

    model_artifact = ModelRegistry.load_from_file(artifact_path)

    # 6. Execute Evaluation Campaign
    campaign_result = RealEvaluationService.evaluate_model_on_dataset(
        dataset=supervised_ds,
        model_artifact_or_instance=model_artifact,
        target_id="target_industrial_segregation",
    )

    # 7. Print Structured Output
    print("=" * 60)
    print("REAL-WORLD ML EVALUATION — NEXT-005")
    print("=" * 60)
    print()
    print(f"Dataset:")
    print(f"    {campaign_result.dataset_id} (version: {campaign_result.dataset_version})")
    print()
    print(f"Model Evaluated:")
    print(f"    {campaign_result.model_id} ({campaign_result.model_type})")
    print()

    first_res = next(iter(campaign_result.strategy_results.values()))
    print(f"Eligible events:")
    print(f"    {first_res.sample_counts.get('eligible', 0)}")
    print()
    print(f"Classes:")
    for c_name, count in first_res.class_distribution.items():
        print(f"    {c_name}: {count}")
    if "non_industrial" not in first_res.class_distribution:
        print("    non-industrial: 0")
    print()
    print("-" * 60)
    print("HOLDOUT STRATEGY EVALUATIONS:")
    print("-" * 60)

    display_names = {
        SplitStrategy.GROUPED_EVENT_HOLDOUT.value: "EVENT HOLDOUT",
        SplitStrategy.FACILITY_HOLDOUT.value: "FACILITY HOLDOUT",
        SplitStrategy.PERSISTENT_SOURCE_HOLDOUT.value: "PERSISTENT SOURCE HOLDOUT",
        SplitStrategy.TEMPORAL_HOLDOUT.value: "TEMPORAL FORWARD HOLDOUT",
        SplitStrategy.SPATIAL_GEOGRAPHIC_HOLDOUT.value: "GEOGRAPHIC HOLDOUT",
    }

    for s_name, res in campaign_result.strategy_results.items():
        title = display_names.get(s_name, s_name.upper())
        print(f"{title}:")
        print(f"    Status: {res.status}")
        if res.reason:
            print(f"    Reason: {res.reason}")
        if res.status == "VALID":
            m = res.metrics
            print(f"    Macro F1:         {m.get('macro_f1', 0.0):.4f}")
            print(f"    Accuracy:         {m.get('accuracy', 0.0):.4f}")
            print(f"    Balanced Accuracy:{m.get('balanced_accuracy', 0.0):.4f}")
        print()

    print("-" * 60)
    print("OVERALL REAL-WORLD EVALUATION:")
    print(f"    {'VALID' if campaign_result.is_production_ready else 'NOT SCIENTIFICALLY VALID ON CURRENT PILOT'}")
    print("=" * 60)


if __name__ == "__main__":
    run_real_evaluation()
