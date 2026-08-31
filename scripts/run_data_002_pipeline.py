"""CLI Execution Script for DATA-002: Multi-Region Backfill & Ground-Truth Ingestion.

Orchestrates:
1. Multi-region NASA FIRMS observational backfill across Indian study corridors.
2. Authoritative agricultural / non-industrial ground-truth ingestion & matching.
3. Full contextual enrichment, provenance tracking, and reference label adjudication.
4. Real SupervisedDataset synthesis and Scientific Training Gate evaluation.
"""

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

from packages.context.ground_truth import GroundTruthIngestionService
from packages.context.pipeline import RealContextLabelingService
from packages.data.firms.activation import FirmsDataActivationService
from packages.data.firms.bulk import (
    CANONICAL_STUDY_AREAS,
    STUDY_AREA_REGISTRY,
    BulkDataAcquisitionService,
)
from packages.data.firms.schemas import FirmsProduct
from packages.events.pipeline import (
    RealEventConstructionService,
    get_default_calibrated_scientific_config,
)
from packages.schemas.ml import SupervisedDataset
from services.ml.labels.dataset import SupervisedDatasetBuilder
from services.ml.training.gate import RealTrainingGateEvaluator


def main() -> None:
    """Run DATA-002 backfill, ground truth ingestion, and gate evaluation workflow."""
    parser = argparse.ArgumentParser(
        description="Run DATA-002 multi-region backfill and agricultural ground truth ingestion."
    )
    parser.add_argument(
        "--ground-truth-file",
        type=str,
        default="fixtures/reference/agricultural_ground_truth_sample.json",
        help="Path to authoritative ground truth JSON fixture (default: fixtures/reference/agricultural_ground_truth_sample.json).",
    )
    parser.add_argument(
        "--context-file",
        type=str,
        default="fixtures/context/context_sample_jamnagar.json",
        help="Path to contextual infrastructure fixture (default: fixtures/context/context_sample_jamnagar.json).",
    )
    parser.add_argument(
        "--firms-csv",
        type=str,
        default="fixtures/firms/firms_real_sample_jamnagar.csv",
        help="Path to raw FIRMS CSV observation fixture.",
    )
    parser.add_argument(
        "--study-area",
        type=str,
        default="jamnagar_kutch",
        help="Study area identifier (default: jamnagar_kutch).",
    )

    args = parser.parse_args()
    config = get_default_calibrated_scientific_config()

    print("=" * 65)
    print("DATA-002: MULTI-REGION BACKFILL & GROUND-TRUTH INGESTION")
    print("=" * 65)
    print()

    # 1. Activate FIRMS Detections
    area = STUDY_AREA_REGISTRY.get(args.study_area, CANONICAL_STUDY_AREAS[0])
    firms_csv_path = Path(args.firms_csv)
    if not firms_csv_path.exists():
        print(f"Error: FIRMS CSV fixture not found at {firms_csv_path}")
        sys.exit(1)

    print(f"1. Activating raw FIRMS observations from {firms_csv_path}...")
    det_ds = FirmsDataActivationService.activate_from_csv(
        csv_input=firms_csv_path,
        study_area=area,
        requested_start_date="2026-08-01",
        requested_end_date="2026-08-10",
        source_product="VIIRS_SNPP_NRT",
        sensor="VIIRS",
    )
    print(f"   -> Activated {len(det_ds.detections)} raw observations across {det_ds.manifest.study_area_id}")

    # 2. Construct Physical Events
    print("2. Constructing physical thermal events and persistent sources...")
    event_ds = RealEventConstructionService.construct_events_and_sources(
        detection_dataset=det_ds,
        config=config,
    )
    print(f"   -> Derived {len(event_ds.events)} physical events and {len(event_ds.persistent_sources)} persistent sources.")

    # 3. Ingest Authoritative Ground Truth
    gt_file_path = Path(args.ground_truth_file)
    external_evidence = []
    if gt_file_path.exists():
        print(f"3. Ingesting authoritative ground truth from {gt_file_path}...")
        gt_records, gt_hash = GroundTruthIngestionService.load_ground_truth_from_json(gt_file_path)
        print(f"   -> Loaded {len(gt_records)} external ground-truth records (Hash: {gt_hash[:16]}...)")

        # Match Events to Ground Truth
        external_evidence = GroundTruthIngestionService.match_events_to_ground_truth(
            events=event_ds.events,
            ground_truth_records=gt_records,
            max_distance_meters=config.attribution_radius_meters or 2000.0,
            max_temporal_delta_hours=24.0,
        )
        print(f"   -> Matched {len(external_evidence)} authoritative ground-truth reference evidence items.")
    else:
        print(f"3. No external ground-truth file provided or found at {gt_file_path} (continuing with context-only)...")

    # 4. Context Enrichment & Reference Label Adjudication
    ctx_file_path = Path(args.context_file)
    print(f"4. Enriching context and adjudicating labels using {ctx_file_path}...")
    ctx_features, ctx_hashes = RealContextLabelingService.load_context_features_from_fixture(ctx_file_path)
    enriched_ds = RealContextLabelingService.enrich_and_adjudicate_dataset(
        event_dataset=event_ds,
        candidate_features=ctx_features,
        snapshot_hashes=ctx_hashes,
        config=config,
        external_reference_evidence=external_evidence,
    )
    print(f"   -> Adjudicated {len(enriched_ds.reference_labels)} reference label decisions.")

    # 5. Build Supervised Dataset
    print("5. Synthesizing 30-feature SupervisedDataset...")
    builder = SupervisedDatasetBuilder()
    supervised_ds = builder.build_from_real_enriched_dataset(
        enriched_dataset=enriched_ds,
        detection_dataset=det_ds,
        target_ids=["target_industrial_segregation"],
    )
    print(f"   -> Built SupervisedDataset ({supervised_ds.manifest.dataset_id}) with {len(supervised_ds.records)} total records.")

    # 6. Evaluate Scientific Training Gate
    print("6. Evaluating Scientific Training Gate...")
    gate_eval = RealTrainingGateEvaluator.evaluate(
        dataset=supervised_ds,
        target_id="target_industrial_segregation",
    )

    print()
    print("-" * 65)
    print("DATA-002 PIPELINE & SCIENTIFIC GATE SUMMARY")
    print("-" * 65)
    print(f"Total Physical Events:         {gate_eval.total_events}")
    print(f"Eligible Labeled Events:       {gate_eval.eligible_events}")
    print(f"Excluded Events:               {gate_eval.excluded_events}")
    print(f"Class Distribution:            {gate_eval.class_distribution}")
    print(f"Unique Persistent Sources:     {gate_eval.unique_persistent_sources}")
    print(f"Unique Facilities:             {gate_eval.unique_facilities}")
    print(f"Geographic Study Areas:        {gate_eval.geographic_coverage}")
    print(f"Temporal Span (Days):          {gate_eval.temporal_coverage_days:.1f}")
    print(f"Sensors:                       {gate_eval.sensor_diversity}")
    print(f"Split Feasibility:             {gate_eval.split_feasibility}")
    print(f"Class Diversity Sufficient:    {gate_eval.class_diversity_sufficient}")
    print(f"Statistical Validity:          {gate_eval.statistical_validity}")
    print(f"Gate Status:                   {gate_eval.gate_status}")
    print(f"Production ML Readiness:       {'YES' if gate_eval.is_production_ready else 'NO'}")
    print()

    if gate_eval.rejection_reasons:
        print("Scientific Gate Rejection Reasons:")
        for r in gate_eval.rejection_reasons:
            print(f"  - {r}")
        print()

    print("=" * 65)


if __name__ == "__main__":
    main()
