"""Validation script to run acquired real FIRMS data through the complete real ML pipeline.

Pipeline:
Raw FIRMS CSVs
    ↓
FirmsDataActivationService
    ↓
RealDetectionDataset
    ↓
RealEventConstructionService
    ↓
RealThermalEventDataset
    ↓
GroundTruthIngestionService
    ↓
RealContextLabelingService
    ↓
RealEnrichedEventDataset
    ↓
SupervisedDatasetBuilder
    ↓
SupervisedDataset (30 canonical features)
    ↓
RealTrainingGateEvaluator
"""

import json
from collections import Counter
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
    ALL_CANDIDATE_AREAS,
    get_candidate_study_area,
)
from packages.schemas.detection import Detection
from packages.schemas.event import RealThermalEventDataset
from packages.schemas.ml import DatasetRowStatus
from services.ml.labels.dataset import SupervisedDatasetBuilder
from services.ml.training.gate import RealTrainingGateEvaluator


def main() -> None:
    raw_root = Path("data/real/raw/firms")
    config = get_default_calibrated_scientific_config()

    print("=" * 70)
    print("SIH26162 — DATA-002 POST-ACQUISITION REAL PIPELINE VALIDATION")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # STEP 1: DISCOVER ACQUIRED DATA
    # -------------------------------------------------------------------------
    print("\n" + "=" * 50)
    print("STEP 1: DISCOVER ACQUIRED RAW DATA")
    print("=" * 50)

    csv_paths = sorted(raw_root.glob("*/*/*/raw.csv"))
    manifest_paths = sorted(raw_root.glob("*/*/*/manifest.json"))
    print(f"Total raw CSV files found: {len(csv_paths)}")
    print(f"Total manifest files found: {len(manifest_paths)}")

    area_counts: dict[str, int] = Counter()
    product_counts: dict[str, int] = Counter()
    total_raw_rows = 0
    sha_verified = 0
    sha_mismatched = 0

    for csv_path in csv_paths:
        manifest_path = csv_path.parent / "manifest.json"
        content = csv_path.read_bytes()
        lines = [
            line
            for line in content.decode("utf-8", errors="replace").splitlines()
            if line.strip()
        ]
        data_rows = (
            max(0, len(lines) - 1)
            if lines and "latitude" in lines[0].lower()
            else len(lines)
        )
        total_raw_rows += data_rows

        parts = csv_path.parts
        area_id = parts[-4]
        product_name = parts[-3]

        area_counts[area_id] += data_rows
        product_counts[product_name] += data_rows

        if manifest_path.exists():
            try:
                manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
                expected_sha = manifest_data.get("raw_file_sha256")
                actual_sha = compute_content_hash(content)
                if expected_sha == actual_sha:
                    sha_verified += 1
                else:
                    sha_mismatched += 1
            except Exception:
                sha_mismatched += 1

    print(f"Total raw data rows: {total_raw_rows}")
    print(
        f"SHA-256 integrity verification: {sha_verified}/{len(csv_paths)} passed ({sha_mismatched} failed)"
    )
    print("\nRaw Observations by Study Area:")
    for area_key, count in sorted(area_counts.items()):
        print(f"  - {area_key:25s}: {count:6d} rows")
    print("\nRaw Observations by Product:")
    for prod, count in sorted(product_counts.items()):
        print(f"  - {prod:25s}: {count:6d} rows")

    # -------------------------------------------------------------------------
    # STEP 2: ACTIVATE REAL FIRMS DATA
    # -------------------------------------------------------------------------
    print("\n" + "=" * 50)
    print("STEP 2: ACTIVATE REAL FIRMS DATA")
    print("=" * 50)

    all_detections: list[Detection] = []

    for csv_path in csv_paths:
        parts = csv_path.parts
        area_id = parts[-4]
        product_name = parts[-3]
        dates = parts[-2].split("_")
        start_date, end_date = dates[0], dates[1]

        try:
            area = get_candidate_study_area(area_id)
        except KeyError:
            continue

        sensor = "MODIS" if "MODIS" in product_name.upper() else "VIIRS"

        det_ds = FirmsDataActivationService.activate_from_csv(
            csv_input=csv_path,
            study_area=area,
            requested_start_date=start_date,
            requested_end_date=end_date,
            source_product=product_name,
            sensor=sensor,
        )
        all_detections.extend(det_ds.detections)

    # Deduplicate across multiple overlapping chunk folders if any
    seen_ids = set()
    deduped_detections: list[Detection] = []
    duplicate_count = 0
    for det in all_detections:
        if det.detection_id in seen_ids:
            duplicate_count += 1
            continue
        seen_ids.add(det.detection_id)
        deduped_detections.append(det)

    all_detections = deduped_detections
    total_valid = len(all_detections)
    print(f"TOTAL_RAW_DETECTIONS:      {total_raw_rows}")
    print(f"TOTAL_VALID_DETECTIONS:    {total_valid}")
    print(f"TOTAL_DUPLICATE_EXCLUDED:  {duplicate_count}")
    print(
        f"TOTAL_REJECTED_DETECTIONS: {total_raw_rows - total_valid - duplicate_count}"
    )

    from packages.schemas.common import BoundingBox

    combined_det_manifest = RealDataAcquisitionManifest(
        dataset_id="ds_real_firms_combined",
        source_name="NASA_FIRMS",
        source_product="MULTI_PRODUCT",
        sensor="MULTI_SENSOR",
        study_area_id="global_calibration_validation",
        study_area_name="Global Calibration and Validation Corridors",
        requested_start_date="2026-08-01",
        requested_end_date="2026-08-30",
        bounding_box=BoundingBox(
            min_latitude=-60.0,
            min_longitude=-180.0,
            max_latitude=75.0,
            max_longitude=180.0,
        ),
        raw_record_count=total_raw_rows,
        valid_record_count=total_valid,
        canonical_record_count=total_valid,
        canonical_dataset_hash=compute_content_hash(
            json.dumps([d.detection_id for d in all_detections], sort_keys=True).encode(
                "utf-8"
            )
        ),
        created_at=datetime.now(UTC),
    )
    combined_det_dataset = RealDetectionDataset(
        manifest=combined_det_manifest,
        detections=all_detections,
    )

    # -------------------------------------------------------------------------
    # STEP 3: CONSTRUCT PHYSICAL EVENTS
    # -------------------------------------------------------------------------
    print("\n" + "=" * 50)
    print("STEP 3: CONSTRUCT PHYSICAL EVENTS & PERSISTENT SOURCES")
    print("=" * 50)

    event_ds: RealThermalEventDataset = (
        RealEventConstructionService.construct_events_and_sources(
            detection_dataset=combined_det_dataset,
            config=config,
        )
    )
    total_events = len(event_ds.events)
    total_persistent_sources = len(event_ds.persistent_sources)

    print(f"TOTAL_PHYSICAL_EVENTS:     {total_events}")
    print(f"TOTAL_PERSISTENT_SOURCES:  {total_persistent_sources}")

    events_by_region: Counter[str] = Counter()
    for ev in event_ds.events:
        for area_cand in ALL_CANDIDATE_AREAS:
            if (
                area_cand.bounding_box.min_latitude
                <= ev.centroid_geometry.latitude
                <= area_cand.bounding_box.max_latitude
                and area_cand.bounding_box.min_longitude
                <= ev.centroid_geometry.longitude
                <= area_cand.bounding_box.max_longitude
            ):
                events_by_region[area_cand.area_id] += 1
                break

    print("\nEvents by Region:")
    for r_name, c_cnt in sorted(events_by_region.items()):
        print(f"  - {r_name:25s}: {c_cnt:5d} events")

    # -------------------------------------------------------------------------
    # STEP 4 & 5: INGEST GROUND TRUTH & MATCH EVIDENCE
    # -------------------------------------------------------------------------
    print("\n" + "=" * 50)
    print("STEP 4 & 5: INGEST GROUND TRUTH & MATCH EVIDENCE")
    print("=" * 50)

    # Ingest Ground Truth Catalog
    all_gt_records, gt_hashes = GroundTruthIngestionService.discover_and_load_catalog(
        ["data/real/reference", "fixtures/reference"]
    )
    print(
        f"Total Ground Truth Records Loaded: {len(all_gt_records)} across {len(gt_hashes)} files"
    )

    matched_evidence = GroundTruthIngestionService.match_events_to_ground_truth(
        events=event_ds.events,
        ground_truth_records=all_gt_records,
        max_distance_meters=2000.0,
        max_temporal_delta_hours=24.0,
    )
    print(f"Total Matched Reference Evidence Items: {len(matched_evidence)}")

    # Load Context Infrastructure & Facilities
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
    print(f"Total Context & Facility Features Ingested: {len(context_features)}")

    # -------------------------------------------------------------------------
    # STEP 6: LABEL ADJUDICATION & ENRICHMENT
    # -------------------------------------------------------------------------
    print("\n" + "=" * 50)
    print("STEP 6: CONTEXT ENRICHMENT & LABEL ADJUDICATION")
    print("=" * 50)

    enriched_ds = RealContextLabelingService.enrich_and_adjudicate_dataset(
        event_dataset=event_ds,
        candidate_features=context_features,
        snapshot_hashes=snapshot_hashes,
        external_reference_evidence=matched_evidence,
        config=config,
    )

    label_counts: Counter[str] = Counter()
    for lbl in enriched_ds.reference_labels:
        label_counts[lbl.assigned_class] += 1

    print("Adjudicated Label Distribution across all physical events:")
    for lbl_cls, count in sorted(label_counts.items()):
        print(f"  - {lbl_cls:20s}: {count:6d} events")

    # -------------------------------------------------------------------------
    # STEP 7: BUILD SUPERVISED DATASET
    # -------------------------------------------------------------------------
    print("\n" + "=" * 50)
    print("STEP 7: BUILD 30-FEATURE SUPERVISED DATASET")
    print("=" * 50)

    builder = SupervisedDatasetBuilder()
    supervised_ds = builder.build_from_real_enriched_dataset(
        enriched_dataset=enriched_ds,
        detection_dataset=combined_det_dataset,
    )

    total_supervised = len(supervised_ds.records)
    train_eligible = [
        r
        for r in supervised_ds.records
        if r.row_status == DatasetRowStatus.TRAIN_ELIGIBLE
        and r.labels.get("target_industrial_segregation")
        and r.labels["target_industrial_segregation"].is_train_eligible
        and r.labels["target_industrial_segregation"].assigned_class != "unknown"
    ]
    train_ineligible = [r for r in supervised_ds.records if r not in train_eligible]

    class_dist: Counter[str] = Counter()
    for r_item in train_eligible:
        lbl_item = r_item.labels.get("target_industrial_segregation")
        target_val = lbl_item.assigned_class if lbl_item else "UNKNOWN"
        class_dist[target_val] += 1

    feature_count = (
        len(supervised_ds.records[0].feature_record.features)
        if supervised_ds.records
        else 0
    )

    print(f"TOTAL_SUPERVISED_RECORDS:  {total_supervised}")
    print(f"TRAIN_ELIGIBLE_RECORDS:    {len(train_eligible)}")
    print(f"TRAIN_INELIGIBLE_RECORDS:  {len(train_ineligible)}")
    print(f"FEATURE_COUNT:             {feature_count}")
    print("Train-Eligible Target Distribution:")
    for cls_name, count in sorted(class_dist.items()):
        print(f"  - {cls_name:20s}: {count:6d} records")

    # -------------------------------------------------------------------------
    # STEP 8: RUN SCIENTIFIC TRAINING GATE
    # -------------------------------------------------------------------------
    print("\n" + "=" * 50)
    print("STEP 8: SCIENTIFIC TRAINING GATE EVALUATION")
    print("=" * 50)

    gate_result = RealTrainingGateEvaluator.evaluate(
        dataset=supervised_ds,
    )

    print(f"OVERALL GATE STATUS:       {gate_result.gate_status}")
    print(f"PRODUCTION ML READINESS:   {gate_result.is_production_ready}")
    print("\nDetailed Gate Metrics:")
    print(f"  - Total Events:              {gate_result.total_events}")
    print(f"  - Eligible Events:           {gate_result.eligible_events}")
    print(f"  - Excluded Events:           {gate_result.excluded_events}")
    print(f"  - Class Distribution:        {gate_result.class_distribution}")
    print(f"  - Unique Persistent Sources: {gate_result.unique_persistent_sources}")
    print(f"  - Unique Facilities:         {gate_result.unique_facilities}")
    print(f"  - Geographic Coverage:       {gate_result.geographic_coverage}")
    print(f"  - Temporal Coverage (Days):  {gate_result.temporal_coverage_days:.1f}")
    print(f"  - Sensor Diversity:          {gate_result.sensor_diversity}")
    print(f"  - Split Feasibility:         {gate_result.split_feasibility}")
    print(f"  - Class Diversity Sufficient:{gate_result.class_diversity_sufficient}")
    print(f"  - Statistical Validity:      {gate_result.statistical_validity}")

    if gate_result.rejection_reasons:
        print("\nRejection Reasons:")
        for r in gate_result.rejection_reasons:
            print(f"  - {r}")

    # -------------------------------------------------------------------------
    # STEP 9: READINESS FOR NEXT-006
    # -------------------------------------------------------------------------
    print("\n" + "=" * 50)
    print("STEP 9: NEXT-006 READINESS VERDICT")
    print("=" * 50)

    if gate_result.gate_status == "PASSED":
        print("VERDICT: NEXT-006 MAY BEGIN")
    else:
        print("VERDICT: NEXT-006 MUST NOT BEGIN YET")
        print("\nEXACT MISSING SCIENTIFIC PREREQUISITES:")
        for r in gate_result.rejection_reasons:
            print(f"  - {r}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
