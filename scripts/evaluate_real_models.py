"""NEXT-007: Production Real ML Model Scientific Evaluation Entry Point.

Executes the authoritative scientific evaluation campaign for real production models
post NEXT-006 training, utilizing strictly held-out real labeled data.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from packages.context.ground_truth import GroundTruthIngestionService
from packages.context.pipeline import RealContextLabelingService
from packages.data.firms.activation import FirmsDataActivationService
from packages.data.firms.capture import compute_content_hash
from packages.data.firms.schemas import (
    RealDataAcquisitionManifest,
    RealDetectionDataset,
)
from packages.events.pipeline import (
    RealEventConstructionService,
    get_default_calibrated_scientific_config,
)
from packages.feasibility.candidates import get_candidate_study_area
from packages.schemas.common import BoundingBox
from packages.schemas.ml import SplitStrategy
from services.ml.evaluation.next_007_evaluator import Next007RealModelEvaluator
from services.ml.labels.dataset import SupervisedDatasetBuilder


def run_real_evaluation() -> None:
    print("=" * 75)
    print("SIH26162 — NEXT-007 REAL PRODUCTION MODEL SCIENTIFIC EVALUATION")
    print("=" * 75)
    print()

    config = get_default_calibrated_scientific_config()

    raw_root = Path("data/real/raw/firms")
    csv_paths = sorted(raw_root.glob("*/*/*/raw.csv"))

    if not csv_paths:
        print("[ERROR] No raw FIRMS data found in data/real/raw/firms/.")
        return

    print(f"Discovered {len(csv_paths)} raw observation chunks across corridors.")
    all_detections = []
    for p in csv_paths:
        parts = p.parts
        area_id = parts[-4]
        prod = parts[-3]
        sensor = "MODIS" if "MODIS" in prod.upper() else "VIIRS"
        dates = parts[-2].split("_")
        try:
            area = get_candidate_study_area(area_id)
            det_ds = FirmsDataActivationService.activate_from_csv(
                csv_input=p,
                study_area=area,
                requested_start_date=dates[0],
                requested_end_date=dates[1],
                source_product=prod,
                sensor=sensor,
            )
            all_detections.extend(det_ds.detections)
        except Exception as err:
            print(f"  [WARN] Failed activating {p}: {err}")

    seen_ids = set()
    dedup_detections = []
    for d in all_detections:
        if d.detection_id not in seen_ids:
            seen_ids.add(d.detection_id)
            dedup_detections.append(d)

    print(f"Activated {len(dedup_detections)} unique valid satellite detections.")

    min_date = (
        min(d.acquired_at.strftime("%Y-%m-%d") for d in dedup_detections)
        if dedup_detections
        else "2026-03-01"
    )
    max_date = (
        max(d.acquired_at.strftime("%Y-%m-%d") for d in dedup_detections)
        if dedup_detections
        else "2026-08-30"
    )

    combined_manifest = RealDataAcquisitionManifest(
        dataset_id="ds_global_real_full",
        source_name="NASA_FIRMS",
        source_product="MULTI_GLOBAL",
        sensor="MULTI",
        study_area_id="global_corridors",
        study_area_name="Global Multi-Corridor Active Coverage",
        requested_start_date=min_date,
        requested_end_date=max_date,
        bounding_box=BoundingBox(
            min_latitude=-60.0,
            min_longitude=-180.0,
            max_latitude=75.0,
            max_longitude=180.0,
        ),
        raw_record_count=len(all_detections),
        valid_record_count=len(dedup_detections),
        canonical_record_count=len(dedup_detections),
        canonical_dataset_hash=compute_content_hash(b"global_real_full_dataset"),
        created_at=datetime.now(UTC),
    )
    combined_det_ds = RealDetectionDataset(
        manifest=combined_manifest,
        detections=dedup_detections,
    )

    event_ds = RealEventConstructionService.construct_events_and_sources(
        detection_dataset=combined_det_ds,
        config=config,
    )
    print(
        f"Constructed {len(event_ds.events)} physical events and "
        f"{len(event_ds.persistent_sources)} persistent sources."
    )

    all_gt_records, gt_hashes = GroundTruthIngestionService.discover_and_load_catalog(
        ["data/real/reference", "fixtures/reference"]
    )
    matched_evidence = GroundTruthIngestionService.match_events_to_ground_truth(
        events=event_ds.events,
        ground_truth_records=all_gt_records,
        max_distance_meters=2000.0,
        max_temporal_delta_hours=24.0,
    )
    sample_cf, sample_hashes = (
        RealContextLabelingService.load_context_features_from_fixture(
            "fixtures/context/context_sample_jamnagar.json"
        )
    )
    facility_features, fac_hashes = (
        GroundTruthIngestionService.load_facility_context_features(
            "data/real/reference/facilities"
        )
    )
    context_features = sample_cf + facility_features
    snapshot_hashes = {**sample_hashes, **fac_hashes, **gt_hashes}

    enriched_ds = RealContextLabelingService.enrich_and_adjudicate_dataset(
        event_dataset=event_ds,
        candidate_features=context_features,
        snapshot_hashes=snapshot_hashes,
        config=config,
        data_status="LIVE_ACQUISITION",
        dataset_id="ds_real_enriched_v1.0.0",
        dataset_version="v1.0.0",
        external_reference_evidence=matched_evidence,
    )

    builder = SupervisedDatasetBuilder()
    supervised_ds = builder.build_from_real_enriched_dataset(
        enriched_dataset=enriched_ds,
        detection_dataset=combined_det_ds,
        split_strategy=SplitStrategy.PERSISTENT_SOURCE_HOLDOUT,
        target_ids=["target_industrial_segregation"],
    )

    event_coords = {
        ev.event_id: (ev.centroid_geometry.latitude, ev.centroid_geometry.longitude)
        for ev in event_ds.events
    }

    campaign = Next007RealModelEvaluator.evaluate_production_campaign(
        dataset=supervised_ds,
        production_artifact_dir="artifacts/real/production",
        output_dir="artifacts/real/evaluation",
        target_id="target_industrial_segregation",
        event_coords=event_coords,
        random_seed=42,
    )

    print("\n" + "=" * 75)
    print("NEXT-007 EVALUATION RESULTS SUMMARY")
    print("=" * 75)
    print(f"Total Physical Events:         {campaign.total_physical_events}")
    print(
        f"Eligible Labeled Events:       {campaign.eligible_labeled_events} "
        f"(Industrial: {campaign.industrial_events}, "
        f"Non-Industrial: {campaign.non_industrial_events})"
    )
    print(f"Excluded UNKNOWN Events:       {campaign.unknown_excluded_events}")
    print(
        f"Split Strategy:                {campaign.split_strategy} "
        f"(Seed: {campaign.random_seed})"
    )
    print(f"Test Partition Size:           {campaign.models_evaluated[0].test_samples}")
    print()

    print("-" * 75)
    print("MODEL PERFORMANCE COMPARISON (HELD-OUT TEST PARTITION)")
    print("-" * 75)
    header = (
        f"{'Model':35s} | {'Macro F1':8s} | {'Bal Acc':8s} | "
        f"{'Prec':6s} | {'Recall':6s} | {'ROC-AUC':7s} | {'ECE':6s}"
    )
    print(header)
    print("-" * 75)
    for m in campaign.models_evaluated:
        roc_str = f"{m.roc_auc:.4f}" if m.roc_auc is not None else "N/A"
        ece_str = (
            f"{m.expected_calibration_error:.4f}"
            if m.expected_calibration_error is not None
            else "N/A"
        )
        print(
            f"{m.model_type:35s} | {m.macro_f1:8.4f} | {m.balanced_accuracy:8.4f} | "
            f"{m.precision:6.4f} | {m.recall:6.4f} | {roc_str:7s} | {ece_str:6s}"
        )

    print("-" * 75)
    print("\nCONFUSION MATRICES (Positive = Industrial, Negative = Non-Industrial):")
    for m in campaign.models_evaluated:
        cm = m.confusion_matrix
        print(
            f"  - {m.model_type:35s}: TP={cm.true_positives:3d}, "
            f"FP={cm.false_positives:3d}, TN={cm.true_negatives:3d}, "
            f"FN={cm.false_negatives:3d}"
        )

    print("\nFEATURE GROUP ABLATION IMPACT (Random Forest):")
    for a in campaign.feature_ablation_matrix:
        print(
            f"  - Removed {a.feature_group:25s}: Macro F1 = {a.macro_f1:.4f} "
            f"(Delta = {a.macro_f1_delta:+.4f}), Bal Acc = {a.balanced_accuracy:.4f} "
            f"(Delta = {a.balanced_accuracy_delta:+.4f})"
        )

    print("\nSCIENTIFIC ACCEPTANCE GATES:")
    for g_name, g_val in campaign.acceptance_gates.items():
        status_sym = "PASS" if g_val["passed"] else "FAIL"
        obs_val = (
            f"{g_val['observed']:.4f}"
            if isinstance(g_val["observed"], float)
            else str(g_val["observed"])
        )
        print(
            f"  - [{status_sym}] {g_name:30s}: "
            f"Threshold {g_val['threshold']:15s} | Observed: {obs_val}"
        )

    print("\n" + "=" * 75)
    print(f"EXECUTIVE VERDICT:             {campaign.executive_verdict}")
    print(f"RECOMMENDED PRODUCTION MODEL:  {campaign.recommended_production_model}")
    print("=" * 75)


if __name__ == "__main__":
    run_real_evaluation()
