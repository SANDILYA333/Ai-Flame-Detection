"""CLI Execution Script for DATA-001: Bulk Real-World Data Acquisition.

Provides command-line orchestration for multi-region, multi-temporal, multi-sensor
NASA FIRMS observation acquisition, manifest hashing, deduplication, and
scientific training gate evaluation.
"""

import argparse
import sys
from pathlib import Path

from packages.data.firms.bulk import (
    CANONICAL_STUDY_AREAS,
    STUDY_AREA_REGISTRY,
    BulkDataAcquisitionService,
)
from packages.data.firms.schemas import FirmsProduct
from packages.schemas.ml import SupervisedDataset
from services.ml.training.gate import RealTrainingGateEvaluator


def main() -> None:
    """Run bulk FIRMS acquisition workflow."""
    parser = argparse.ArgumentParser(
        description="Acquire and expand real NASA FIRMS observational datasets across Indian study areas."
    )
    parser.add_argument(
        "--study-area",
        type=str,
        default="all",
        help="Study area selector ('all', 'jamnagar', 'singrauli', 'angul', 'punjab', or comma-separated list).",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default="2026-08-01",
        help="Start date in YYYY-MM-DD format (default: 2026-08-01).",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default="2026-08-10",
        help="End date in YYYY-MM-DD format (default: 2026-08-10).",
    )
    parser.add_argument(
        "--sensor",
        type=str,
        default="all",
        help="Sensor selection ('all', 'VIIRS', 'MODIS').",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/real/raw/firms",
        help="Output root directory for raw captures and manifests.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate request planning without downloading data.",
    )

    args = parser.parse_args()

    # 1. Resolve Sensor / Products
    products: list[FirmsProduct] = []
    sensor_lower = args.sensor.strip().lower()
    if sensor_lower in ("all", "both"):
        products = [
            FirmsProduct.VIIRS_SNPP_NRT,
            FirmsProduct.VIIRS_NOAA20_NRT,
            FirmsProduct.MODIS_NRT,
        ]
    elif sensor_lower == "viirs":
        products = [FirmsProduct.VIIRS_SNPP_NRT, FirmsProduct.VIIRS_NOAA20_NRT]
    elif sensor_lower == "modis":
        products = [FirmsProduct.MODIS_NRT]
    else:
        try:
            products = [FirmsProduct(args.sensor)]
        except ValueError:
            print(f"Error: Unknown sensor/product '{args.sensor}'. Available: 'all', 'VIIRS', 'MODIS', {[p.value for p in FirmsProduct]}")
            sys.exit(1)

    # 2. Execute Acquisition or Dry Run
    service = BulkDataAcquisitionService(base_output_dir=args.output_dir)
    summary = service.acquire_bulk_dataset(
        study_areas=args.study_area,
        start_date=args.start_date,
        end_date=args.end_date,
        products=products,
        dry_run=args.dry_run,
    )

    print("=" * 60)
    print("DATA-001: BULK REAL-WORLD DATA ACQUISITION REPORT")
    print("=" * 60)
    print()
    print(f"Execution Mode:       {'DRY_RUN (Simulation Only)' if summary.is_dry_run else 'LIVE_ACQUISITION'}")
    print(f"Target Study Areas:   {summary.study_areas}")
    print(f"Target Products:      {summary.products}")
    print(f"Date Coverage:        {summary.start_date} to {summary.end_date}")
    print(f"Total Chunks Planned: {summary.total_chunks_planned}")
    print()

    if summary.is_dry_run:
        print("-" * 60)
        print("PLANNED ACQUISITION CHUNKS:")
        print("-" * 60)
        for i, chunk in enumerate(summary.quality_breakdown.get("planned_chunks", [])):
            print(f"  Chunk {i+1:02d}: Area={chunk['study_area']:<20} Product={chunk['product']:<18} Dates={chunk['start_date']} -> {chunk['end_date']} ({chunk['day_range']} days)")
        print()
        print("Dry run completed successfully. No files written.")
        print("=" * 60)
        return

    print("-" * 60)
    print("ACQUISITION RESULTS:")
    print("-" * 60)
    print(f"Successful Chunks:    {summary.successful_chunks} / {summary.total_chunks_planned}")
    print(f"Failed Chunks:        {summary.failed_chunks}")
    print(f"Total Raw Rows:       {summary.total_raw_rows}")
    print(f"Raw Files Written:    {len(summary.raw_files)}")
    print(f"Manifests Generated:  {len(summary.manifest_paths)}")
    print()

    if summary.quality_breakdown.get("regional_observations"):
        print("Regional Observations Breakdown:")
        for reg, cnt in summary.quality_breakdown["regional_observations"].items():
            print(f"  - {reg}: {cnt} rows")
        print()

    if summary.quality_breakdown.get("sensor_observations"):
        print("Sensor Observations Breakdown:")
        for sens, cnt in summary.quality_breakdown["sensor_observations"].items():
            print(f"  - {sens}: {cnt} rows")
        print()

    if summary.errors:
        print("Warnings / Errors:")
        for err in summary.errors:
            print(f"  ! {err}")
        print()

    print("=" * 60)


if __name__ == "__main__":
    main()
