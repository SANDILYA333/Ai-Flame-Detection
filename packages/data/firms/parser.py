"""High-level CSV parsing APIs for NASA FIRMS active fire observation records."""

import csv
import io
from pathlib import Path
from typing import Any, TextIO

from packages.data.firms.normalizer import normalize_raw_row_to_detection
from packages.data.firms.schemas import (
    FirmsParseReport,
    FirmsRowError,
    RawFirmsCsvRow,
)
from packages.errors import ContractViolationError
from packages.schemas.detection import Detection

# Minimum required columns for a valid FIRMS CSV
_REQUIRED_COLUMNS = {"latitude", "longitude", "acq_date", "acq_time", "satellite"}


def _prepare_raw_dict(raw_row: dict[str, Any]) -> dict[str, Any]:
    """Clean and normalize dictionary keys and empty string values from CSV."""
    cleaned: dict[str, Any] = {}
    for k, v in raw_row.items():
        if not k:
            continue
        clean_key = k.strip().lower()
        if isinstance(v, str):
            clean_val = v.strip()
            # Convert empty strings to None for optional field validation
            cleaned[clean_key] = clean_val if clean_val != "" else None
        else:
            cleaned[clean_key] = v
    return cleaned


def parse_firms_csv(
    csv_input: str | Path | TextIO,
    source_snapshot_id: str,
    product_type: str = "nrt",
    product_version: str = "v2.0",
    strict: bool = True,
) -> list[Detection]:
    """Parse a NASA FIRMS CSV input into a list of canonical Detection domain records.

    Args:
        csv_input: CSV content string, file Path, or readable text stream.
        source_snapshot_id: Identifier of originating source snapshot for lineage.
        product_type: Product processing tier (e.g. 'nrt', 'standard', 'urt').
        product_version: Version string of the source data product.
        strict: If True, raises ContractViolationError on first malformed row.

    Returns:
        list[Detection]: Deterministically ordered list of canonical detections.

    Raises:
        ContractViolationError: If input is malformed or invalid.
    """
    if not source_snapshot_id or not source_snapshot_id.strip():
        raise ContractViolationError(
            "source_snapshot_id cannot be empty.",
            details={"source": "firms"},
        )

    # Resolve input stream
    stream: io.StringIO | TextIO
    if isinstance(csv_input, Path):
        with open(csv_input, encoding="utf-8") as f:
            content = f.read()
        stream = io.StringIO(content)
    elif isinstance(csv_input, str):
        stream = io.StringIO(csv_input)
    else:
        stream = csv_input

    reader = csv.DictReader(stream)
    if reader.fieldnames is None:
        return []

    # Validate header columns
    normalized_headers = {h.strip().lower() for h in reader.fieldnames if h}
    missing_headers = _REQUIRED_COLUMNS - normalized_headers
    if missing_headers:
        raise ContractViolationError(
            f"FIRMS CSV missing required headers: {sorted(missing_headers)}",
            details={
                "missing_headers": sorted(missing_headers),
                "available_headers": sorted(normalized_headers),
            },
        )

    detections: list[Detection] = []

    for row_idx, raw_row in enumerate(reader):
        cleaned_row = _prepare_raw_dict(raw_row)
        try:
            validated_row = RawFirmsCsvRow.model_validate(cleaned_row)
            det = normalize_raw_row_to_detection(
                row=validated_row,
                raw_dict=cleaned_row,
                source_snapshot_id=source_snapshot_id,
                product_type=product_type,
                product_version=product_version,
            )
            detections.append(det)
        except Exception as exc:
            if strict:
                raise ContractViolationError(
                    f"Malformed FIRMS record at row {row_idx + 1}: {exc}",
                    details={
                        "row_index": row_idx,
                        "raw_data": cleaned_row,
                        "error": str(exc),
                    },
                ) from exc

    # Deterministic canonical ordering: (acquired_at, latitude, longitude, raw_hash)
    detections.sort(
        key=lambda d: (
            d.acquired_at,
            d.geometry.latitude,
            d.geometry.longitude,
            d.raw_hash,
        )
    )

    return detections


def parse_firms_csv_with_report(
    csv_input: str | Path | TextIO,
    source_snapshot_id: str,
    product_type: str = "nrt",
    product_version: str = "v2.0",
) -> FirmsParseReport:
    """Parse FIRMS CSV in batch report mode collecting valid detections and errors.

    Args:
        csv_input: CSV content string, file Path, or readable text stream.
        source_snapshot_id: Lineage snapshot identifier.
        product_type: Product tier.
        product_version: Source version string.

    Returns:
        FirmsParseReport: Comprehensive report of parsed records and errors.
    """
    if not source_snapshot_id or not source_snapshot_id.strip():
        raise ContractViolationError(
            "source_snapshot_id cannot be empty.",
            details={"source": "firms"},
        )

    stream: io.StringIO | TextIO
    if isinstance(csv_input, Path):
        with open(csv_input, encoding="utf-8") as f:
            content = f.read()
        stream = io.StringIO(content)
    elif isinstance(csv_input, str):
        stream = io.StringIO(csv_input)
    else:
        stream = csv_input

    reader = csv.DictReader(stream)
    if reader.fieldnames is None:
        return FirmsParseReport(
            source_snapshot_id=source_snapshot_id.strip(),
            total_rows=0,
            valid_count=0,
            error_count=0,
            valid_detections=[],
            row_errors=[],
        )

    # Validate header columns
    normalized_headers = {h.strip().lower() for h in reader.fieldnames if h}
    missing_headers = _REQUIRED_COLUMNS - normalized_headers
    if missing_headers:
        raise ContractViolationError(
            f"FIRMS CSV missing required headers: {sorted(missing_headers)}",
            details={
                "missing_headers": sorted(missing_headers),
                "available_headers": sorted(normalized_headers),
            },
        )

    valid_detections: list[Detection] = []
    row_errors: list[FirmsRowError] = []
    total_rows = 0

    for row_idx, raw_row in enumerate(reader):
        total_rows += 1
        cleaned_row = _prepare_raw_dict(raw_row)
        try:
            validated_row = RawFirmsCsvRow.model_validate(cleaned_row)
            det = normalize_raw_row_to_detection(
                row=validated_row,
                raw_dict=cleaned_row,
                source_snapshot_id=source_snapshot_id,
                product_type=product_type,
                product_version=product_version,
            )
            valid_detections.append(det)
        except Exception as exc:
            row_errors.append(
                FirmsRowError(
                    row_index=row_idx,
                    field_name=None,
                    raw_value=None,
                    error_message=str(exc),
                    raw_row_data=cleaned_row,
                )
            )

    # Deterministic canonical ordering
    valid_detections.sort(
        key=lambda d: (
            d.acquired_at,
            d.geometry.latitude,
            d.geometry.longitude,
            d.raw_hash,
        )
    )

    return FirmsParseReport(
        source_snapshot_id=source_snapshot_id.strip(),
        total_rows=total_rows,
        valid_count=len(valid_detections),
        error_count=len(row_errors),
        valid_detections=valid_detections,
        row_errors=row_errors,
    )
