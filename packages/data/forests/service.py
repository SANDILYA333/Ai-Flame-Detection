"""Forest Ingestion Service orchestrating OpenStreetMap acquisition.

Handles normalization, deduplication, and persistence.
"""

import logging
import time
from typing import Any

from packages.data.forests.client import ForestOverpassClient
from packages.data.forests.parser import candidate_to_forest_record, parse_osm_element
from packages.data.forests.repository import (
    ForestRepositoryProtocol,
    get_forest_repository,
)
from packages.logging import get_logger, log_with_context
from packages.schemas.forest import ForestIngestionStats

logger = get_logger("packages.data.forests.service")


class ForestIngestionService:
    """Production service orchestrating OpenStreetMap forest intelligence ingestion."""

    def __init__(
        self,
        client: ForestOverpassClient | None = None,
        repository: ForestRepositoryProtocol | None = None,
    ) -> None:
        self.client = client or ForestOverpassClient()
        self.repository = repository or get_forest_repository()

    def ingest_by_country(
        self,
        country_code: str,
        dry_run: bool = False,
        limit: int | None = None,
        include_boundary: bool = False,
    ) -> ForestIngestionStats:
        """Ingest OpenStreetMap forests within a specified country.

        Args:
            country_code: ISO 3166-1 alpha-2 code (e.g. 'IN', 'BR', 'US').
            dry_run: If True, parse and validate without persisting.
            limit: Maximum elements to retrieve.
            include_boundary: Whether to include boundary=forest tags.

        Returns:
            ForestIngestionStats summary report.
        """
        code = country_code.strip().upper()
        scope_str = f"country={code}"
        start_time = time.time()

        log_with_context(
            logger,
            logging.INFO,
            f"[FOREST_INGEST] Starting forest ingestion for {scope_str}",
            context={"country_code": code, "dry_run": dry_run, "limit": limit},
        )

        query = self.client.build_country_query(
            code, limit=limit, include_boundary=include_boundary
        )
        data = self.client.execute_query(query)
        elements = data.get("elements", [])

        stats = self._process_elements(
            elements=elements,
            scope=scope_str,
            default_country=code,
            dry_run=dry_run,
            start_time=start_time,
        )

        self._log_completion(stats)
        return stats

    def ingest_by_bbox(
        self,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
        country_code: str = "IN",
        dry_run: bool = False,
        limit: int | None = None,
        include_boundary: bool = False,
    ) -> ForestIngestionStats:
        """Ingest OpenStreetMap forests within a bounding box.

        Args:
            min_lat: South latitude.
            min_lon: West longitude.
            max_lat: North latitude.
            max_lon: East longitude.
            country_code: Default ISO country code for region.
            dry_run: If True, do not persist to database.
            limit: Maximum elements to retrieve.
            include_boundary: Whether to include boundary=forest.

        Returns:
            ForestIngestionStats summary report.
        """
        scope_str = f"bbox=[{min_lat},{min_lon},{max_lat},{max_lon}]"
        start_time = time.time()

        log_with_context(
            logger,
            logging.INFO,
            f"[FOREST_INGEST] Starting bounding box forest ingestion for {scope_str}",
            context={"scope": scope_str, "dry_run": dry_run, "limit": limit},
        )

        query = self.client.build_bbox_query(
            min_lat=min_lat,
            min_lon=min_lon,
            max_lat=max_lat,
            max_lon=max_lon,
            limit=limit,
            include_boundary=include_boundary,
        )
        data = self.client.execute_query(query)
        elements = data.get("elements", [])

        stats = self._process_elements(
            elements=elements,
            scope=scope_str,
            default_country=country_code.upper(),
            dry_run=dry_run,
            start_time=start_time,
        )

        self._log_completion(stats)
        return stats

    def ingest_raw_elements(
        self,
        elements: list[dict[str, Any]],
        default_country: str = "IN",
        dry_run: bool = False,
        scope: str = "custom_fixture",
    ) -> ForestIngestionStats:
        """Process pre-fetched raw Overpass elements.

        Useful for testing fixtures and offline data.
        """
        start_time = time.time()
        stats = self._process_elements(
            elements=elements,
            scope=scope,
            default_country=default_country.upper(),
            dry_run=dry_run,
            start_time=start_time,
        )
        self._log_completion(stats)
        return stats

    def _process_elements(
        self,
        elements: list[dict[str, Any]],
        scope: str,
        default_country: str,
        dry_run: bool,
        start_time: float,
    ) -> ForestIngestionStats:
        """Internal processing pipeline with deduplication and validation."""
        objects_received = len(elements)
        polygons_parsed = 0
        invalid_geometries = 0
        geometry_repairs = 0
        inserted = 0
        updated = 0
        duplicates_skipped = 0
        rejected = 0

        # Track seen OSM identities to handle intra-batch duplicate elements
        seen_in_batch: set[str] = set()

        for elem in elements:
            candidate = parse_osm_element(elem, default_country_code=default_country)
            if candidate is None:
                rejected += 1
                continue

            if not candidate.norm_result.is_valid:
                invalid_geometries += 1
                rejected += 1
                continue

            polygons_parsed += 1

            if candidate.norm_result.is_repaired:
                geometry_repairs += 1

            # Check intra-batch duplicate
            if candidate.osm_identity in seen_in_batch:
                duplicates_skipped += 1
                continue
            seen_in_batch.add(candidate.osm_identity)

            record = candidate_to_forest_record(candidate)
            if record is None:
                rejected += 1
                continue

            if dry_run:
                # In dry-run mode, check if it would be an insert or update
                existing = self.repository.get_forest_by_osm_identity(
                    record.osm_identity
                )
                if existing:
                    updated += 1
                else:
                    inserted += 1
            else:
                is_new = self.repository.save_forest(record)
                if is_new:
                    inserted += 1
                else:
                    updated += 1

        elapsed = round(time.time() - start_time, 3)

        return ForestIngestionStats(
            scope=scope,
            source="OPENSTREETMAP",
            objects_received=objects_received,
            polygons_parsed=polygons_parsed,
            invalid_geometries=invalid_geometries,
            geometry_repairs=geometry_repairs,
            inserted=inserted,
            updated=updated,
            duplicates_skipped=duplicates_skipped,
            rejected=rejected,
            is_dry_run=dry_run,
            duration_seconds=elapsed,
        )

    def _log_completion(self, stats: ForestIngestionStats) -> None:
        """Log structured ingestion statistics matching engineering specifications."""
        log_with_context(
            logger,
            logging.INFO,
            f"[FOREST_INGEST] Completed for {stats.scope} (dry_run={stats.is_dry_run})",
            context={
                "scope": stats.scope,
                "source": stats.source,
                "objects_received": stats.objects_received,
                "polygons_parsed": stats.polygons_parsed,
                "invalid_geometries": stats.invalid_geometries,
                "geometry_repairs": stats.geometry_repairs,
                "inserted": stats.inserted,
                "updated": stats.updated,
                "duplicates_skipped": stats.duplicates_skipped,
                "rejected": stats.rejected,
                "duration_seconds": stats.duration_seconds,
            },
        )
