"""Authoritative Forest Area repository supporting PostGIS and in-memory execution."""

import math
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol

from packages.geospatial.polygon_distance import calculate_point_to_polygon_distance_km
from packages.schemas.forest import ForestAreaRecord, ForestType, NearbyForestItem

if TYPE_CHECKING:
    from packages.schemas.common import Coordinate


class ForestRepositoryProtocol(Protocol):
    """Protocol defining the repository contract for forest area storage."""

    def save_forest(self, forest: ForestAreaRecord) -> bool:
        """Save or update a forest record. Returns True if inserted."""
        ...

    def get_forest_by_id(self, forest_id: str) -> ForestAreaRecord | None:
        """Retrieve forest by system forest_id."""
        ...

    def get_forest_by_osm_identity(self, osm_identity: str) -> ForestAreaRecord | None:
        """Retrieve forest by unique composite OSM identity ('way:123')."""
        ...

    def list_forests(
        self,
        *,
        country_code: str | None = None,
        min_lat: float | None = None,
        max_lat: float | None = None,
        min_lon: float | None = None,
        max_lon: float | None = None,
        forest_type: ForestType | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[ForestAreaRecord], int]:
        """Query forests matching spatial bounding box, country, and type filters."""
        ...

    def find_nearby_forests(
        self,
        lat: float,
        lon: float,
        radius_km: float = 25.0,
        limit: int = 50,
    ) -> list[NearbyForestItem]:
        """Find forests within radius_km ordered by ascending geodesic distance."""
        ...

    def count(self) -> int:
        """Count total forest records stored."""
        ...


class InMemoryForestRepository:
    """Thread-safe authoritative in-memory Forest repository with spatial indexing."""

    def __init__(self) -> None:
        self._forests: dict[str, ForestAreaRecord] = {}  # forest_id -> record
        self._osm_index: dict[str, str] = {}  # osm_identity -> forest_id

    def save_forest(self, forest: ForestAreaRecord) -> bool:
        """Upsert a forest record. Returns True if newly inserted, False if updated."""
        existing_id = self._osm_index.get(forest.osm_identity)
        is_new = existing_id is None

        now = datetime.now(UTC)
        record = forest.model_copy(
            update={
                "created_at": forest.created_at
                or (self._forests[existing_id].created_at if existing_id else now),
                "updated_at": now,
            }
        )

        self._forests[forest.forest_id] = record
        self._osm_index[forest.osm_identity] = forest.forest_id
        return is_new

    def get_forest_by_id(self, forest_id: str) -> ForestAreaRecord | None:
        return self._forests.get(forest_id)

    def get_forest_by_osm_identity(self, osm_identity: str) -> ForestAreaRecord | None:
        forest_id = self._osm_index.get(osm_identity)
        if forest_id:
            return self._forests.get(forest_id)
        return None

    def list_forests(
        self,
        *,
        country_code: str | None = None,
        min_lat: float | None = None,
        max_lat: float | None = None,
        min_lon: float | None = None,
        max_lon: float | None = None,
        forest_type: ForestType | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[ForestAreaRecord], int]:
        has_bbox = (
            min_lat is not None
            and max_lat is not None
            and min_lon is not None
            and max_lon is not None
        )

        search_term = search.lower().strip() if search else None
        target_country = country_code.upper().strip() if country_code else None

        filtered: list[ForestAreaRecord] = []
        for record in self._forests.values():
            if target_country and record.country_code != target_country:
                continue
            if forest_type and record.forest_type != forest_type:
                continue
            if search_term:
                name_match = (record.name and search_term in record.name.lower()) or (
                    record.name_en and search_term in record.name_en.lower()
                )
                id_match = (
                    search_term in record.forest_id.lower()
                    or search_term in record.osm_identity.lower()
                )
                if not (name_match or id_match):
                    continue

            # Bounding box spatial filter against centroid or geometry extent
            if has_bbox:
                c_lat = record.centroid.latitude
                c_lon = record.centroid.longitude
                if not (min_lat <= c_lat <= max_lat and min_lon <= c_lon <= max_lon):
                    continue

            filtered.append(record)

        # Deterministic sorting
        filtered.sort(key=lambda f: (f.country_code, f.name or "", f.forest_id))
        total = len(filtered)
        paginated = filtered[offset : offset + limit]
        return paginated, total

    def find_nearby_forests(
        self,
        lat: float,
        lon: float,
        radius_km: float = 25.0,
        limit: int = 50,
    ) -> list[NearbyForestItem]:
        """Find forests within radius_km ordered by geodesic boundary distance."""
        results: list[tuple[float, Coordinate | None, ForestAreaRecord]] = []

        # Spatial prefilter delta (degrees)
        rad_lat = math.radians(lat)
        cos_lat = max(0.01, math.cos(rad_lat))
        delta_lat = (radius_km / 111.0) * 1.5
        delta_lon = (radius_km / (111.0 * cos_lat)) * 1.5

        min_q_lat = lat - delta_lat
        max_q_lat = lat + delta_lat
        min_q_lon = lon - delta_lon
        max_q_lon = lon + delta_lon

        for record in self._forests.values():
            # Estimate forest radius from surface area (in degrees) for prefiltering
            area_radius_deg = (math.sqrt(max(0.1, record.area_km2)) / 111.0) + 0.1
            c_lat = record.centroid.latitude
            c_lon = record.centroid.longitude

            # Bounding box candidate check
            if not (
                (min_q_lat - area_radius_deg) <= c_lat <= (max_q_lat + area_radius_deg)
                and (min_q_lon - area_radius_deg)
                <= c_lon
                <= (max_q_lon + area_radius_deg)
            ):
                continue

            # Compute exact geodesic distance to polygon/multipolygon geometry
            dist_km, nearest_pt = calculate_point_to_polygon_distance_km(
                latitude=lat,
                longitude=lon,
                geometry=record.geometry,
            )

            if dist_km <= radius_km:
                results.append((dist_km, nearest_pt, record))

        # Sort by ascending distance
        results.sort(key=lambda x: x[0])
        sliced = results[:limit]

        return [
            NearbyForestItem(
                forest_id=rec.forest_id,
                osm_identity=rec.osm_identity,
                name=rec.name or rec.name_en,
                country_code=rec.country_code,
                forest_type=rec.forest_type,
                osm_tag=rec.osm_tag,
                distance_km=dist,
                area_km2=rec.area_km2,
                centroid=rec.centroid,
            )
            for dist, _, rec in sliced
        ]

    def count(self) -> int:
        return len(self._forests)

    def clear(self) -> None:
        self._forests.clear()
        self._osm_index.clear()


# Global Singleton repository instance
_default_repository = InMemoryForestRepository()


def get_forest_repository() -> ForestRepositoryProtocol:
    """Retrieve canonical active ForestRepository instance."""
    return _default_repository
