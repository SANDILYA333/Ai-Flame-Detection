#!/usr/bin/env python3
"""Canonical DATASET-002 script: Real Supervised Dataset Assembly & Splitting.

Executes the complete canonical pipeline from real NASA FIRMS observations to a
content-addressed, leakage-safe SupervisedDataset artifact without synthetic data.
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


def main() -> None:
    print("=" * 70)
    print("DATASET-002: REAL SUPERVISED DATASET ASSEMBLY & LEAKAGE-SAFE SPLITTING")
    print("=" * 70)

    config = ScientificConfig(
        version="v1.0-prod",
        name="production_profile",
        description="Production calibrated scientific configuration profile",
        spatial_cluster_radius_meters=1000.0,
        temporal_window_hours=2.0,
        persistence_threshold_days=10.0,
        persistence_min_observations=3,
        attribution_radius_meters=1500.0,
        attribution_confidence_threshold=0.7,
        minimum_event_confidence=0.5,
        abstention_confidence_threshold=0.4,
    )

    # 1. Step 1: Real NASA FIRMS Ingestion (DATA-002 / DATA-005)
    csv_path = Path("fixtures/firms/firms_real_sample_jamnagar.csv")
    print(f"\n[1] Activating Real NASA FIRMS Observations from {csv_path}...")
    detection_dataset = FirmsDataActivationService.activate_from_csv(
        csv_input=csv_path,
        study_area=JAMNAGAR_KUTCH,
        requested_start_date="2026-08-01",
        requested_end_date="2026-08-10",
    )
    print(f"    -> Activated {len(detection_dataset.detections)} real detections.")
    print(f"    -> SHA-256 Digest: {detection_dataset.compute_canonical_hash()}")

    # 2. Step 2: Spatiotemporal Event Clustering (GEO-001 / GEO-002 / GEO-003)
    print("\n[2] Constructing Physical Events & Persistent Sources (DBSCAN)...")
    event_dataset = RealEventConstructionService.construct_events_and_sources(
        detection_dataset=detection_dataset,
        config=config,
    )
    print(f"    -> Constructed {len(event_dataset.events)} physical events.")
    print(f"    -> Tracked {len(event_dataset.persistent_sources)} sources.")
    print(f"    -> SHA-256 Digest: {event_dataset.canonical_dataset_hash}")

    # 3. Step 3: Contextual Enrichment & Label Adjudication (CTX-001 / DATA-008)
    context_fixture = Path("fixtures/context/context_sample_jamnagar.json")
    print(f"\n[3] Enriching Events & Adjudicating Labels from {context_fixture}...")
    features, hashes = RealContextLabelingService.load_context_features_from_fixture(
        context_fixture
    )
    enriched_dataset = RealContextLabelingService.enrich_and_adjudicate_dataset(
        event_dataset=event_dataset,
        candidate_features=features,
        snapshot_hashes=hashes,
        config=config,
    )
    print(f"    -> Matched {len(enriched_dataset.context_evidence)} context items.")
    print(f"    -> Adjudicated {len(enriched_dataset.reference_labels)} labels.")
    print(f"    -> SHA-256 Digest: {enriched_dataset.canonical_dataset_hash}")

    # 4. Step 4: Supervised Dataset Assembly & Splitting (DATASET-002)
    print("\n[4] Building Real Supervised Dataset with FACILITY_HOLDOUT...")
    builder = SupervisedDatasetBuilder()
    supervised_dataset = builder.build_from_real_enriched_dataset(
        enriched_dataset=enriched_dataset,
        detection_dataset=detection_dataset,
        split_strategy=SplitStrategy.FACILITY_HOLDOUT,
        target_ids=["target_industrial_segregation"],
        train_ratio=0.70,
        val_ratio=0.15,
        test_ratio=0.15,
        dataset_id="ds_real_supervised_v1.0.0",
        dataset_version="v1.0.0",
    )

    print("\n[5] Real Supervised Dataset Summary:")
    print(f"    -> Total Labeled Records: {len(supervised_dataset.records)}")
    print(f"    -> Feature Count: {len(supervised_dataset.feature_definitions)}")
    print(f"    -> Train Partition: {supervised_dataset.split_manifest.train_count}")
    print(f"    -> Val Partition: {supervised_dataset.split_manifest.validation_count}")
    print(f"    -> Test Partition: {supervised_dataset.split_manifest.test_count}")
    print(
        f"    -> Excluded Records: {supervised_dataset.split_manifest.excluded_count}"
    )

    stats = supervised_dataset.summary_statistics
    print("\n[6] Class Distribution by Target:")
    print(json.dumps(stats.get("class_distribution_by_target", {}), indent=2))

    print("\n[7] Exclusion Breakdown (Missing != Negative):")
    print(json.dumps(stats.get("exclusion_breakdown", {}), indent=2))

    print("\n[8] Scientific Data-Volume Assessment:")
    manifest = supervised_dataset.split_manifest
    train_eligible = (
        manifest.train_count + manifest.validation_count + manifest.test_count
    )
    if train_eligible < 500:
        print(f"    [!] NOTE: Dataset contains {train_eligible} train-eligible events.")
        print("    [!] This is an offline smoke-test fixture (N=4).")
        print("    [!] Real training requires bulk ingestion (N >= 1,200 events).")
    else:
        print(f"    [OK] Dataset has {train_eligible} events, ready for training.")

    print("\n" + "=" * 70)
    print("DATASET-002: EXECUTION COMPLETE — BRIDGE OPERATIONAL")
    print("=" * 70)


if __name__ == "__main__":
    main()
