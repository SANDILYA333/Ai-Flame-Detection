"""Application service for querying canonical forest intelligence data."""

import contextlib

from packages.data.forests.normalizer import normalize_and_validate_geometry
from packages.data.forests.repository import (
    ForestRepositoryProtocol,
    get_forest_repository,
)
from packages.errors import ErrorCode, NotFoundError, ValidationError
from packages.schemas.forest import ForestAreaRecord, ForestType
from services.api.schemas.forests import (
    ForestDetailResponse,
    NearbyForestItemResponse,
    NearbyForestsListResponse,
)
from services.api.schemas.layers import (
    GeoJsonFeature,
    GeoJsonFeatureCollection,
    GeoJsonGeometry,
)

# Canonical baseline forest reserves (e.g. Gir / Western Ghats / Corbett)
_INITIAL_FOREST_FIXTURES: list[dict] = [
    {
        "osm_id": 1001,
        "osm_type": "relation",
        "name": "Gir National Park & Wildlife Sanctuary",
        "name_en": "Gir Forest Reserve",
        "country_code": "IN",
        "region": "Gujarat",
        "forest_type": ForestType.PROTECTED_RESERVE,
        "osm_tag": "boundary=national_park",
        "raw_coords": [
            [
                [70.50, 21.05],
                [70.90, 21.05],
                [70.95, 21.30],
                [70.55, 21.35],
                [70.50, 21.05],
            ]
        ],
        "tags": {
            "name": "Gir National Park & Wildlife Sanctuary",
            "leaf_type": "broadleaved",
            "leaf_cycle": "deciduous",
            "protect_class": "2",
            "operator": "Gujarat Forest Department",
        },
    },
    {
        "osm_id": 1002,
        "osm_type": "relation",
        "name": "Sundarbans Biosphere Reserve",
        "name_en": "Sundarbans Mangrove Reserve",
        "country_code": "IN",
        "region": "West Bengal",
        "forest_type": ForestType.NATURAL_WOOD,
        "osm_tag": "natural=wood",
        "raw_coords": [
            [
                [88.40, 21.60],
                [89.10, 21.60],
                [89.15, 22.00],
                [88.45, 22.05],
                [88.40, 21.60],
            ]
        ],
        "tags": {
            "name": "Sundarbans Biosphere Reserve",
            "leaf_type": "mangrove",
            "leaf_cycle": "evergreen",
            "protect_class": "1a",
        },
    },
    {
        "osm_id": 1003,
        "osm_type": "relation",
        "name": "Jim Corbett Tiger Reserve",
        "name_en": "Jim Corbett National Park",
        "country_code": "IN",
        "region": "Uttarakhand",
        "forest_type": ForestType.PROTECTED_RESERVE,
        "osm_tag": "boundary=national_park",
        "raw_coords": [
            [
                [78.70, 29.45],
                [79.10, 29.45],
                [79.15, 29.70],
                [78.75, 29.75],
                [78.70, 29.45],
            ]
        ],
        "tags": {
            "name": "Jim Corbett Tiger Reserve",
            "leaf_type": "needleleaved",
            "leaf_cycle": "mixed",
            "protect_class": "2",
        },
    },
    {
        "osm_id": 1004,
        "osm_type": "way",
        "name": "Western Ghats High Wilderness Tract",
        "name_en": "Anamalai Forest Corridor",
        "country_code": "IN",
        "region": "Kerala / Tamil Nadu",
        "forest_type": ForestType.LANDUSE_FOREST,
        "osm_tag": "landuse=forest",
        "raw_coords": [
            [
                [76.80, 10.15],
                [77.20, 10.15],
                [77.25, 10.45],
                [76.85, 10.50],
                [76.80, 10.15],
            ]
        ],
        "tags": {
            "name": "Western Ghats High Wilderness Tract",
            "leaf_type": "broadleaved",
            "leaf_cycle": "evergreen",
            "managed": "yes",
        },
    },
    {
        "osm_id": 1005,
        "osm_type": "way",
        "name": "Kaziranga Forest Tract",
        "name_en": "Kaziranga National Forest",
        "country_code": "IN",
        "region": "Assam",
        "forest_type": ForestType.PROTECTED_RESERVE,
        "osm_tag": "boundary=national_park",
        "raw_coords": [
            [
                [93.10, 26.50],
                [93.50, 26.50],
                [93.55, 26.80],
                [93.15, 26.85],
                [93.10, 26.50],
            ]
        ],
        "tags": {
            "name": "Kaziranga Forest Tract",
            "leaf_type": "broadleaved",
            "leaf_cycle": "evergreen",
        },
    },
    {
        "osm_id": 1006,
        "osm_type": "relation",
        "name": "Nilgiri Biosphere Reserve",
        "name_en": "Mudumalai & Nilgiri Wilderness",
        "country_code": "IN",
        "region": "Tamil Nadu / Karnataka",
        "forest_type": ForestType.PROTECTED_RESERVE,
        "osm_tag": "boundary=national_park",
        "raw_coords": [
            [
                [76.45, 11.45],
                [76.85, 11.45],
                [76.90, 11.80],
                [76.50, 11.85],
                [76.45, 11.45],
            ]
        ],
        "tags": {
            "name": "Nilgiri Biosphere Reserve",
            "leaf_type": "broadleaved",
            "protect_class": "1b",
        },
    },
    {
        "osm_id": 2001,
        "osm_type": "relation",
        "name": "Amazon Tapajós National Forest",
        "name_en": "Floresta Nacional do Tapajós",
        "country_code": "BR",
        "region": "Pará",
        "forest_type": ForestType.NATURAL_WOOD,
        "osm_tag": "natural=wood",
        "raw_coords": [
            [
                [-55.20, -3.80],
                [-54.70, -3.80],
                [-54.65, -3.20],
                [-55.15, -3.20],
                [-55.20, -3.80],
            ]
        ],
        "tags": {
            "name": "Floresta Nacional do Tapajós",
            "leaf_type": "rainforest",
            "leaf_cycle": "evergreen",
        },
    },
    {
        "osm_id": 2002,
        "osm_type": "relation",
        "name": "Salonga National Park",
        "name_en": "Congo Rainforest Reserve",
        "country_code": "CD",
        "region": "Congo Basin",
        "forest_type": ForestType.PROTECTED_RESERVE,
        "osm_tag": "boundary=national_park",
        "raw_coords": [
            [
                [20.50, -2.50],
                [21.80, -2.50],
                [21.85, -1.50],
                [20.55, -1.50],
                [20.50, -2.50],
            ]
        ],
        "tags": {
            "name": "Salonga National Park",
            "leaf_type": "rainforest",
        },
    },
    {
        "osm_id": 2003,
        "osm_type": "relation",
        "name": "Yellowstone & Shoshone National Forest",
        "name_en": "Yellowstone Wilderness Tract",
        "country_code": "US",
        "region": "Wyoming",
        "forest_type": ForestType.PROTECTED_RESERVE,
        "osm_tag": "boundary=national_park",
        "raw_coords": [
            [
                [-111.10, 44.15],
                [-110.00, 44.15],
                [-109.95, 45.05],
                [-111.05, 45.05],
                [-111.10, 44.15],
            ]
        ],
        "tags": {
            "name": "Yellowstone & Shoshone National Forest",
            "leaf_type": "needleleaved",
            "protect_class": "2",
        },
    },
    {
        "osm_id": 2004,
        "osm_type": "way",
        "name": "Schwarzwald National Park",
        "name_en": "Black Forest Reserve",
        "country_code": "DE",
        "region": "Baden-Württemberg",
        "forest_type": ForestType.NATURAL_WOOD,
        "osm_tag": "natural=wood",
        "raw_coords": [
            [
                [8.10, 48.40],
                [8.45, 48.40],
                [8.50, 48.70],
                [8.15, 48.70],
                [8.10, 48.40],
            ]
        ],
        "tags": {
            "name": "Schwarzwald National Park",
            "leaf_type": "mixed",
        },
    },
    {
        "osm_id": 2005,
        "osm_type": "relation",
        "name": "Daintree Rainforest Sanctuary",
        "name_en": "Daintree National Park",
        "country_code": "AU",
        "region": "Queensland",
        "forest_type": ForestType.NATURAL_WOOD,
        "osm_tag": "natural=wood",
        "raw_coords": [
            [
                [145.20, -16.30],
                [145.55, -16.30],
                [145.60, -15.95],
                [145.25, -15.95],
                [145.20, -16.30],
            ]
        ],
        "tags": {
            "name": "Daintree Rainforest Sanctuary",
            "leaf_type": "tropical_rainforest",
        },
    },
]


