"""Parser for OpenStreetMap Overpass JSON elements into structured geometries."""

from typing import Any

from packages.data.forests.normalizer import (
    GeometryNormalizationResult,
    map_osm_tags_to_forest_type,
    normalize_and_validate_geometry,
)
from packages.logging import get_logger
from packages.schemas.forest import ForestAreaRecord

logger = get_logger("packages.data.forests.parser")


class ParsedForestCandidate:
    """Intermediate candidate extracted from raw OSM element before persistence."""

    def __init__(
        self,
        *,
        osm_id: int,
        osm_type: str,
        osm_identity: str,
        name: str | None,
        name_en: str | None,
        country_code: str,
        region: str | None,
        tags: dict[str, str],
        norm_result: GeometryNormalizationResult,
    ) -> None:
        self.osm_id = osm_id
        self.osm_type = osm_type
        self.osm_identity = osm_identity
        self.name = name
        self.name_en = name_en
        self.country_code = country_code
        self.region = region
        self.tags = tags
        self.norm_result = norm_result


def parse_way_geometry(
    geometry_nodes: list[dict[str, float]],
) -> list[list[list[float]]] | None:
    """Parse a way's geometry node list into GeoJSON Polygon coordinates."""
    if not geometry_nodes or len(geometry_nodes) < 3:
        return None

    ring: list[list[float]] = []
    for node in geometry_nodes:
        lon = float(node.get("lon", 0.0))
        lat = float(node.get("lat", 0.0))
        ring.append([lon, lat])

    # Ensure ring is closed
    if ring[0] != ring[-1]:
        ring.append(ring[0])

    if len(ring) < 4:
        return None

    return [ring]


def parse_relation_geometry(
    members: list[dict[str, Any]],
) -> tuple[list[Any], str] | None:
    """Parse relation members with geometries into coordinates."""
    outer_rings: list[list[list[float]]] = []
    inner_rings: list[list[list[float]]] = []

    for member in members:
        role = member.get("role", "")
        geometry = member.get("geometry", [])
        if not geometry or len(geometry) < 3:
            continue

        ring = [[float(pt["lon"]), float(pt["lat"])] for pt in geometry]
        if len(ring) < 3:
            continue
        # Ensure closed ring
        if ring[0] != ring[-1]:
            ring.append(ring[0])

        if role == "outer" or not role:
            outer_rings.append(ring)
        elif role == "inner":
            inner_rings.append(ring)

    if not outer_rings:
        return None

    if len(outer_rings) == 1:
        # Single polygon with possible inner rings (holes)
        coords = [outer_rings[0], *inner_rings]
        return coords, "Polygon"

    # MultiPolygon: list of [outer, *inners] polygons
    polygons: list[list[list[list[float]]]] = []
    for outer in outer_rings:
        polygons.append([outer])
    return polygons, "MultiPolygon"


def parse_osm_element(
    element: dict[str, Any],
    default_country_code: str = "IN",
) -> ParsedForestCandidate | None:
    """Parse a raw OSM element from Overpass JSON into a ParsedForestCandidate.

    Args:
        element: Dict containing raw OSM element payload.
        default_country_code: Fallback ISO country code if not in tags.

    Returns:
        ParsedForestCandidate if valid geometry, or None if rejected.
    """
    elem_type = element.get("type")
    elem_id = element.get("id")
    if not elem_type or elem_id is None or elem_type not in ("way", "relation"):
        return None

    tags = element.get("tags", {})
    osm_id = int(elem_id)
    osm_identity = f"{elem_type}:{osm_id}"

    # Extract names and geographic metadata
    name = tags.get("name")
    name_en = tags.get("name:en")
    country_code = tags.get("addr:country", default_country_code).upper()
    region = tags.get("addr:state") or tags.get("is_in:state") or tags.get("region")

    # Parse coordinates based on element type
    raw_coords: list[Any] | None = None
    geom_type = "Polygon"

    if elem_type == "way":
        raw_coords = parse_way_geometry(element.get("geometry", []))
    elif elem_type == "relation":
        res = parse_relation_geometry(element.get("members", []))
        if res is not None:
            raw_coords, geom_type = res

    if raw_coords is None:
        return None

    # Validate and normalize geometry
    norm_result = normalize_and_validate_geometry(raw_coords, geometry_type=geom_type)

    return ParsedForestCandidate(
        osm_id=osm_id,
        osm_type=elem_type,
        osm_identity=osm_identity,
        name=name,
        name_en=name_en,
        country_code=country_code,
        region=region,
        tags=tags,
        norm_result=norm_result,
    )


def candidate_to_forest_record(
    candidate: ParsedForestCandidate,
) -> ForestAreaRecord | None:
    """Convert a validated ParsedForestCandidate into a canonical ForestAreaRecord."""
    if not candidate.norm_result.is_valid or candidate.norm_result.geometry is None:
        return None
    if candidate.norm_result.centroid is None:
        return None

    forest_type, osm_tag = map_osm_tags_to_forest_type(candidate.tags)

    # Filter metadata tags to preserve useful attributes without bloat
    preserved_keys = {
        "leaf_type",
        "leaf_cycle",
        "operator",
        "protect_class",
        "wood",
        "description",
        "natural",
        "landuse",
        "boundary",
        "leisure",
        "wikidata",
        "wikipedia",
    }
    filtered_tags = {k: v for k, v in candidate.tags.items() if k in preserved_keys}

    return ForestAreaRecord(
        forest_id=f"forest_{candidate.osm_type}_{candidate.osm_id}",
        osm_id=candidate.osm_id,
        osm_type=candidate.osm_type,
        osm_identity=candidate.osm_identity,
        name=candidate.name,
        name_en=candidate.name_en,
        country_code=candidate.country_code,
        region=candidate.region,
        forest_type=forest_type,
        osm_tag=osm_tag,
        geometry=candidate.norm_result.geometry,
        centroid=candidate.norm_result.centroid,
        area_km2=candidate.norm_result.area_km2,
        metadata_tags=filtered_tags,
        source="openstreetmap",
        is_repaired=candidate.norm_result.is_repaired,
    )
