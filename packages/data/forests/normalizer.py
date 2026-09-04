"""Geospatial normalization, Shapely geometry validation, and area computation."""

import math
from typing import Any

from shapely.geometry import MultiPolygon, Polygon, mapping, shape
from shapely.validation import make_valid

from packages.schemas.common import Coordinate
from packages.schemas.forest import ForestGeometry, ForestType

WGS84_RADIUS_METERS = 6371008.8  # Earth mean radius in meters


def compute_geodesic_polygon_area_km2(geom: Polygon | MultiPolygon) -> float:
    """Calculate geodesic polygon surface area in km² using spherical excess.

    Uses the spherical excess geodesic surface integral on the WGS-84 sphere
    to calculate precise geographic surface area without distortion from
    degree projection.

    Args:
        geom: Valid Shapely Polygon or MultiPolygon in (lon, lat) degrees.

    Returns:
        Surface area in square kilometers (km²), non-negative float.
    """
    if geom.is_empty:
        return 0.0

    def _ring_spherical_area(ring_coords: list[tuple[float, float]]) -> float:
        """Compute spherical area of a single ring in square meters."""
        if len(ring_coords) < 4:
            return 0.0

        rad = math.pi / 180.0
        total = 0.0
        n = len(ring_coords)

        for i in range(n):
            lon1, lat1 = ring_coords[i]
            lon2, lat2 = ring_coords[(i + 1) % n]
            lon1_rad = lon1 * rad
            lat1_rad = lat1 * rad
            lon2_rad = lon2 * rad
            lat2_rad = lat2 * rad

            # Segment area contribution using spherical trapezoids
            total += (lon2_rad - lon1_rad) * (
                2.0 + math.sin(lat1_rad) + math.sin(lat2_rad)
            )

        area_sq_meters = abs(total * (WGS84_RADIUS_METERS**2) / 2.0)
        return area_sq_meters

    def _polygon_area(poly: Polygon) -> float:
        exterior_coords = list(poly.exterior.coords)
        exterior_area = _ring_spherical_area(exterior_coords)

        # Subtract interior rings (holes)
        interior_area = 0.0
        for interior in poly.interiors:
            interior_area += _ring_spherical_area(list(interior.coords))

        return max(0.0, exterior_area - interior_area)

    total_m2 = 0.0
    if isinstance(geom, Polygon):
        total_m2 = _polygon_area(geom)
    elif isinstance(geom, MultiPolygon):
        for p in geom.geoms:
            total_m2 += _polygon_area(p)

    return total_m2 / 1_000_000.0  # Convert m² to km²


class GeometryNormalizationResult:
    """Result of normalizing and repairing an OSM geometry."""

    def __init__(
        self,
        *,
        geometry: ForestGeometry | None,
        shapely_geom: Polygon | MultiPolygon | None,
        centroid: Coordinate | None,
        area_km2: float,
        is_valid: bool,
        is_repaired: bool,
        rejection_reason: str | None = None,
    ) -> None:
        self.geometry = geometry
        self.shapely_geom = shapely_geom
        self.centroid = centroid
        self.area_km2 = area_km2
        self.is_valid = is_valid
        self.is_repaired = is_repaired
        self.rejection_reason = rejection_reason


