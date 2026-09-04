"""Application service for industrial asset query and GeoJSON serialization."""

from typing import Any

from packages.data.industrial.loader import IndustrialDataLoader
from packages.errors import ErrorCode, NotFoundError, ValidationError
from packages.logging import get_logger
from packages.schemas.industrial_asset import (
    IndustrialAsset,
    IndustrialAssetCollection,
)
from services.api.schemas.layers import (
    GeoJsonFeature,
    GeoJsonFeatureCollection,
    GeoJsonGeometry,
)

logger = get_logger("services.api.services.industrial")


class IndustrialAssetQueryService:
    """Service providing query, filtering, and GeoJSON for industrial assets."""

    _cached_primary_collection: IndustrialAssetCollection | None = None
    _cached_all_collection: IndustrialAssetCollection | None = None

    @classmethod
    def get_collection(
        cls, include_expansion: bool = False
    ) -> IndustrialAssetCollection:
        """Retrieve canonical industrial asset collection with in-memory caching."""
        if include_expansion:
            if cls._cached_all_collection is None:
                logger.info(
                    "Loading primary facilities + expansion steel into memory cache"
                )
                loader = IndustrialDataLoader()
                primary_coll = loader.load_primary_master_facilities(
                    enrich=True, detect_duplicates=True
                )
                steel_assets = loader.load_expansion_steel_facilities()

                combined_assets = list(primary_coll.assets) + list(steel_assets)
                # Deterministic sorting
                combined_assets.sort(
                    key=lambda a: (
                        a.industry.value,
                        a.latitude,
                        a.longitude,
                        a.id,
                    )
                )
                from collections import Counter

                sources_summary = dict(Counter(a.source for a in combined_assets))
                industries_summary = dict(
                    Counter(a.industry.value for a in combined_assets)
                )

                cls._cached_all_collection = IndustrialAssetCollection(
                    assets=combined_assets,
                    total_count=len(combined_assets),
                    map_eligible_count=sum(
                        1 for a in combined_assets if a.is_map_eligible
                    ),
                    sources_summary=sources_summary,
                    industries_summary=industries_summary,
                    duplicate_candidates_count=primary_coll.duplicate_candidates_count,
                )
            return cls._cached_all_collection

        if cls._cached_primary_collection is None:
            logger.info(
                "Loading primary master industrial facilities into memory cache"
            )
            loader = IndustrialDataLoader()
            cls._cached_primary_collection = loader.load_primary_master_facilities(
                enrich=True, detect_duplicates=True
            )
        return cls._cached_primary_collection

    @classmethod
    def clear_cache(cls) -> None:
        """Reset cached collections (primarily for testing)."""
        cls._cached_primary_collection = None
        cls._cached_all_collection = None

    @staticmethod
    def _validate_bbox(
        min_lat: float | None,
        max_lat: float | None,
        min_lon: float | None,
        max_lon: float | None,
    ) -> None:
        """Validate bounding box coordinate consistency and ranges."""
        if min_lat is not None and not (-90.0 <= min_lat <= 90.0):
            raise ValidationError(
                message=f"min_lat {min_lat} must be between -90 and 90 degrees.",
                code=ErrorCode.VALIDATION_ERROR,
            )
        if max_lat is not None and not (-90.0 <= max_lat <= 90.0):
            raise ValidationError(
                message=f"max_lat {max_lat} must be between -90 and 90 degrees.",
                code=ErrorCode.VALIDATION_ERROR,
            )
        if min_lon is not None and not (-180.0 <= min_lon <= 180.0):
            raise ValidationError(
                message=f"min_lon {min_lon} must be between -180 and 180 degrees.",
                code=ErrorCode.VALIDATION_ERROR,
            )
        if max_lon is not None and not (-180.0 <= max_lon <= 180.0):
            raise ValidationError(
                message=f"max_lon {max_lon} must be between -180 and 180 degrees.",
                code=ErrorCode.VALIDATION_ERROR,
            )

        if min_lat is not None and max_lat is not None and min_lat > max_lat:
            raise ValidationError(
                message=(
                    f"min_lat ({min_lat}) cannot be greater than max_lat ({max_lat})."
                ),
                code=ErrorCode.VALIDATION_ERROR,
            )
        if min_lon is not None and max_lon is not None and min_lon > max_lon:
            raise ValidationError(
                message=(
                    f"min_lon ({min_lon}) cannot be greater than max_lon ({max_lon})."
                ),
                code=ErrorCode.VALIDATION_ERROR,
            )

    @classmethod
    def query_assets_geojson(
        cls,
        min_lat: float | None = None,
        max_lat: float | None = None,
        min_lon: float | None = None,
        max_lon: float | None = None,
        bbox_str: str | None = None,
        industry: str | None = None,
        status: str | None = None,
        state: str | None = None,
        include_expansion: bool = False,
        limit: int = 2000,
        offset: int = 0,
    ) -> GeoJsonFeatureCollection:
        """Query industrial assets and serialize as GeoJSON FeatureCollection."""
        # Parse bbox_str if provided ("min_lon,min_lat,max_lon,max_lat")
        if bbox_str is not None:
            parts = [p.strip() for p in bbox_str.split(",")]
            if len(parts) != 4:
                raise ValidationError(
                    message=(
                        "bbox must be formatted as 'min_lon,min_lat,max_lon,max_lat'"
                    ),
                    code=ErrorCode.VALIDATION_ERROR,
                )
            try:
                b_min_lon, b_min_lat, b_max_lon, b_max_lat = (
                    float(parts[0]),
                    float(parts[1]),
                    float(parts[2]),
                    float(parts[3]),
                )
                min_lon = b_min_lon if min_lon is None else min_lon
                min_lat = b_min_lat if min_lat is None else min_lat
                max_lon = b_max_lon if max_lon is None else max_lon
                max_lat = b_max_lat if max_lat is None else max_lat
            except ValueError as exc:
                raise ValidationError(
                    message=f"Invalid numeric values in bbox: {exc}",
                    code=ErrorCode.VALIDATION_ERROR,
                ) from exc

        cls._validate_bbox(min_lat, max_lat, min_lon, max_lon)

        collection = cls.get_collection(include_expansion=include_expansion)
        assets = collection.assets

        # 1. Spatial bounding box filter
        if min_lat is not None:
            assets = [a for a in assets if a.latitude >= min_lat]
        if max_lat is not None:
            assets = [a for a in assets if a.latitude <= max_lat]
        if min_lon is not None:
            assets = [a for a in assets if a.longitude >= min_lon]
        if max_lon is not None:
            assets = [a for a in assets if a.longitude <= max_lon]

        # 2. Industry filter
        if industry is not None:
            ind_target = industry.strip().lower()
            assets = [a for a in assets if a.industry.value.lower() == ind_target]

        # 3. Operational status filter
        if status is not None:
            status_target = status.strip().lower()
            assets = [a for a in assets if a.status.value.lower() == status_target]

        # 4. State filter
        if state is not None:
            state_target = state.strip().lower()
            assets = [
                a for a in assets if a.state and state_target in a.state.strip().lower()
            ]

        # 5. Deterministic Pagination
        paged_assets = assets[offset : offset + limit]

        # 6. Serialize to RFC 7946 GeoJSON Features
        features: list[GeoJsonFeature] = []
        lons: list[float] = []
        lats: list[float] = []

        for asset in paged_assets:
            feat_dict = asset.to_geojson_feature()
            feat_geo = GeoJsonGeometry(
                type=feat_dict["geometry"]["type"],
                coordinates=feat_dict["geometry"]["coordinates"],
            )
            feature = GeoJsonFeature(
                type="Feature",
                id=asset.id,
                geometry=feat_geo,
                properties=feat_dict["properties"],
            )
            features.append(feature)
            lons.append(asset.longitude)
            lats.append(asset.latitude)

        # 7. Compute Layer Bounding Box [min_lon, min_lat, max_lon, max_lat]
        layer_bbox: list[float] | None = None
        if lons and lats:
            layer_bbox = [min(lons), min(lats), max(lons), max(lats)]

        return GeoJsonFeatureCollection(
            type="FeatureCollection",
            features=features,
            bbox=layer_bbox,
        )

    @classmethod
    def get_asset_by_id(
        cls, asset_id: str, include_expansion: bool = True
    ) -> IndustrialAsset:
        """Retrieve a single industrial asset by canonical identifier."""
        collection = cls.get_collection(include_expansion=include_expansion)
        target = next((a for a in collection.assets if a.id == asset_id), None)
        if target is None:
            raise NotFoundError(
                message=f"Industrial asset '{asset_id}' not found.",
                code=ErrorCode.RESOURCE_NOT_FOUND,
            )
        return target

    @classmethod
    def get_summary(cls, include_expansion: bool = False) -> dict[str, Any]:
        """Assemble operational summary metrics for the industrial asset dataset."""
        collection = cls.get_collection(include_expansion=include_expansion)
        return {
            "total_count": collection.total_count,
            "map_eligible_count": collection.map_eligible_count,
            "sources_summary": collection.sources_summary,
            "industries_summary": collection.industries_summary,
            "duplicate_candidates_count": collection.duplicate_candidates_count,
        }
