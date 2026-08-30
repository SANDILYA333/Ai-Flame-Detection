"""Normalization, geometry extraction, and tag mapping for external context."""

import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Any

from packages.data.context.errors import ContextValidationError
from packages.geospatial.coordinates import validate_wgs84_coordinates
from packages.geospatial.envelope import (
    calculate_bounding_box,
    calculate_spatial_centroid,
)
from packages.schemas.common import BoundingBox, Coordinate
from packages.schemas.enums import ContextType


def map_tags_to_context_type(tags: dict[str, Any]) -> ContextType:
    """Map OpenStreetMap and external metadata tags to canonical ContextType.

    Args:
        tags: Dictionary of key-value metadata tags.

    Returns:
        ContextType: Normalized canonical context category.
    """
    clean_tags = {
        str(k).strip().lower(): str(v).strip().lower() for k, v in tags.items() if v
    }

    # 1. Power generation and transmission
    sources = ("coal", "gas", "nuclear", "hydro", "solar")
    if (
        "power" in clean_tags
        or clean_tags.get("amenity") == "power"
        or clean_tags.get("plant:source") in sources
    ):
        return ContextType.POWER

    # 2. Oil, gas, refinery, and flaring infrastructure
    industrial_val = clean_tags.get("industrial", "")
    man_made_val = clean_tags.get("man_made", "")
    if (
        industrial_val in ("refinery", "oil", "gas", "petrochemical", "lng")
        or man_made_val in ("flare", "petroleum_well", "pipeline")
        or "refinery" in clean_tags.get("name", "")
        or "petrochemical" in clean_tags.get("name", "")
    ):
        return ContextType.OIL_GAS

    # 3. Mining and quarrying
    if (
        clean_tags.get("landuse") == "quarry"
        or industrial_val == "mining"
        or "mine" in clean_tags
        or clean_tags.get("resource") in ("coal", "iron", "bauxite", "lignite")
    ):
        return ContextType.MINING

    # 4. General Industrial
    if (
        clean_tags.get("landuse") in ("industrial", "port", "depot")
        or clean_tags.get("building") == "industrial"
        or "industrial" in clean_tags
        or industrial_val in ("steel", "aluminium", "cement", "chemical", "factory")
    ):
        return ContextType.INDUSTRIAL

    # 5. Agricultural
    if clean_tags.get("landuse") in (
        "farmland",
        "farmyard",
        "orchard",
        "vineyard",
        "crop",
    ) or clean_tags.get("agricultural") in ("yes", "farm"):
        return ContextType.AGRICULTURAL

    # 6. Forest and vegetation
    if clean_tags.get("landuse") in ("forest", "wood") or clean_tags.get("natural") in (
        "wood",
        "scrub",
        "forest",
        "tree_row",
    ):
        return ContextType.FOREST_VEGETATION

    # 7. Urban and residential
    if clean_tags.get("landuse") in (
        "residential",
        "commercial",
        "retail",
    ) or clean_tags.get("building") in ("residential", "commercial", "apartments"):
        return ContextType.URBAN

    return ContextType.OTHER


def map_fuel_or_industry_to_context_type(
    industry_type: str | None,
    fuel_type: str | None = None,
) -> ContextType:
    """Map industrial catalog categories (fuel / facility type) to ContextType."""
    val = f"{industry_type or ''} {fuel_type or ''}".strip().lower()

    if any(
        w in val
        for w in (
            "power",
            "coal",
            "gas",
            "hydro",
            "nuclear",
            "solar",
            "wind",
            "thermal",
            "generator",
        )
    ):
        return ContextType.POWER

    if any(
        w in val for w in ("refinery", "oil", "petrochemical", "flare", "lng", "crude")
    ):
        return ContextType.OIL_GAS

    if any(w in val for w in ("mine", "quarry", "bauxite", "lignite", "iron ore")):
        return ContextType.MINING

    if any(w in val for w in ("farm", "agriculture", "stubble", "crop", "paddy")):
        return ContextType.AGRICULTURAL

    if any(w in val for w in ("forest", "woodland", "scrub", "trees")):
        return ContextType.FOREST_VEGETATION

    if any(w in val for w in ("urban", "residential", "city", "commercial")):
        return ContextType.URBAN

    return ContextType.INDUSTRIAL


