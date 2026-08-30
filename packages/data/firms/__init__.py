"""NASA FIRMS data ingestion, raw capture adapter, and canonical parser package."""

from packages.data.firms.capture import (
    FirmsRawCaptureAdapter,
    compute_content_hash,
    compute_request_fingerprint,
    count_csv_data_rows,
)
from packages.data.firms.client import FirmsClient
from packages.data.firms.errors import (
    FirmsApiError,
    FirmsAuthenticationError,
    FirmsMalformedPayloadError,
    FirmsRateLimitError,
    FirmsTimeoutError,
    FirmsUnavailableError,
)
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
    FirmsAreaRequest,
    FirmsCountryRequest,
    FirmsParseReport,
    FirmsProduct,
    FirmsRawCapture,
    FirmsRowError,
    RawFirmsCsvRow,
)

__all__ = [
    "FirmsApiError",
    "FirmsAreaRequest",
    "FirmsAuthenticationError",
    "FirmsClient",
    "FirmsCountryRequest",
    "FirmsMalformedPayloadError",
    "FirmsParseReport",
    "FirmsProduct",
    "FirmsRateLimitError",
    "FirmsRawCapture",
    "FirmsRawCaptureAdapter",
    "FirmsRowError",
    "FirmsTimeoutError",
    "FirmsUnavailableError",
    "RawFirmsCsvRow",
    "compute_canonical_detection_id",
    "compute_content_hash",
    "compute_firms_raw_hash",
    "compute_request_fingerprint",
    "count_csv_data_rows",
    "normalize_day_night",
    "normalize_instrument",
    "normalize_raw_row_to_detection",
    "normalize_satellite_name",
    "parse_firms_csv",
    "parse_firms_csv_with_report",
    "parse_firms_timestamp",
]
