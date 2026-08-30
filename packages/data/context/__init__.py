"""External Context Data Ingestion package (DATA-004)."""

from packages.data.context.errors import (
    ContextDataError,
    ContextParsingError,
    ContextValidationError,
)
from packages.data.context.normalizer import (
    compute_canonical_feature_id,
    compute_context_raw_hash,
    map_fuel_or_industry_to_context_type,
    map_tags_to_context_type,
    normalize_geojson_geometry,
    parse_optional_datetime,
)
from packages.data.context.parser import (
    parse_context_geojson,
    parse_context_geojson_with_report,
    parse_industrial_catalog_csv,
    parse_industrial_catalog_csv_with_report,
)
from packages.data.context.schemas import (
    ContextIngestionReport,
    RawContextFeatureError,
    RawContextRow,
)

__all__ = [
    "ContextDataError",
    "ContextIngestionReport",
    "ContextParsingError",
    "ContextValidationError",
    "RawContextFeatureError",
    "RawContextRow",
    "compute_canonical_feature_id",
    "compute_context_raw_hash",
    "map_fuel_or_industry_to_context_type",
    "map_tags_to_context_type",
    "normalize_geojson_geometry",
    "parse_context_geojson",
    "parse_context_geojson_with_report",
    "parse_industrial_catalog_csv",
    "parse_industrial_catalog_csv_with_report",
    "parse_optional_datetime",
]