def normalize_and_validate_geometry(
    raw_coords: list[Any],
    geometry_type: str = "Polygon",
) -> GeometryNormalizationResult:
    """Validate, repair, and normalize raw coordinates into canonical GeoJSON geometry.

    Args:
        raw_coords: Coordinates array in GeoJSON format [[[lon, lat], ...]].
        geometry_type: 'Polygon' or 'MultiPolygon'.

    Returns:
        GeometryNormalizationResult with validity, repair status, centroid, and area.
    """
    if not raw_coords:
        return GeometryNormalizationResult(
            geometry=None,
            shapely_geom=None,
            centroid=None,
            area_km2=0.0,
            is_valid=False,
            is_repaired=False,
            rejection_reason="Empty coordinates provided",
        )

    try:
        raw_geo = {"type": geometry_type, "coordinates": raw_coords}
        geom = shape(raw_geo)
    except Exception as e:
        return GeometryNormalizationResult(
            geometry=None,
            shapely_geom=None,
            centroid=None,
            area_km2=0.0,
            is_valid=False,
            is_repaired=False,
            rejection_reason=f"Failed to construct geometry: {e}",
        )

    if geom.is_empty:
        return GeometryNormalizationResult(
            geometry=None,
            shapely_geom=None,
            centroid=None,
            area_km2=0.0,
            is_valid=False,
            is_repaired=False,
            rejection_reason="Geometry is empty",
        )

    is_repaired = False

    # Check validity and attempt safe repair if self-intersecting or malformed
    if not geom.is_valid:
        try:
            repaired = make_valid(geom)
            # If make_valid produced a GeometryCollection, extract polygon parts
            if repaired.geom_type == "GeometryCollection":
                polys = [
                    g
                    for g in repaired.geoms
                    if g.geom_type in ("Polygon", "MultiPolygon")
                ]
                if not polys:
                    return GeometryNormalizationResult(
                        geometry=None,
                        shapely_geom=None,
                        centroid=None,
                        area_km2=0.0,
                        is_valid=False,
                        is_repaired=False,
                        rejection_reason="Repair yielded no valid polygon components",
                    )
                if len(polys) == 1 and polys[0].geom_type == "Polygon":
                    geom = polys[0]
                else:
                    all_polys = []
                    for g in polys:
                        if g.geom_type == "Polygon":
                            all_polys.append(g)
                        elif g.geom_type == "MultiPolygon":
                            all_polys.extend(g.geoms)
                    geom = MultiPolygon(all_polys)
            elif repaired.geom_type in ("Polygon", "MultiPolygon"):
                geom = repaired
            else:
                return GeometryNormalizationResult(
                    geometry=None,
                    shapely_geom=None,
                    centroid=None,
                    area_km2=0.0,
                    is_valid=False,
                    is_repaired=False,
                    rejection_reason=(
                        f"Repaired geometry is non-polygonal: {repaired.geom_type}"
                    ),
                )
            is_repaired = True
        except Exception as e:
            return GeometryNormalizationResult(
                geometry=None,
                shapely_geom=None,
                centroid=None,
                area_km2=0.0,
                is_valid=False,
                is_repaired=False,
                rejection_reason=f"Geometry repair failed: {e}",
            )

    if not isinstance(geom, (Polygon, MultiPolygon)) or geom.is_empty:
        return GeometryNormalizationResult(
            geometry=None,
            shapely_geom=None,
            centroid=None,
            area_km2=0.0,
            is_valid=False,
            is_repaired=False,
            rejection_reason=f"Unsupported final geometry type: {type(geom)}",
        )

    # Calculate centroid
    centroid_pt = geom.centroid
    centroid_coord = Coordinate(latitude=centroid_pt.y, longitude=centroid_pt.x)

    # Compute geodesic area in km²
    area_km2 = compute_geodesic_polygon_area_km2(geom)

    # Export canonical GeoJSON geometry dictionary
    geo_dict = mapping(geom)
    forest_geo = ForestGeometry(
        type="MultiPolygon" if geom.geom_type == "MultiPolygon" else "Polygon",
        coordinates=geo_dict["coordinates"],
    )

    return GeometryNormalizationResult(
        geometry=forest_geo,
        shapely_geom=geom,
        centroid=centroid_coord,
        area_km2=round(area_km2, 4),
        is_valid=True,
        is_repaired=is_repaired,
    )


def map_osm_tags_to_forest_type(tags: dict[str, str]) -> tuple[ForestType, str]:
    """Classify OSM tags into ForestType and preserve primary OSM tag string."""
    natural_val = tags.get("natural", "").lower()
    landuse_val = tags.get("landuse", "").lower()
    boundary_val = tags.get("boundary", "").lower()
    leisure_val = tags.get("leisure", "").lower()

    if natural_val == "wood":
        return ForestType.NATURAL_WOOD, "natural=wood"
    if landuse_val == "forest":
        return ForestType.LANDUSE_FOREST, "landuse=forest"
    if boundary_val in ("forest", "national_park", "protected_area"):
        if boundary_val == "forest":
            return ForestType.BOUNDARY_FOREST, "boundary=forest"
        return ForestType.PROTECTED_RESERVE, f"boundary={boundary_val}"
    if leisure_val == "nature_reserve":
        return ForestType.PROTECTED_RESERVE, "leisure=nature_reserve"

    return ForestType.OTHER, f"natural={natural_val}" if natural_val else "forest_area"
