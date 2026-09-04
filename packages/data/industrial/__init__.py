"""Industrial infrastructure data loading, normalization, and deduplication package."""

from packages.data.industrial.deduplication import (
    find_duplicate_candidates,
    haversine_distance_meters,
    link_duplicate_records,
)
from packages.data.industrial.loader import IndustrialDataLoader
from packages.data.industrial.normalizer import (
    compute_canonical_asset_id,
    normalize_coordinates,
    normalize_facility_name,
    normalize_industry_and_asset_type,
    normalize_operational_status,
    normalize_state_name,
)
from packages.schemas.industrial_asset import (
    AssetType,
    DuplicateCandidate,
    IndustrialAsset,
    IndustrialAssetCollection,
    IndustryType,
    OperationalStatus,
)

__all__ = [
    "AssetType",
    "DuplicateCandidate",
    "IndustrialAsset",
    "IndustrialAssetCollection",
    "IndustrialDataLoader",
    "IndustryType",
    "OperationalStatus",
    "compute_canonical_asset_id",
    "find_duplicate_candidates",
    "haversine_distance_meters",
    "link_duplicate_records",
    "normalize_coordinates",
    "normalize_facility_name",
    "normalize_industry_and_asset_type",
    "normalize_operational_status",
    "normalize_state_name",
]
