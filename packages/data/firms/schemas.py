import hashlib
import json
import math
import re
from enum import StrEnum
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from packages.schemas.common import BaseDomainModel, BoundingBox, UtcDatetime
from packages.schemas.detection import Detection
from packages.schemas.enums import SnapshotAvailabilityState


class FirmsProduct(StrEnum):
    """Supported NASA FIRMS satellite data products."""

    VIIRS_SNPP_NRT = "VIIRS_SNPP_NRT"
    VIIRS_NOAA20_NRT = "VIIRS_NOAA20_NRT"
    VIIRS_NOAA21_NRT = "VIIRS_NOAA21_NRT"
    MODIS_NRT = "MODIS_NRT"
    MODIS_SP = "MODIS_SP"


class FirmsAreaRequest(BaseModel):
    """Validated request parameters for NASA FIRMS Area API."""

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    min_longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Western boundary longitude in WGS-84 decimal degrees.",
    )
    min_latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Southern boundary latitude in WGS-84 decimal degrees.",
    )
    max_longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Eastern boundary longitude in WGS-84 decimal degrees.",
    )
    max_latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Northern boundary latitude in WGS-84 decimal degrees.",
    )
    product: FirmsProduct = Field(
        default=FirmsProduct.VIIRS_SNPP_NRT,
        description="Target FIRMS satellite observation product.",
    )
    day_range: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Temporal acquisition window in days (1-10 allowed by NASA).",
    )
    date: str | None = Field(
        default=None,
        description="Optional reference date in 'YYYY-MM-DD' format.",
    )

    @field_validator("date", mode="after")
    @classmethod
    def _validate_date_format(cls, v: str | None) -> str | None:
        if v is not None and not re.match(r"^\d{4}-\d{2}-\d{2}$", v.strip()):
            raise ValueError(f"date '{v}' must be in YYYY-MM-DD format.")
        return v

    @model_validator(mode="after")
    def _validate_bbox_bounds(self) -> "FirmsAreaRequest":
        if self.min_latitude > self.max_latitude:
            raise ValueError(
                f"min_lat ({self.min_latitude}) > max_lat ({self.max_latitude})."
            )
        if self.min_longitude > self.max_longitude:
            raise ValueError(
                f"min_lon ({self.min_longitude}) > max_lon ({self.max_longitude})."
            )
        return self


class FirmsCountryRequest(BaseModel):
    """Validated request parameters for NASA FIRMS Country API."""

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    country_code: str = Field(
        ...,
        min_length=3,
        max_length=3,
        description="3-letter ISO country code (e.g. 'IND').",
    )
    product: FirmsProduct = Field(
        default=FirmsProduct.VIIRS_SNPP_NRT,
        description="Target FIRMS satellite observation product.",
    )
    day_range: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Temporal acquisition window in days (1-10).",
    )
    date: str | None = Field(
        default=None,
        description="Optional reference date in 'YYYY-MM-DD' format.",
    )

    @field_validator("country_code", mode="after")
    @classmethod
    def _validate_country_code(cls, v: str) -> str:
        code = v.strip().upper()
        if not re.match(r"^[A-Z]{3}$", code):
            raise ValueError(f"country_code '{v}' must be a 3-letter ISO code.")
        return code

    @field_validator("date", mode="after")
    @classmethod
    def _validate_date_format(cls, v: str | None) -> str | None:
        if v is not None and not re.match(r"^\d{4}-\d{2}-\d{2}$", v.strip()):
            raise ValueError(f"date '{v}' must be in YYYY-MM-DD format.")
        return v


class FirmsRawCapture(BaseDomainModel):
    """Immutable representation of a raw NASA FIRMS provider retrieval result.

    Preserves the exact raw response bytes, safe request metadata, cryptographic
    fingerprints, and source snapshot provenance.
    """

    source_snapshot_id: str = Field(
        ...,
        min_length=1,
        description="Unique deterministic identifier for the source snapshot.",
    )
    source_id: str = Field(
        default="firms",
        min_length=1,
        description="Identifier of the source registry entry.",
    )
    product: str = Field(
        ...,
        min_length=1,
        description="Target FIRMS product identifier.",
    )
    product_version: str = Field(
        default="v2.0",
        min_length=1,
        description="Processing product version.",
    )
    request_fingerprint: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="SHA-256 hash of canonical sanitized request parameters.",
    )
    raw_content: bytes = Field(
        ...,
        description="Exact raw response bytes as received from provider.",
    )
    raw_content_str: str = Field(
        ...,
        description="Decoded UTF-8 string of raw provider response.",
    )
    content_hash: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="SHA-256 cryptographic hash of raw_content bytes.",
    )
    retrieved_at: UtcDatetime = Field(
        ...,
        description="Explicit UTC timestamp when external retrieval occurred.",
    )
    availability_status: SnapshotAvailabilityState = Field(
        ...,
        description="Availability status (AVAILABLE, EMPTY_RESULT, FAILED, etc.).",
    )
    http_status: int = Field(
        ...,
        ge=100,
        le=599,
        description="HTTP response status code.",
    )
    safe_request_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Sanitized request parameters strictly excluding credentials.",
    )
    row_count: int = Field(
        default=0,
        ge=0,
        description="Count of active fire data rows present in response.",
    )
    error_message: str | None = Field(
        default=None,
        description="Error details if retrieval encountered an issue.",
    )
    error_code: str | None = Field(
        default=None,
        description="Machine-readable error code if failure occurred.",
    )


