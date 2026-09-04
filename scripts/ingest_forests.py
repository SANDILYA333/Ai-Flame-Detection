#!/usr/bin/env python3
"""CLI tool for ingesting OpenStreetMap global forest areas via Overpass API."""

import argparse
import json
import sys

from packages.config import get_settings
from packages.data.forests.service import ForestIngestionService
from packages.logging import configure_logging, get_logger

logger = get_logger("scripts.ingest_forests")


def main() -> None:
    """Parse CLI arguments and execute OpenStreetMap forest area ingestion."""
    parser = argparse.ArgumentParser(
        description="Ingest global forest areas from OpenStreetMap via Overpass API."
    )
    parser.add_argument(
        "--country",
        "-c",
        type=str,
        default=None,
        help="ISO 3166-1 alpha-2 country code (e.g. 'IN', 'BR', 'US', 'CA', 'AU').",
    )
    parser.add_argument(
        "--bbox",
        "-b",
        type=str,
        default=None,
        help="Bounding box in 'min_lat,min_lon,max_lat,max_lon' format (EPSG:4326).",
    )
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=None,
        help="Maximum number of OSM elements to retrieve.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Query, parse, validate, and report stats without writing to DB.",
    )
    parser.add_argument(
        "--include-boundary",
        action="store_true",
        help="Include 'boundary=forest' in addition to standard forest tags.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output ingestion telemetry stats as pure JSON.",
    )

    args = parser.parse_args()

    settings = get_settings()
    configure_logging(level=settings.LOG_LEVEL)

    if not args.country and not args.bbox:
        print("Error: Either --country or --bbox must be provided.", file=sys.stderr)
        parser.print_help(sys.stderr)
        sys.exit(1)

    service = ForestIngestionService()

    try:
        if args.country:
            stats = service.ingest_by_country(
                country_code=args.country,
                dry_run=args.dry_run,
                limit=args.limit,
                include_boundary=args.include_boundary,
            )
        else:
            parts = [float(p.strip()) for p in args.bbox.split(",")]
            if len(parts) != 4:
                raise ValueError(
                    "bbox requires 4 values: min_lat,min_lon,max_lat,max_lon"
                )
            min_lat, min_lon, max_lat, max_lon = parts
            stats = service.ingest_by_bbox(
                min_lat=min_lat,
                min_lon=min_lon,
                max_lat=max_lat,
                max_lon=max_lon,
                dry_run=args.dry_run,
                limit=args.limit,
                include_boundary=args.include_boundary,
            )

        if args.json:
            print(json.dumps(stats.model_dump(), indent=2))
        else:
            print("\n==========================================")
            print("  FOREST INTELLIGENCE INGESTION REPORT    ")
            print("==========================================")
            print(f"Scope:               {stats.scope}")
            print(f"Source:              {stats.source}")
            print(f"Dry Run Mode:        {stats.is_dry_run}")
            print(f"Objects Received:    {stats.objects_received}")
            print(f"Polygons Parsed:     {stats.polygons_parsed}")
            print(f"Invalid Geometries:  {stats.invalid_geometries}")
            print(f"Geometry Repairs:    {stats.geometry_repairs}")
            print(f"Inserted:            {stats.inserted}")
            print(f"Updated:             {stats.updated}")
            print(f"Duplicates Skipped:  {stats.duplicates_skipped}")
            print(f"Rejected:            {stats.rejected}")
            print(f"Duration:            {stats.duration_seconds}s")
            print("==========================================\n")

    except Exception as e:
        print(f"Error during forest ingestion: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
