"""Parsers for GeoJSON and CSV external contextual datasets."""

import csv
import io
import json
from pathlib import Path
from typing import Any, TextIO

from packages.context.models import ContextFeature
from packages.data.context.errors import ContextParsingError, ContextValidationError
from packages.data.context.normalizer import (
    compute_canonical_feature_id,
    compute_context_raw_hash,
    map_fuel_or_industry_to_context_type,
    map_tags_to_context_type,
    normalize_geojson_geometry,
    parse_optional_datetime,
)
from packages.data.context.schemas import (
    ContextIngestionReport,
    RawContextFeatureError,
)
from packages.geospatial.coordinates import validate_wgs84_coordinates
from packages.schemas.common import Coordinate


def _load_geojson_dict(geojson_input: str | Path | dict[str, Any]) -> dict[str, Any]:
    """Load and validate GeoJSON dictionary representation."""
    if isinstance(geojson_input, dict):
        return geojson_input
    if isinstance(geojson_input, Path):
        with open(geojson_input, encoding="utf-8") as f:
            return json.load(f)  # type: ignore[no-any-return]
    if isinstance(geojson_input, str):
        try:
            return json.loads(geojson_input)  # type: ignore[no-any-return]
        except json.JSONDecodeError as exc:
            raise ContextParsingError(f"Malformed GeoJSON JSON payload: {exc}") from exc

    raise ContextParsingError(f"Unsupported GeoJSON input type {type(geojson_input)}.")


def parse_context_geojson(
    geojson_input: str | Path | dict[str, Any],
    provider: str,
    dataset_name: str,
    dataset_version: str = "v1.0",
    strict: bool = True,
) -> list[ContextFeature]:
    """Parse GeoJSON FeatureCollection into canonical ContextFeature domain objects.

    Args:
        geojson_input: GeoJSON JSON string, file Path, or dictionary.
        provider: Provider identifier (e.g. 'osm', 'gadm').
        dataset_name: Dataset name (e.g. 'osm_industrial').
        dataset_version: Dataset release version or snapshot tag.
        strict: If True, raises ContextValidationError on first invalid feature.

    Returns:
        list[ContextFeature]: Deterministically sorted canonical context features.

    Raises:
        ContextParsingError: If GeoJSON structure is invalid.
        ContextValidationError: If feature geometry or attributes are invalid.
    """
    data = _load_geojson_dict(geojson_input)

    if not isinstance(data, dict):
        raise ContextParsingError("GeoJSON root must be a JSON object.")

    features_raw = data.get("features")
    if features_raw is None:
        if data.get("type") == "Feature":
            features_raw = [data]
        else:
            raise ContextParsingError(
                "GeoJSON object missing 'features' list or 'Feature' type."
            )

    if not isinstance(features_raw, list):
        raise ContextParsingError("GeoJSON 'features' attribute must be a list.")

    features: list[ContextFeature] = []

    for idx, raw_feat in enumerate(features_raw):
        if not isinstance(raw_feat, dict):
            if strict:
                raise ContextValidationError(
                    f"Feature at index {idx} is not a dictionary object.",
                    item_index=idx,
                )
            continue

        try:
            geom_raw = raw_feat.get("geometry")
            if not geom_raw or not isinstance(geom_raw, dict):
                raise ContextValidationError(
                    "Feature missing required 'geometry' object."
                )

            centroid, bbox = normalize_geojson_geometry(geom_raw)

            props = raw_feat.get("properties") or {}
            if not isinstance(props, dict):
                props = {}

            # Map context classification
            context_type = map_tags_to_context_type(props)

            facility_name = (
                props.get("name")
                or props.get("facility_name")
                or props.get("plant_name")
            )
            facility_name_str = (
                str(facility_name).strip() if facility_name is not None else None
            )

            raw_id = (
                raw_feat.get("id")
                or props.get("id")
                or props.get("osm_id")
                or props.get("@id")
            )
            raw_id_str = str(raw_id).strip() if raw_id is not None else None

            raw_hash = compute_context_raw_hash(raw_feat)
            feature_id = compute_canonical_feature_id(provider, raw_id_str, raw_hash)

            valid_from = parse_optional_datetime(props.get("start_date"))
            valid_to = parse_optional_datetime(props.get("end_date"))

            # Stringify metadata dictionary for domain model
            raw_meta: dict[str, str] = {
                str(k): str(v) for k, v in props.items() if v is not None
            }

            feature = ContextFeature(
                feature_id=feature_id,
                provider=provider.strip().lower(),
                dataset_name=dataset_name.strip().lower(),
                dataset_version=dataset_version.strip(),
                context_type=context_type,
                geometry=centroid,
                facility_name=facility_name_str if facility_name_str != "" else None,
                bounding_box=bbox,
                valid_from=valid_from,
                valid_to=valid_to,
                raw_metadata=raw_meta if raw_meta else None,
            )
            features.append(feature)

        except Exception as exc:
            if strict:
                raise ContextValidationError(
                    f"Malformed context feature at index {idx}: {exc}",
                    item_index=idx,
                    details={"raw_data": raw_feat, "error": str(exc)},
                ) from exc

    # Deterministic canonical sorting: (context_type, latitude, longitude, feature_id)
    features.sort(
        key=lambda f: (
            f.context_type.value,
            f.geometry.latitude,
            f.geometry.longitude,
            f.feature_id,
        )
    )

    return features


