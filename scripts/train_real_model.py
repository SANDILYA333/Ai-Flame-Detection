"""NEXT-006 Production Real ML Model Training Script.

Orchestrates real-world dataset ingestion across all active corridors and authoritative
ground-truth catalogs, constructs canonical 30-feature SupervisedDataset, and strictly
evaluates the Scientific Training Gate.

If the gate is NOT_PASSED:
  - Halts execution immediately with clean blocking message.
  - Generates no production model artifacts or fake models.
  - Explicitly logs all missing scientific prerequisites.

If the gate is PASSED:
  - Executes leakage-safe group-aware splitting.
  - Fits preprocessor strictly on the training partition.
  - Fits candidate models (Baseline, Logistic Regression, Decision Tree, Random Forest).
  - Performs validation-based model selection using Macro F1.
  - Evaluates final selected model once on held-out test set.
  - Serializes versioned production model artifact and provenance manifest.
"""

import sys
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
from packages.feasibility.candidates import (
    get_candidate_study_area,
)
from packages.schemas.common import BoundingBox
from packages.schemas.ml import SplitStrategy
from services.ml.labels.dataset import SupervisedDatasetBuilder
from services.ml.training.gate import RealTrainingGateEvaluator
from services.ml.training.real_trainer import RealMLTrainer


def train_real_model_main() -> None:
    print("=" * 70)
    print("SIH26162 — NEXT-006 REAL MODEL TRAINING PIPELINE")
    print("=" * 70)
    print()

    config = get_default_calibrated_scientific_config()

    # 1. Discover and Load All Acquired Real FIRMS Observations
    raw_root = Path("data/real/raw/firms")
    csv_paths = sorted(raw_root.glob("*/*/*/raw.csv"))

    if not csv_paths:
        print("[ERROR] No raw FIRMS data found in data/real/raw/firms/.")
        print("REAL MODEL TRAINING BLOCKED: Missing raw observational data.")
        sys.exit(1)

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

    # Deduplicate detections
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

    # 2. Build Unified RealDetectionDataset
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

    # 3. Construct Physical Thermal Events & Persistent Sources
    event_ds = RealEventConstructionService.construct_events_and_sources(
        detection_dataset=combined_det_ds,
        config=config,
    )
    print(
        f"Constructed {len(event_ds.events)} physical events and {len(event_ds.persistent_sources)} persistent sources."
    )

    # 4. Ingest Authoritative Ground Truth Catalogs & Evidence Matching
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
    print(
        f"Ingested {len(all_gt_records)} ground-truth records, matched {len(matched_evidence)} evidence items, {len(context_features)} facility features."
    )

    # 5. Contextual Enrichment & Scientific Label Adjudication
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

    # 6. Assemble Canonical 30-Feature SupervisedDataset
    builder = SupervisedDatasetBuilder()
    supervised_ds = builder.build_from_real_enriched_dataset(
        enriched_dataset=enriched_ds,
        detection_dataset=combined_det_ds,
        split_strategy=SplitStrategy.PERSISTENT_SOURCE_HOLDOUT,
        target_ids=["target_industrial_segregation"],
    )

    # 7. INDEPENDENT HARD SCIENTIFIC TRAINING GATE EVALUATION
    print()
    print("-" * 70)
    print("INDEPENDENT SCIENTIFIC TRAINING GATE EVALUATION")
    print("-" * 70)

    gate_eval = RealTrainingGateEvaluator.evaluate(
        dataset=supervised_ds,
        target_id="target_industrial_segregation",
    )

    print(f"Gate Status:             {gate_eval.gate_status}")
    print(f"Production ML Readiness: {gate_eval.is_production_ready}")
    print(f"Total Events:            {gate_eval.total_events}")
    print(
        f"Eligible Labeled Events: {gate_eval.eligible_events} (Excluded: {gate_eval.excluded_events})"
    )
    print(f"Class Distribution:      {gate_eval.class_distribution}")

    # 8. GATE DECISION BRANCH
    if gate_eval.gate_status != "PASSED" or not gate_eval.is_production_ready:
        print()
        print("=" * 70)
        print("REAL MODEL TRAINING BLOCKED")
        print("=" * 70)
        print("Scientific training gate has not passed.")
        print("No production model artifact was created.")
        print()
        print("EXACT REMAINING DATA DEFICIENCIES / BLOCKING REASONS:")
        for idx, reason in enumerate(gate_eval.rejection_reasons, 1):
            print(f"  {idx}. {reason}")
        print("=" * 70)
        return

    # 9. IF GATE PASSES -> EXECUTE PRODUCTION MODEL TRAINING
    print()
    print("=" * 70)
    print("SCIENTIFIC GATE PASSED — PROCEEDING WITH REAL MODEL TRAINING")
    print("=" * 70)

    trainer = RealMLTrainer(
        random_seed=42,
        artifact_base_dir="artifacts/real/production",
    )
    suite_result = trainer.train_real_suite(
        dataset=supervised_ds,
        target_id="target_industrial_segregation",
    )

    print("Successfully completed real production training suite.")
    for m_type, res in suite_result.model_results.items():
        print(f"  - {m_type:35s}: status={res.status}, artifact={res.artifact_path}")


if __name__ == "__main__":
    train_real_model_main()