def normalize_geojson_geometry(
    geometry_dict: dict[str, Any],
) -> tuple[Coordinate, BoundingBox | None]:
    """Extract centroid Coordinate and optional BoundingBox from GeoJSON geometry.

    Args:
        geometry_dict: GeoJSON geometry dictionary (Point, Polygon, or MultiPolygon).

    Returns:
        tuple[Coordinate, BoundingBox | None]: Representative coordinate and envelope.

    Raises:
        ContextValidationError: If geometry is unparseable or out of bounds.
    """
    if not isinstance(geometry_dict, dict):
        raise ContextValidationError("Geometry must be a dictionary object.")

    geom_type = geometry_dict.get("type")
    coords = geometry_dict.get("coordinates")

    if not geom_type or coords is None:
        raise ContextValidationError("Geometry missing 'type' or 'coordinates'.")

    geom_type_upper = geom_type.strip().upper()

    if geom_type_upper == "POINT":
        if not isinstance(coords, (list, tuple)) or len(coords) < 2:
            raise ContextValidationError(
                f"Point coordinates must have >= 2 elements [lon, lat], got {coords}."
            )
        lon_raw, lat_raw = coords[0], coords[1]
        try:
            lat_f = float(lat_raw)
            lon_f = float(lon_raw)
        except (ValueError, TypeError) as exc:
            raise ContextValidationError(
                f"Non-numeric Point coordinates [{lon_raw}, {lat_raw}]."
            ) from exc

        lat_v, lon_v = validate_wgs84_coordinates(lat_f, lon_f)
        return Coordinate(latitude=lat_v, longitude=lon_v), None

    if geom_type_upper in ("POLYGON", "MULTIPOLYGON"):
        flat_points: list[tuple[float, float]] = []

        def _extract_rings(ring_data: Any) -> None:
            if isinstance(ring_data, (list, tuple)) and ring_data:
                if isinstance(ring_data[0], (int, float)):
                    if len(ring_data) >= 2:
                        try:
                            lon_f = float(ring_data[0])
                            lat_f = float(ring_data[1])
                            lat_v, lon_v = validate_wgs84_coordinates(lat_f, lon_f)
                            flat_points.append((lat_v, lon_v))
                        except Exception as exc:
                            raise ContextValidationError(
                                f"Invalid coordinate in polygon ring {ring_data}: {exc}"
                            ) from exc
                else:
                    for sub in ring_data:
                        _extract_rings(sub)

        _extract_rings(coords)

        if not flat_points:
            raise ContextValidationError(
                f"Empty or invalid {geom_type} coordinates payload."
            )

        bbox = calculate_bounding_box(flat_points)
        c_lat, c_lon = calculate_spatial_centroid(flat_points)
        centroid = Coordinate(latitude=c_lat, longitude=c_lon)
        return centroid, bbox

    raise ContextValidationError(f"Unsupported GeoJSON geometry type '{geom_type}'.")


def compute_context_raw_hash(raw_dict: dict[str, Any]) -> str:
    """Compute deterministic cryptographic SHA-256 hash over raw feature dictionary."""
    normalized_dict: dict[str, Any] = {}
    for k in sorted(raw_dict.keys()):
        v = raw_dict[k]
        if isinstance(v, str):
            normalized_dict[k] = v.strip()
        else:
            normalized_dict[k] = v

    canonical_json = json.dumps(
        normalized_dict, sort_keys=True, ensure_ascii=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def compute_canonical_feature_id(
    provider: str, raw_id: str | None, raw_hash: str
) -> str:
    """Compute content-addressable feature identifier."""
    clean_provider = provider.strip().lower()
    if raw_id and raw_id.strip():
        # Sanitize raw ID (alphanumeric, underscore, hyphen)
        sanitized = re.sub(r"[^a-zA-Z0-9_\-]", "_", raw_id.strip())
        return f"ctx_{clean_provider}_{sanitized}"

    return f"ctx_{clean_provider}_{raw_hash[:12]}"


def parse_optional_datetime(dt_str: str | None) -> datetime | None:
    """Parse optional ISO timestamp or 4-digit year into UTC datetime."""
    if not dt_str or not dt_str.strip():
        return None

    clean = dt_str.strip()
    # Check 4-digit year format (e.g. '2018')
    if re.match(r"^\d{4}$", clean):
        year = int(clean)
        return datetime(year, 1, 1, 0, 0, 0, tzinfo=UTC)

    # Check ISO format
    try:
        dt = datetime.fromisoformat(clean.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except Exception:
        return None