def parse_context_geojson_with_report(
    geojson_input: str | Path | dict[str, Any],
    provider: str,
    dataset_name: str,
    dataset_version: str = "v1.0",
) -> ContextIngestionReport:
    """Parse GeoJSON in report mode collecting valid features and errors."""
    data = _load_geojson_dict(geojson_input)

    if not isinstance(data, dict):
        raise ContextParsingError("GeoJSON root must be a JSON object.")

    features_raw = data.get("features")
    if features_raw is None:
        if data.get("type") == "Feature":
            features_raw = [data]
        else:
            raise ContextParsingError(
                "GeoJSON object missing 'features' list or 'Feature' type."
            )

    valid_features: list[ContextFeature] = []
    errors: list[RawContextFeatureError] = []

    for idx, raw_feat in enumerate(features_raw):
        if not isinstance(raw_feat, dict):
            errors.append(
                RawContextFeatureError(
                    item_index=idx,
                    feature_id=None,
                    field_name="feature",
                    error_message="Feature is not a dictionary.",
                    raw_data={},
                )
            )
            continue

        try:
            geom_raw = raw_feat.get("geometry")
            if not geom_raw or not isinstance(geom_raw, dict):
                raise ContextValidationError(
                    "Feature missing required 'geometry' object."
                )

            centroid, bbox = normalize_geojson_geometry(geom_raw)

            props = raw_feat.get("properties") or {}
            if not isinstance(props, dict):
                props = {}

            context_type = map_tags_to_context_type(props)
            facility_name = (
                props.get("name")
                or props.get("facility_name")
                or props.get("plant_name")
            )
            facility_name_str = (
                str(facility_name).strip() if facility_name is not None else None
            )

            raw_id = (
                raw_feat.get("id")
                or props.get("id")
                or props.get("osm_id")
                or props.get("@id")
            )
            raw_id_str = str(raw_id).strip() if raw_id is not None else None

            raw_hash = compute_context_raw_hash(raw_feat)
            feature_id = compute_canonical_feature_id(provider, raw_id_str, raw_hash)

            valid_from = parse_optional_datetime(props.get("start_date"))
            valid_to = parse_optional_datetime(props.get("end_date"))

            raw_meta: dict[str, str] = {
                str(k): str(v) for k, v in props.items() if v is not None
            }

            feature = ContextFeature(
                feature_id=feature_id,
                provider=provider.strip().lower(),
                dataset_name=dataset_name.strip().lower(),
                dataset_version=dataset_version.strip(),
                context_type=context_type,
                geometry=centroid,
                facility_name=facility_name_str if facility_name_str != "" else None,
                bounding_box=bbox,
                valid_from=valid_from,
                valid_to=valid_to,
                raw_metadata=raw_meta if raw_meta else None,
            )
            valid_features.append(feature)

        except Exception as exc:
            raw_id_val = raw_feat.get("id") if isinstance(raw_feat, dict) else None
            errors.append(
                RawContextFeatureError(
                    item_index=idx,
                    feature_id=str(raw_id_val) if raw_id_val is not None else None,
                    field_name=None,
                    error_message=str(exc),
                    raw_data=raw_feat if isinstance(raw_feat, dict) else {},
                )
            )

    valid_features.sort(
        key=lambda f: (
            f.context_type.value,
            f.geometry.latitude,
            f.geometry.longitude,
            f.feature_id,
        )
    )

    return ContextIngestionReport(
        provider=provider.strip().lower(),
        dataset_name=dataset_name.strip().lower(),
        dataset_version=dataset_version.strip(),
        total_items=len(features_raw),
        valid_count=len(valid_features),
        error_count=len(errors),
        valid_features=valid_features,
        errors=errors,
    )


