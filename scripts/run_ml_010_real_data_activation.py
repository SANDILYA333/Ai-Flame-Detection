#!/usr/bin/env python3
"""SIH26162 Phase 4 — ML-010 Real-World Data Activation & Provenance Demonstration.

Demonstrates:
1. Loading and activating real-schema NASA FIRMS active fire observations.
2. Geographic bounding box filtering for Jamnagar/Kutch pilot study area.
3. Temporal window filtering and duplicate record elimination.
4. Deterministic canonical dataset hashing and quality control auditing.
5. Filesystem persistence and reload invariance verification.
6. Displaying one sanitized canonical detection record.
"""

import tempfile
from pathlib import Path

from packages.data.firms.activation import FirmsDataActivationService
from packages.feasibility.candidates import JAMNAGAR_KUTCH


def main() -> None:
    print("=" * 70)
    print(" SIH26162 Phase 4 — ML-010 Real-World Data Activation & Provenance ")
    print("=" * 70)

    fixture_path = Path("fixtures/firms/firms_real_sample_jamnagar.csv")
    print("\n[Step 1/5] Loading real-world FIRMS observations from fixture:")
    print(f" -> Source file:             {fixture_path}")
    print(
        f" -> Target Study Area:       {JAMNAGAR_KUTCH.name} ({JAMNAGAR_KUTCH.area_id})"
    )
    bbox = JAMNAGAR_KUTCH.bounding_box
    print(
        f" -> Bounding Box (WGS84):    Lat [{bbox.min_latitude}, {bbox.max_latitude}], "
        f"Lon [{bbox.min_longitude}, {bbox.max_longitude}]"
    )
    print(" -> Temporal Window:         2026-08-01 to 2026-08-10")

    dataset = FirmsDataActivationService.activate_from_csv(
        csv_input=fixture_path,
        study_area=JAMNAGAR_KUTCH,
        requested_start_date="2026-08-01",
        requested_end_date="2026-08-10",
        source_product="VIIRS_SNPP_NRT",
        sensor="VIIRS",
        dataset_id="ds_real_firms_v1.0.0",
        dataset_version="v1.0.0",
    )

    manifest = dataset.manifest

    print("\n[Step 2/5] Ingestion & Quality Control Metrics:")
    print(f" -> Raw Records Parsed:      {manifest.raw_record_count}")
    print(f" -> Structurally Valid:      {manifest.valid_record_count}")
    print(f" -> Invalid / Malformed:     {manifest.invalid_record_count}")
    print(f" -> Exact Duplicates:        {manifest.duplicate_record_count}")
    print(f" -> Spatially Excluded:      {manifest.spatial_excluded_count}")
    print(f" -> Temporally Excluded:     {manifest.temporal_excluded_count}")
    print(f" -> Canonical Detections:    {manifest.canonical_record_count}")
    start_str = (
        manifest.actual_coverage_start.isoformat()
        if manifest.actual_coverage_start
        else "None"
    )
    end_str = (
        manifest.actual_coverage_end.isoformat()
        if manifest.actual_coverage_end
        else "None"
    )
    print(f" -> Earliest Observation:    {start_str}")
    print(f" -> Latest Observation:      {end_str}")

    print("\n[Step 3/5] Sensor & Measurement Distributions:")
    print(f" -> Sensor Breakdown:        {manifest.sensor_distribution}")
    print(f" -> Satellite Breakdown:     {manifest.satellite_distribution}")
    print(f" -> Day / Night Breakdown:   {manifest.day_night_distribution}")
    print(f" -> Missingness Summary:     {manifest.missingness_summary}")
    print(f" -> Canonical Dataset Hash:  {manifest.canonical_dataset_hash}")

    print("\n[Step 4/5] Filesystem Persistence & Reload Integrity:")
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_path = FirmsDataActivationService.save_dataset(dataset, tmp_dir)
        size_bytes = out_path.stat().st_size
        print(f" -> Persisted dataset to:    {out_path.name} ({size_bytes} bytes)")
        reloaded_ds = FirmsDataActivationService.load_dataset(out_path)
        assert (
            reloaded_ds.manifest.canonical_dataset_hash
            == manifest.canonical_dataset_hash
        )
        print(" -> Reload Hash Integrity:   VERIFIED (100% Match)")

    print("\n[Step 5/5] Example Sanitized Canonical Detection Record:")
    print("-" * 70)
    example_det = dataset.detections[0]
    lat_val = example_det.geometry.latitude
    lon_val = example_det.geometry.longitude
    dn_val = example_det.day_night.value if example_det.day_night else "None"
    print(f"  Detection ID:              {example_det.detection_id}")
    print(f"  Source:                    {example_det.source}")
    print(f"  Source Snapshot ID:        {example_det.source_snapshot_id}")
    print(f"  Acquired At (UTC):         {example_det.acquired_at.isoformat()}")
    print(f"  Coordinates (WGS84):       Lat {lat_val:.4f}, Lon {lon_val:.4f}")
    sat_val = example_det.satellite
    inst_val = example_det.instrument
    print(f"  Satellite / Instrument:    {sat_val} / {inst_val}")
    print(f"  Fire Radiative Power (MW): {example_det.frp_mw} MW")
    print(f"  Brightness Temp (TI4):     {example_det.brightness_ti4_k} K")
    print(f"  Confidence:                {example_det.confidence}")
    print(f"  Day / Night:               {dn_val}")
    print("-" * 70)

    print("\n" + "=" * 70)
    print(" ML-010 Real-World Data Activation: PASSED (ALL CHECKS OK)")
    print("=" * 70)


if __name__ == "__main__":
    main()