class RawFirmsCsvRow(BaseModel):
    """Validation schema for raw, unnormalized NASA FIRMS CSV row.

    Captures vendor-specific column names and applies initial type/boundary checks
    before canonical domain normalization.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="allow",  # Allow vendor extra metadata without rejecting row
        str_strip_whitespace=True,
    )

    latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Observation latitude in WGS-84 decimal degrees (-90 to 90).",
    )
    longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Observation longitude in WGS-84 decimal degrees (-180 to 180).",
    )
    acq_date: str = Field(
        ...,
        min_length=8,
        max_length=10,
        description="Acquisition date string (e.g. 'YYYY-MM-DD').",
    )
    acq_time: str = Field(
        ...,
        min_length=1,
        max_length=6,
        description="Acquisition time string (e.g. 'HHMM' or 'HH:MM').",
    )
    satellite: str = Field(
        ...,
        min_length=1,
        description="Observing satellite/platform identifier.",
    )
    instrument: str | None = Field(
        None,
        description="Sensor instrument name (e.g. 'VIIRS', 'MODIS').",
    )
    confidence: str | None = Field(
        None,
        description="Source confidence string or numeric score as string.",
    )
    version: str | None = Field(
        None,
        description="Source data product processing version.",
    )
    bright_ti4: float | None = Field(
        None,
        ge=0.0,
        description="VIIRS I-4 band brightness temperature in Kelvin.",
    )
    bright_ti5: float | None = Field(
        None,
        ge=0.0,
        description="VIIRS I-5 band brightness temperature in Kelvin.",
    )
    brightness: float | None = Field(
        None,
        ge=0.0,
        description="MODIS Channel 21/22 brightness temperature in Kelvin.",
    )
    bright_t31: float | None = Field(
        None,
        ge=0.0,
        description="MODIS Channel 31 brightness temperature in Kelvin.",
    )
    frp: float | None = Field(
        None,
        ge=0.0,
        description="Fire Radiative Power in Megawatts (MW).",
    )
    scan: float | None = Field(
        None,
        gt=0.0,
        description="Along-scan pixel dimension in kilometers.",
    )
    track: float | None = Field(
        None,
        gt=0.0,
        description="Along-track pixel dimension in kilometers.",
    )
    daynight: str | None = Field(
        None,
        description="Daytime ('D') or Nighttime ('N') observation indicator.",
    )

    @field_validator(
        "latitude",
        "longitude",
        "bright_ti4",
        "bright_ti5",
        "brightness",
        "bright_t31",
        "frp",
        "scan",
        "track",
        mode="after",
    )
    @classmethod
    def _validate_finite(cls, v: float | None) -> float | None:
        if v is not None and not math.isfinite(v):
            raise ValueError("Numeric measurement must be finite (not NaN or Inf).")
        return v


class FirmsRowError(BaseDomainModel):
    """Structured diagnostic representation of a malformed FIRMS record row."""

    row_index: int = Field(
        ...,
        ge=0,
        description="0-indexed line number in source input.",
    )
    field_name: str | None = Field(
        None,
        description="Specific column/field name causing failure if known.",
    )
    raw_value: str | None = Field(
        None,
        description="Raw string value that failed validation.",
    )
    error_message: str = Field(
        ...,
        min_length=1,
        description="Detailed diagnostic error message.",
    )
    raw_row_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Full raw row dictionary for auditability.",
    )


class FirmsParseReport(BaseDomainModel):
    """Structured result of a batch FIRMS fixture parsing operation."""

    source_snapshot_id: str = Field(..., min_length=1)
    total_rows: int = Field(..., ge=0)
    valid_count: int = Field(..., ge=0)
    error_count: int = Field(..., ge=0)
    valid_detections: list[Detection] = Field(default_factory=list)
    row_errors: list[FirmsRowError] = Field(default_factory=list)


class RealDataAcquisitionManifest(BaseDomainModel):
    """Provenance and quality manifest for real observational satellite data."""

    dataset_id: str = Field(
        default="ds_real_firms_v1.0.0",
        min_length=1,
        description="Unique identifier for the observational dataset.",
    )
    dataset_version: str = Field(
        default="v1.0.0",
        min_length=1,
        description="Semantic version of the observational dataset.",
    )
    source_name: str = Field(
        default="NASA_FIRMS",
        description="Originating observational data system.",
    )
    source_product: str = Field(
        ...,
        description="NASA FIRMS product identifier (e.g. VIIRS_SNPP_NRT, MODIS_NRT).",
    )
    sensor: str = Field(
        ...,
        description="Observing satellite sensor platform (e.g. VIIRS, MODIS).",
    )
    study_area_id: str = Field(
        ...,
        description="Identifier of study area (e.g. jamnagar_kutch).",
    )
    study_area_name: str = Field(
        ...,
        description="Human-readable study area title.",
    )
    bounding_box: BoundingBox = Field(
        ...,
        description="Geographic WGS-84 spatial bounding envelope.",
    )
    requested_start_date: str = Field(
        ...,
        description="Requested temporal window start date (YYYY-MM-DD).",
    )
    requested_end_date: str = Field(
        ...,
        description="Requested temporal window end date (YYYY-MM-DD).",
    )
    actual_coverage_start: UtcDatetime | None = Field(
        None,
        description="Earliest observation timestamp among canonical detections.",
    )
    actual_coverage_end: UtcDatetime | None = Field(
        None,
        description="Latest observation timestamp among canonical detections.",
    )
    raw_record_count: int = Field(
        ...,
        ge=0,
        description="Total raw CSV observation rows parsed from source.",
    )
    valid_record_count: int = Field(
        ...,
        ge=0,
        description="Total structurally valid observation rows.",
    )
    invalid_record_count: int = Field(
        default=0,
        ge=0,
        description="Total malformed or unparseable rows rejected.",
    )
    duplicate_record_count: int = Field(
        default=0,
        ge=0,
        description="Total exact duplicate rows removed during ingestion.",
    )
    spatial_excluded_count: int = Field(
        default=0,
        ge=0,
        description="Records filtered out due to location outside study area.",
    )
    temporal_excluded_count: int = Field(
        default=0,
        ge=0,
        description="Records filtered out due to timestamp outside window.",
    )
    canonical_record_count: int = Field(
        ...,
        ge=0,
        description="Final count of canonical Detection records in dataset.",
    )
    raw_file_hashes: list[str] = Field(
        default_factory=list,
        description="SHA-256 hashes of immutable raw input files/captures.",
    )
    canonical_dataset_hash: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="Deterministic SHA-256 hash of sorted canonical detections.",
    )
    missingness_summary: dict[str, int] = Field(
        default_factory=dict,
        description="Count of missing/null values for optional measurement fields.",
    )
    sensor_distribution: dict[str, int] = Field(
        default_factory=dict,
        description="Breakdown of detections by sensor instrument.",
    )
    satellite_distribution: dict[str, int] = Field(
        default_factory=dict,
        description="Breakdown of detections by observing satellite.",
    )
    day_night_distribution: dict[str, int] = Field(
        default_factory=dict,
        description="Breakdown of detections by day/night observation flag.",
    )
    quality_control_passed: bool = Field(
        default=True,
        description="Whether dataset passed quality and consistency audit.",
    )
    created_at: UtcDatetime = Field(
        ...,
        description="Timestamp when dataset and manifest were compiled in UTC.",
    )
    ingestion_version: str = Field(
        default="v1.0.0",
        description="Version of ingestion software pipeline.",
    )


class RealDetectionDataset(BaseDomainModel):
    """Canonical container for real observational satellite detection records."""

    manifest: RealDataAcquisitionManifest = Field(
        ...,
        description="Provenance and quality manifest.",
    )
    detections: list[Detection] = Field(
        default_factory=list,
        description="Deterministically ordered canonical Detection domain objects.",
    )

    def compute_canonical_hash(self) -> str:
        """Compute deterministic SHA-256 hash across sorted detection records."""
        sorted_dets = sorted(
            self.detections,
            key=lambda d: (
                d.acquired_at.isoformat(),
                d.geometry.latitude,
                d.geometry.longitude,
                d.satellite,
                d.detection_id,
            ),
        )
        canonical_rows = [
            {
                "detection_id": d.detection_id,
                "source": d.source,
                "source_snapshot_id": d.source_snapshot_id,
                "acquired_at": d.acquired_at.isoformat(),
                "latitude": round(d.geometry.latitude, 6),
                "longitude": round(d.geometry.longitude, 6),
                "satellite": d.satellite,
                "instrument": d.instrument,
                "product_type": d.product_type,
                "product_version": d.product_version,
                "raw_hash": d.raw_hash,
                "frp_mw": round(d.frp_mw, 4) if d.frp_mw is not None else None,
                "brightness_ti4_k": (
                    round(d.brightness_ti4_k, 2)
                    if d.brightness_ti4_k is not None
                    else None
                ),
                "confidence": d.confidence,
                "day_night": d.day_night.value if d.day_night else None,
            }
            for d in sorted_dets
        ]
        json_bytes = json.dumps(
            canonical_rows, sort_keys=True, ensure_ascii=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(json_bytes).hexdigest()