def parse_industrial_catalog_csv(
    csv_input: str | Path | TextIO,
    provider: str = "wri",
    dataset_name: str = "power_plants",
    dataset_version: str = "v1.0",
    strict: bool = True,
) -> list[ContextFeature]:
    """Parse a tabular industrial/power CSV into canonical ContextFeature records.

    Args:
        csv_input: CSV string, file Path, or text stream.
        provider: Originating provider (e.g. 'wri', 'gem').
        dataset_name: Dataset identifier.
        dataset_version: Dataset version string.
        strict: If True, raises ContextValidationError on invalid rows.

    Returns:
        list[ContextFeature]: Canonical context features.
    """
    if isinstance(csv_input, Path):
        with open(csv_input, encoding="utf-8") as f:
            content = f.read()
        stream: io.StringIO | TextIO = io.StringIO(content)
    elif isinstance(csv_input, str):
        stream = io.StringIO(csv_input)
    else:
        stream = csv_input

    reader = csv.DictReader(stream)
    if reader.fieldnames is None:
        return []

    features: list[ContextFeature] = []

    for row_idx, raw_row in enumerate(reader):
        cleaned: dict[str, Any] = {}
        for k, v in raw_row.items():
            if not k:
                continue
            clean_k = k.strip().lower()
            clean_v = v.strip() if isinstance(v, str) else v
            cleaned[clean_k] = clean_v if clean_v != "" else None

        try:
            # Check required coordinate columns
            if "latitude" not in cleaned or "longitude" not in cleaned:
                raise ContextValidationError("Row missing 'latitude' or 'longitude'.")

            lat_val = float(cleaned["latitude"])
            lon_val = float(cleaned["longitude"])
            lat_v, lon_v = validate_wgs84_coordinates(lat_val, lon_val)
            coord = Coordinate(latitude=lat_v, longitude=lon_v)

            # Map category
            industry_type = (
                cleaned.get("facility_type")
                or cleaned.get("industry_type")
                or cleaned.get("sector")
            )
            fuel_type = cleaned.get("primary_fuel") or cleaned.get("fuel")
            context_type = map_fuel_or_industry_to_context_type(
                industry_type, fuel_type
            )

            facility_name = (
                cleaned.get("facility_name")
                or cleaned.get("plant_name")
                or cleaned.get("name")
            )
            raw_id = (
                cleaned.get("facility_id")
                or cleaned.get("gppd_idnr")
                or cleaned.get("id")
            )

            raw_hash = compute_context_raw_hash(cleaned)
            feature_id = compute_canonical_feature_id(provider, raw_id, raw_hash)

            valid_from = parse_optional_datetime(
                cleaned.get("valid_from") or cleaned.get("commissioning_year")
            )
            valid_to = parse_optional_datetime(cleaned.get("valid_to"))

            raw_meta: dict[str, str] = {
                str(k): str(v) for k, v in cleaned.items() if v is not None
            }

            feat = ContextFeature(
                feature_id=feature_id,
                provider=provider.strip().lower(),
                dataset_name=dataset_name.strip().lower(),
                dataset_version=dataset_version.strip(),
                context_type=context_type,
                geometry=coord,
                facility_name=facility_name,
                bounding_box=None,
                valid_from=valid_from,
                valid_to=valid_to,
                raw_metadata=raw_meta if raw_meta else None,
            )
            features.append(feat)

        except Exception as exc:
            if strict:
                raise ContextValidationError(
                    f"Malformed context row at line {row_idx + 1}: {exc}",
                    item_index=row_idx,
                    details={"raw_data": cleaned, "error": str(exc)},
                ) from exc

    features.sort(
        key=lambda f: (
            f.context_type.value,
            f.geometry.latitude,
            f.geometry.longitude,
            f.feature_id,
        )
    )

    return features


