"""CLI Execution Script for DATA-001 / DATA-002: Bulk Real-World & Global-Scale Data Acquisition.

Provides command-line orchestration for multi-region, multi-temporal, multi-sensor
NASA FIRMS observation acquisition, deterministic spatial tiling, manifest hashing,
resumability, deduplication, and scientific training gate evaluation across calibration corridors
and global bounding boxes.
"""

import argparse
import sys
from pathlib import Path

from packages.data.firms.bulk import (
    CANONICAL_STUDY_AREAS,
    GLOBAL_VALIDATION_AREAS,
    STUDY_AREA_REGISTRY,
    BulkDataAcquisitionService,
)
from packages.data.firms.schemas import FirmsProduct
from packages.schemas.common import BoundingBox


def main() -> None:
    """Run bulk FIRMS acquisition workflow."""
    parser = argparse.ArgumentParser(
        description="Acquire real NASA FIRMS observational datasets across calibration corridors or global bounding envelopes."
    )
    parser.add_argument(
        "--scope",
        type=str,
        default=None,
        choices=["calibration", "validation", "all", "global"],
        help="Acquisition scope: 'calibration' (Indian corridors), 'validation' (global validation areas), 'all' (all registered), 'global' (worldwide spatial tiling).",
    )
    parser.add_argument(
        "--study-area",
        type=str,
        default=None,
        help="Named study area selector ('jamnagar', 'singrauli', 'angul', 'punjab', 'persian_gulf', 'california', 'amazon', 'australia', or comma-separated list).",
    )
    parser.add_argument(
        "--bbox",
        type=float,
        nargs=4,
        metavar=("MIN_LAT", "MIN_LON", "MAX_LAT", "MAX_LON"),
        default=None,
        help="Arbitrary geographic bounding box coordinates in WGS-84 decimal degrees.",
    )
    parser.add_argument(
        "--tile-size-degrees",
        type=float,
        default=10.0,
        help="Spatial tiling step size in degrees for large bounding envelopes (default: 10.0 deg).",
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
    parser.add_argument(
        "--resume",
        action="store_true",
        default=True,
        help="Enable skipping of previously verified raw downloads (enabled by default).",
    )
    parser.add_argument(
        "--no-resume",
        action="store_false",
        dest="resume",
        help="Disable skipping of previously verified raw downloads.",
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Force re-download of existing chunk folders.",
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

    # 2. Resolve Scope / Target Areas
    custom_bbox: BoundingBox | None = None
    if args.bbox:
        custom_bbox = BoundingBox(
            min_latitude=args.bbox[0],
            min_longitude=args.bbox[1],
            max_latitude=args.bbox[2],
            max_longitude=args.bbox[3],
        )

    study_areas = args.study_area
    if not study_areas and not custom_bbox and not args.scope:
        study_areas = "all"  # Default backward-compatible behavior

    # 3. Execute Acquisition or Dry Run
    service = BulkDataAcquisitionService(base_output_dir=args.output_dir)
    summary = service.acquire_bulk_dataset(
        study_areas=study_areas,
        start_date=args.start_date,
        end_date=args.end_date,
        products=products,
        dry_run=args.dry_run,
        scope=args.scope,
        custom_bbox=custom_bbox,
        tile_size_degrees=args.tile_size_degrees,
        resume=args.resume,
        retry_failed=args.retry_failed,
    )

    print("=" * 65)
    print("DATA-002: GLOBALLY SCALABLE REAL-WORLD FIRE DATA ACQUISITION REPORT")
    print("=" * 65)
    print()
    print(f"Execution Mode:       {'DRY_RUN (Simulation Only)' if summary.is_dry_run else 'LIVE_ACQUISITION'}")
    print(f"Target Areas / Tiles: {len(summary.study_areas)} target envelope(s)")
    print(f"Target Products:      {summary.products}")
    print(f"Date Coverage:        {summary.start_date} to {summary.end_date}")
    print(f"Total Chunks Planned: {summary.total_chunks_planned}")
    print()

    if summary.is_dry_run:
        print("-" * 65)
        print("PLANNED ACQUISITION CHUNKS (Sample):")
        print("-" * 65)
        planned = summary.quality_breakdown.get("planned_chunks", [])
        sample_chunks = planned[:20]
        for i, chunk in enumerate(sample_chunks):
            bbox_str = f"[{chunk['bbox']['min_latitude']:.1f}, {chunk['bbox']['min_longitude']:.1f} to {chunk['bbox']['max_latitude']:.1f}, {chunk['bbox']['max_longitude']:.1f}]"
            print(f"  Chunk {i+1:03d}: Area={chunk['study_area'][:28]:<28} Prod={chunk['product'][:16]:<16} Dates={chunk['start_date']}->{chunk['end_date']} BBox={bbox_str}")
        if len(planned) > 20:
            print(f"  ... and {len(planned) - 20} more planned spatial/temporal chunk(s).")
        print()
        print("Dry run completed successfully. No files written.")
        print("=" * 65)
        return

    print("-" * 65)
    print("ACQUISITION RESULTS:")
    print("-" * 65)
    print(f"Successful Chunks:    {summary.successful_chunks} / {summary.total_chunks_planned}")
    print(f"Skipped (Resumed):    {summary.skipped_chunks}")
    print(f"Failed Chunks:        {summary.failed_chunks}")
    print(f"Total Raw Rows:       {summary.total_raw_rows}")
    print(f"Raw Files Written:    {len(summary.raw_files)}")
    print(f"Manifests Generated:  {len(summary.manifest_paths)}")
    print()

    if summary.quality_breakdown.get("regional_observations"):
        print("Regional Observations Breakdown:")
        for reg, cnt in list(summary.quality_breakdown["regional_observations"].items())[:15]:
            print(f"  - {reg}: {cnt} rows")
        if len(summary.quality_breakdown["regional_observations"]) > 15:
            print(f"  ... and {len(summary.quality_breakdown['regional_observations']) - 15} more regions.")
        print()

    if summary.quality_breakdown.get("sensor_observations"):
        print("Sensor Observations Breakdown:")
        for sens, cnt in summary.quality_breakdown["sensor_observations"].items():
            print(f"  - {sens}: {cnt} rows")
        print()

    if summary.errors:
        print("Warnings / Errors:")
        for err in summary.errors[:10]:
            print(f"  - {err}")
        print()

    print("=" * 65)


if __name__ == "__main__":
    main()