def _bootstrap_initial_forests(repo: ForestRepositoryProtocol) -> None:
    """Pre-load baseline canonical forest reserves if repository is empty."""
    if repo.count() > 0:
        return

    for fix in _INITIAL_FOREST_FIXTURES:
        norm = normalize_and_validate_geometry(
            fix["raw_coords"], geometry_type="Polygon"
        )
        if norm.is_valid and norm.geometry is not None and norm.centroid is not None:
            rec = ForestAreaRecord(
                forest_id=f"forest_{fix['osm_type']}_{fix['osm_id']}",
                osm_id=fix["osm_id"],
                osm_type=fix["osm_type"],
                osm_identity=f"{fix['osm_type']}:{fix['osm_id']}",
                name=fix["name"],
                name_en=fix.get("name_en"),
                country_code=fix["country_code"],
                region=fix.get("region"),
                forest_type=fix["forest_type"],
                osm_tag=fix["osm_tag"],
                geometry=norm.geometry,
                centroid=norm.centroid,
                area_km2=norm.area_km2,
                metadata_tags=fix.get("tags", {}),
                source="openstreetmap",
                is_repaired=norm.is_repaired,
            )
            repo.save_forest(rec)


class ForestQueryService:
    """Application query service exposing forest intelligence endpoints."""

    @classmethod
    def get_repository(cls) -> ForestRepositoryProtocol:
        repo = get_forest_repository()
        _bootstrap_initial_forests(repo)
        return repo

    @classmethod
    def query_forests_geojson(
        cls,
        *,
        country: str | None = None,
        bbox: str | None = None,
        min_lat: float | None = None,
        max_lat: float | None = None,
        min_lon: float | None = None,
        max_lon: float | None = None,
        forest_type: str | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> GeoJsonFeatureCollection:
        """Query forests and return RFC 7946 GeoJSON FeatureCollection."""
        repo = cls.get_repository()

        # Parse bbox if provided as string "min_lon,min_lat,max_lon,max_lat"
        if bbox:
            parts = [float(p.strip()) for p in bbox.split(",")]
            if len(parts) != 4:
                raise ValidationError(
                    "bbox parameter must have 4 float values: "
                    "min_lon,min_lat,max_lon,max_lat."
                )
            min_lon, min_lat, max_lon, max_lat = parts

        if (min_lat is not None and max_lat is not None) and (min_lat > max_lat):
            raise ValidationError("min_lat cannot be greater than max_lat.")
        if (min_lon is not None and max_lon is not None) and (min_lon > max_lon):
            raise ValidationError("min_lon cannot be greater than max_lon.")

        enum_forest_type: ForestType | None = None
        if forest_type:
            with contextlib.suppress(ValueError):
                enum_forest_type = ForestType(forest_type.lower())

        records, _ = repo.list_forests(
            country_code=country,
            min_lat=min_lat,
            max_lat=max_lat,
            min_lon=min_lon,
            max_lon=max_lon,
            forest_type=enum_forest_type,
            search=search,
            limit=limit,
            offset=offset,
        )

        features: list[GeoJsonFeature] = []
        for rec in records:
            feature = GeoJsonFeature(
                id=rec.forest_id,
                geometry=GeoJsonGeometry(
                    type=rec.geometry.type,
                    coordinates=rec.geometry.coordinates,
                ),
                properties={
                    "forest_id": rec.forest_id,
                    "osm_id": rec.osm_id,
                    "osm_type": rec.osm_type,
                    "osm_identity": rec.osm_identity,
                    "name": rec.name or rec.name_en or "Unnamed Forest Area",
                    "name_en": rec.name_en,
                    "country_code": rec.country_code,
                    "region": rec.region,
                    "forest_type": rec.forest_type.value,
                    "osm_tag": rec.osm_tag,
                    "area_km2": rec.area_km2,
                    "centroid": {
                        "latitude": rec.centroid.latitude,
                        "longitude": rec.centroid.longitude,
                    },
                    "metadata": rec.metadata_tags,
                    "source": rec.source,
                    "is_repaired": rec.is_repaired,
                },
            )
            features.append(feature)

        bbox_meta = (
            [min_lon, min_lat, max_lon, max_lat]
            if min_lon is not None
            and min_lat is not None
            and max_lon is not None
            and max_lat is not None
            else None
        )

        return GeoJsonFeatureCollection(
            features=features,
            bbox=bbox_meta,
        )

    @classmethod
    def get_forest_by_id(cls, forest_id: str) -> ForestDetailResponse:
        """Retrieve canonical forest detail by forest_id."""
        repo = cls.get_repository()
        record = repo.get_forest_by_id(forest_id)
        if record is None:
            raise NotFoundError(
                message=f"Forest area record '{forest_id}' not found.",
                code=ErrorCode.RESOURCE_NOT_FOUND,
            )

        return ForestDetailResponse(
            id=record.forest_id,
            osm_id=record.osm_id,
            osm_type=record.osm_type,
            osm_identity=record.osm_identity,
            name=record.name,
            name_en=record.name_en,
            country_code=record.country_code,
            region=record.region,
            forest_type=record.forest_type,
            osm_tag=record.osm_tag,
            area_km2=record.area_km2,
            centroid=record.centroid,
            geometry={
                "type": record.geometry.type,
                "coordinates": record.geometry.coordinates,
            },
            metadata=record.metadata_tags,
            source=record.source,
            is_repaired=record.is_repaired,
        )

    @classmethod
    def find_nearby_forests(
        cls,
        latitude: float,
        longitude: float,
        radius_km: float = 25.0,
        limit: int = 50,
    ) -> NearbyForestsListResponse:
        """Search nearby forests ordered by geodesic distance."""
        if not (-90.0 <= latitude <= 90.0):
            raise ValidationError("Latitude must be between -90.0 and 90.0.")
        if not (-180.0 <= longitude <= 180.0):
            raise ValidationError("Longitude must be between -180.0 and 180.0.")
        if radius_km <= 0.0 or radius_km > 2000.0:
            raise ValidationError("radius_km must be between 0.1 and 2000.0 km.")

        repo = cls.get_repository()
        items = repo.find_nearby_forests(
            lat=latitude,
            lon=longitude,
            radius_km=radius_km,
            limit=limit,
        )

        response_items = [
            NearbyForestItemResponse(
                id=item.forest_id,
                osm_identity=item.osm_identity,
                name=item.name,
                country_code=item.country_code,
                forest_type=item.forest_type.value,
                osm_tag=item.osm_tag,
                distance_km=item.distance_km,
                area_km2=item.area_km2,
                centroid=item.centroid,
            )
            for item in items
        ]

        return NearbyForestsListResponse(
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            total_found=len(response_items),
            forests=response_items,
        )
