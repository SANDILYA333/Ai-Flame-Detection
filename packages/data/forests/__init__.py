"""OpenStreetMap Forest Intelligence and geospatial ingestion package (Phase 1)."""

from packages.data.forests.client import ForestOverpassClient, OverpassApiError
from packages.data.forests.normalizer import (
    GeometryNormalizationResult,
    compute_geodesic_polygon_area_km2,
    map_osm_tags_to_forest_type,
    normalize_and_validate_geometry,
)
from packages.data.forests.parser import (
    ParsedForestCandidate,
    candidate_to_forest_record,
    parse_osm_element,
    parse_relation_geometry,
    parse_way_geometry,
)
from packages.data.forests.repository import (
    ForestRepositoryProtocol,
    InMemoryForestRepository,
    get_forest_repository,
)
from packages.data.forests.service import ForestIngestionService
from packages.data.forests.threat_service import (
    ForestThreatService,
    get_forest_threat_service,
)

__all__ = [
    "ForestIngestionService",
    "ForestOverpassClient",
    "ForestRepositoryProtocol",
    "ForestThreatService",
    "GeometryNormalizationResult",
    "InMemoryForestRepository",
    "OverpassApiError",
    "ParsedForestCandidate",
    "candidate_to_forest_record",
    "compute_geodesic_polygon_area_km2",
    "get_forest_repository",
    "get_forest_threat_service",
    "map_osm_tags_to_forest_type",
    "normalize_and_validate_geometry",
    "parse_osm_element",
    "parse_relation_geometry",
    "parse_way_geometry",
]