def parse_industrial_catalog_csv_with_report(
    csv_input: str | Path | TextIO,
    provider: str = "wri",
    dataset_name: str = "power_plants",
    dataset_version: str = "v1.0",
) -> ContextIngestionReport:
    """Parse CSV in batch report mode collecting valid features and errors."""
    if isinstance(csv_input, Path):
        with open(csv_input, encoding="utf-8") as f:
            content = f.read()
        stream: io.StringIO | TextIO = io.StringIO(content)
    elif isinstance(csv_input, str):
        stream = io.StringIO(csv_input)
    else:
        stream = csv_input

    reader = csv.DictReader(stream)
    if reader.fieldnames is None:
        return ContextIngestionReport(
            provider=provider.strip().lower(),
            dataset_name=dataset_name.strip().lower(),
            dataset_version=dataset_version.strip(),
            total_items=0,
            valid_count=0,
            error_count=0,
            valid_features=[],
            errors=[],
        )

    valid_features: list[ContextFeature] = []
    errors: list[RawContextFeatureError] = []
    total_items = 0

    for row_idx, raw_row in enumerate(reader):
        total_items += 1
        cleaned: dict[str, Any] = {}
        for k, v in raw_row.items():
            if not k:
                continue
            clean_k = k.strip().lower()
            clean_v = v.strip() if isinstance(v, str) else v
            cleaned[clean_k] = clean_v if clean_v != "" else None

        try:
            if "latitude" not in cleaned or "longitude" not in cleaned:
                raise ContextValidationError("Row missing 'latitude' or 'longitude'.")

            lat_val = float(cleaned["latitude"])
            lon_val = float(cleaned["longitude"])
            lat_v, lon_v = validate_wgs84_coordinates(lat_val, lon_val)
            coord = Coordinate(latitude=lat_v, longitude=lon_v)

            industry_type = (
                cleaned.get("facility_type")
                or cleaned.get("industry_type")
                or cleaned.get("sector")
            )
            fuel_type = cleaned.get("primary_fuel") or cleaned.get("fuel")
            context_type = map_fuel_or_industry_to_context_type(
                industry_type, fuel_type
            )

            facility_name = (
                cleaned.get("facility_name")
                or cleaned.get("plant_name")
                or cleaned.get("name")
            )
            raw_id = (
                cleaned.get("facility_id")
                or cleaned.get("gppd_idnr")
                or cleaned.get("id")
            )

            raw_hash = compute_context_raw_hash(cleaned)
            feature_id = compute_canonical_feature_id(provider, raw_id, raw_hash)

            valid_from = parse_optional_datetime(
                cleaned.get("valid_from") or cleaned.get("commissioning_year")
            )
            valid_to = parse_optional_datetime(cleaned.get("valid_to"))

            raw_meta: dict[str, str] = {
                str(k): str(v) for k, v in cleaned.items() if v is not None
            }

            feat = ContextFeature(
                feature_id=feature_id,
                provider=provider.strip().lower(),
                dataset_name=dataset_name.strip().lower(),
                dataset_version=dataset_version.strip(),
                context_type=context_type,
                geometry=coord,
                facility_name=facility_name,
                bounding_box=None,
                valid_from=valid_from,
                valid_to=valid_to,
                raw_metadata=raw_meta if raw_meta else None,
            )
            valid_features.append(feat)

        except Exception as exc:
            errors.append(
                RawContextFeatureError(
                    item_index=row_idx,
                    feature_id=str(cleaned.get("id")) if "id" in cleaned else None,
                    field_name=None,
                    error_message=str(exc),
                    raw_data=cleaned,
                )
            )

    valid_features.sort(
        key=lambda f: (
            f.context_type.value,
            f.geometry.latitude,
            f.geometry.longitude,
            f.feature_id,
        )
    )

    return ContextIngestionReport(
        provider=provider.strip().lower(),
        dataset_name=dataset_name.strip().lower(),
        dataset_version=dataset_version.strip(),
        total_items=total_items,
        valid_count=len(valid_features),
        error_count=len(errors),
        valid_features=valid_features,
        errors=errors,
    )
