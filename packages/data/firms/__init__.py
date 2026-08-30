"""NASA FIRMS canonical source record and fixture parser package."""

from packages.data.firms.normalizer import (
    compute_canonical_detection_id,
    compute_firms_raw_hash,
    normalize_day_night,
    normalize_instrument,
    normalize_raw_row_to_detection,
    normalize_satellite_name,
    parse_firms_timestamp,
)
from packages.data.firms.parser import (
    parse_firms_csv,
    parse_firms_csv_with_report,
)
from packages.data.firms.schemas import (
    FirmsParseReport,
    FirmsRowError,
    RawFirmsCsvRow,
)

__all__ = [
    "FirmsParseReport",
    "FirmsRowError",
    "RawFirmsCsvRow",
    "compute_canonical_detection_id",
    "compute_firms_raw_hash",
    "normalize_day_night",
    "normalize_instrument",
    "normalize_raw_row_to_detection",
    "normalize_satellite_name",
    "parse_firms_csv",
    "parse_firms_csv_with_report",
    "parse_firms_timestamp",
]
