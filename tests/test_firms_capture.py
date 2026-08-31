"""Unit and adversarial tests for DATA-003 FIRMS Raw Capture."""

import urllib.error
import urllib.request
from datetime import UTC, datetime

import pytest
from pydantic import SecretStr, ValidationError

from packages.data.firms import (
    FirmsAreaRequest,
    FirmsAuthenticationError,
    FirmsClient,
    FirmsCountryRequest,
    FirmsMalformedPayloadError,
    FirmsProduct,
    FirmsRateLimitError,
    FirmsRawCaptureAdapter,
    FirmsTimeoutError,
    FirmsUnavailableError,
    compute_content_hash,
    parse_firms_csv,
)
from packages.errors import MissingConfigurationError
from packages.schemas.enums import SnapshotAvailabilityState

_HEADER = (
    b"latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,"
    b"satellite,instrument,confidence,version,bright_ti5,frp,daynight\n"
)

_ROW_1 = (
    b"22.4502,70.0512,352.4,0.38,0.38,2026-08-01,0830,N,VIIRS,"
    b"nominal,2.0NRT,296.2,28.5,D\n"
)
_ROW_2 = (
    b"22.4510,70.0520,365.1,0.37,0.38,2026-08-01,0830,N,VIIRS,"
    b"high,2.0NRT,298.0,42.1,D\n"
)
_ROW_3 = (
    b"24.1025,82.6041,340.8,0.39,0.38,2026-08-02,1945,N,VIIRS,"
    b"nominal,2.0NRT,291.5,15.2,N\n"
)

_SAMPLE_CSV_BYTES = _HEADER + _ROW_1 + _ROW_2 + _ROW_3
_EMPTY_CSV_BYTES = _HEADER


class TestFirmsRequestValidation:
    """Validate client-side boundary checks on request parameters."""

    def test_valid_area_request(self) -> None:
        """Valid area request builds cleanly."""
        req = FirmsAreaRequest(
            min_longitude=68.0,
            min_latitude=20.0,
            max_longitude=72.0,
            max_latitude=24.0,
            product=FirmsProduct.VIIRS_SNPP_NRT,
            day_range=2,
            date="2026-08-01",
        )
        assert req.product == FirmsProduct.VIIRS_SNPP_NRT
        assert req.day_range == 2
        assert req.date == "2026-08-01"

    def test_inverted_latitude_raises_validation_error(self) -> None:
        """min_latitude > max_latitude raises ValidationError."""
        with pytest.raises(ValidationError):
            FirmsAreaRequest(
                min_longitude=68.0,
                min_latitude=25.0,
                max_longitude=72.0,
                max_latitude=20.0,
            )

    def test_inverted_longitude_raises_validation_error(self) -> None:
        """min_longitude > max_longitude raises ValidationError."""
        with pytest.raises(ValidationError):
            FirmsAreaRequest(
                min_longitude=75.0,
                min_latitude=20.0,
                max_longitude=70.0,
                max_latitude=24.0,
            )

    def test_out_of_bounds_coordinates_raise_validation_error(self) -> None:
        """Coordinates outside WGS-84 bounds raise ValidationError."""
        with pytest.raises(ValidationError):
            FirmsAreaRequest(
                min_longitude=68.0,
                min_latitude=-95.0,
                max_longitude=72.0,
                max_latitude=24.0,
            )

    def test_day_range_out_of_bounds_raises_validation_error(self) -> None:
        """day_range must be between 1 and 5 for Area API."""
        with pytest.raises(ValidationError):
            FirmsAreaRequest(
                min_longitude=68.0,
                min_latitude=20.0,
                max_longitude=72.0,
                max_latitude=24.0,
                day_range=6,
            )

    def test_invalid_date_format_raises_validation_error(self) -> None:
        """date must be in YYYY-MM-DD format."""
        with pytest.raises(ValidationError):
            FirmsAreaRequest(
                min_longitude=68.0,
                min_latitude=20.0,
                max_longitude=72.0,
                max_latitude=24.0,
                date="01-08-2026",
            )

    def test_valid_country_request(self) -> None:
        """Valid country code is accepted."""
        req = FirmsCountryRequest(
            country_code="IND",
            product=FirmsProduct.VIIRS_NOAA20_NRT,
            day_range=1,
        )
        assert req.country_code == "IND"

    def test_invalid_country_code_raises_validation_error(self) -> None:
        """Non-3-letter country codes are rejected."""
        with pytest.raises(ValidationError):
            FirmsCountryRequest(country_code="INDIA")


class TestFirmsRawCaptureSuccessAndEmpty:
    """Validate successful and empty raw responses."""

    def test_successful_area_capture(self) -> None:
        """Valid CSV response is captured byte-for-byte with AVAILABLE status."""
        fixed_clock = datetime(2026, 8, 30, 8, 0, 0, tzinfo=UTC)

        def mock_transport(
            _req: urllib.request.Request, _timeout: float
        ) -> tuple[int, dict[str, str], bytes]:
            return 200, {"Content-Type": "text/csv"}, _SAMPLE_CSV_BYTES

        client = FirmsClient(
            map_key=SecretStr("TEST_KEY_1234567890123456789012"),
            http_handler=mock_transport,
        )
        adapter = FirmsRawCaptureAdapter(client=client, clock_fn=lambda: fixed_clock)

        req = FirmsAreaRequest(
            min_longitude=68.0,
            min_latitude=20.0,
            max_longitude=72.0,
            max_latitude=24.0,
            product=FirmsProduct.VIIRS_SNPP_NRT,
            day_range=1,
            date="2026-08-01",
        )

        capture = adapter.capture_area(req)

        assert capture.availability_status == SnapshotAvailabilityState.AVAILABLE
        assert capture.http_status == 200
        assert capture.row_count == 3
        assert capture.raw_content == _SAMPLE_CSV_BYTES
        assert capture.content_hash == compute_content_hash(_SAMPLE_CSV_BYTES)
        assert capture.retrieved_at == fixed_clock
        assert capture.source_snapshot_id.startswith("snap_")
        assert capture.error_message is None

    def test_empty_result_capture_is_not_failure(self) -> None:
        """Header-only response is captured with EMPTY_RESULT status (NOT a failure)."""

        def mock_transport(
            _req: urllib.request.Request, _timeout: float
        ) -> tuple[int, dict[str, str], bytes]:
            return 200, {"Content-Type": "text/csv"}, _EMPTY_CSV_BYTES

        client = FirmsClient(
            map_key=SecretStr("TEST_KEY_1234567890123456789012"),
            http_handler=mock_transport,
        )
        adapter = FirmsRawCaptureAdapter(client=client)

        req = FirmsCountryRequest(
            country_code="IND",
            product=FirmsProduct.MODIS_NRT,
            day_range=1,
        )

        capture = adapter.capture_country(req)

        assert capture.availability_status == SnapshotAvailabilityState.EMPTY_RESULT
        assert capture.http_status == 200
        assert capture.row_count == 0
        assert capture.raw_content == _EMPTY_CSV_BYTES
        assert capture.error_message is None


class TestFirmsClientFailureHandlingAndRetries:
    """Validate explicit error handling, status classification, and bounded retries."""

    def test_missing_map_key_raises_configuration_error(self) -> None:
        """Missing or empty MAP_KEY raises MissingConfigurationError."""
        client = FirmsClient(map_key=None)
        req = FirmsCountryRequest(country_code="IND")
        with pytest.raises(MissingConfigurationError):
            client.build_country_url(req)

    def test_auth_failure_raises_immediately_without_retries(self) -> None:
        """HTTP 401 raises FirmsAuthenticationError immediately with 0 retries."""
        call_count = 0

        def mock_transport(
            _req: urllib.request.Request, _timeout: float
        ) -> tuple[int, dict[str, str], bytes]:
            nonlocal call_count
            call_count += 1
            return 401, {}, b"Unauthorized"

        client = FirmsClient(
            map_key=SecretStr("INVALID_KEY"),
            max_retries=3,
            http_handler=mock_transport,
        )

        with pytest.raises(FirmsAuthenticationError):
            client.execute_request("https://real.url", "https://safe.url")

        assert call_count == 1  # No retries on auth failure

    def test_rate_limit_retry_and_recovery(self) -> None:
        """HTTP 429 recovers on subsequent attempt."""
        attempts = 0
        sleeps: list[float] = []

        def mock_transport(
            _req: urllib.request.Request, _timeout: float
        ) -> tuple[int, dict[str, str], bytes]:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                return 429, {"Retry-After": "2"}, b"Too Many Requests"
            return 200, {}, _SAMPLE_CSV_BYTES

        client = FirmsClient(
            map_key=SecretStr("TEST_KEY"),
            max_retries=3,
            sleep_fn=sleeps.append,
            http_handler=mock_transport,
        )

        status, _headers, body = client.execute_request(
            "https://real.url", "https://safe.url"
        )
        assert status == 200
        assert body == _SAMPLE_CSV_BYTES
        assert attempts == 2
        assert sleeps == [2.0]

    def test_rate_limit_exhausted_raises_error(self) -> None:
        """HTTP 429 raises FirmsRateLimitError when retries are exhausted."""
        attempts = 0

        def mock_transport(
            _req: urllib.request.Request, _timeout: float
        ) -> tuple[int, dict[str, str], bytes]:
            nonlocal attempts
            attempts += 1
            return 429, {"Retry-After": "1"}, b"Too Many Requests"

        client = FirmsClient(
            map_key=SecretStr("TEST_KEY"),
            max_retries=2,
            sleep_fn=lambda s: None,
            http_handler=mock_transport,
        )

        with pytest.raises(FirmsRateLimitError) as exc_info:
            client.execute_request("https://real.url", "https://safe.url")

        assert exc_info.value.retry_after_seconds == 1.0
        assert attempts == 3  # 1 initial + 2 retries

    def test_server_error_exhausted_raises_unavailable(self) -> None:
        """HTTP 503 raises FirmsUnavailableError when retries are exhausted."""
        attempts = 0

        def mock_transport(
            _req: urllib.request.Request, _timeout: float
        ) -> tuple[int, dict[str, str], bytes]:
            nonlocal attempts
            attempts += 1
            return 503, {}, b"Service Unavailable"

        client = FirmsClient(
            map_key=SecretStr("TEST_KEY"),
            max_retries=2,
            sleep_fn=lambda s: None,
            http_handler=mock_transport,
        )

        with pytest.raises(FirmsUnavailableError):
            client.execute_request("https://real.url", "https://safe.url")

        assert attempts == 3

    def test_timeout_exhausted_raises_timeout_error(self) -> None:
        """Socket / URL timeout raises FirmsTimeoutError."""
        attempts = 0

        def mock_transport(
            _req: urllib.request.Request, _timeout: float
        ) -> tuple[int, dict[str, str], bytes]:
            nonlocal attempts
            attempts += 1
            raise urllib.error.URLError("Connection timed out")

        client = FirmsClient(
            map_key=SecretStr("TEST_KEY"),
            max_retries=1,
            sleep_fn=lambda s: None,
            http_handler=mock_transport,
        )

        with pytest.raises(FirmsTimeoutError):
            client.execute_request("https://real.url", "https://safe.url")

        assert attempts == 2

    def test_html_error_payload_raises_malformed_payload(self) -> None:
        """HTTP 200 returning HTML error page raises FirmsMalformedPayloadError."""
        html_error = (
            b"<!DOCTYPE html><html><head><title>500 Error</title></head>"
            b"<body>Server Error</body></html>"
        )

        def mock_transport(
            _req: urllib.request.Request, _timeout: float
        ) -> tuple[int, dict[str, str], bytes]:
            return 200, {"Content-Type": "text/html"}, html_error

        client = FirmsClient(
            map_key=SecretStr("TEST_KEY"),
            http_handler=mock_transport,
        )

        with pytest.raises(FirmsMalformedPayloadError) as exc_info:
            client.execute_request("https://real.url", "https://safe.url")

        assert "HTML error document" in str(exc_info.value)

    def test_provider_invalid_key_text_raises_authentication_error(self) -> None:
        """HTTP 200 returning 'Invalid MAP_KEY' raises FirmsAuthenticationError."""

        def mock_transport(
            _req: urllib.request.Request, _timeout: float
        ) -> tuple[int, dict[str, str], bytes]:
            return 200, {}, b"Invalid MAP_KEY\n"

        client = FirmsClient(
            map_key=SecretStr("TEST_KEY"),
            http_handler=mock_transport,
        )

        with pytest.raises(FirmsAuthenticationError):
            client.execute_request("https://real.url", "https://safe.url")


class TestSecretLeakageAudit:
    """Audit that secret MAP_KEY never appears in logs, exceptions, or metadata."""

    _SECRET_KEY = "SUPER_SECRET_MAP_KEY_999888777"

    def test_secret_is_never_in_safe_url(self) -> None:
        """Redacted safe URL masks the key with ***_REDACTED_***."""
        client = FirmsClient(map_key=SecretStr(self._SECRET_KEY))
        req = FirmsAreaRequest(
            min_longitude=68.0,
            min_latitude=20.0,
            max_longitude=72.0,
            max_latitude=24.0,
        )
        real_url, safe_url = client.build_area_url(req)
        assert self._SECRET_KEY in real_url
        assert self._SECRET_KEY not in safe_url
        assert "***_REDACTED_***" in safe_url

    def test_secret_is_never_in_exception_strings(self) -> None:
        """Exception messages and details never contain the secret key."""

        def mock_transport(
            _req: urllib.request.Request, _timeout: float
        ) -> tuple[int, dict[str, str], bytes]:
            return 401, {}, b"Unauthorized"

        client = FirmsClient(
            map_key=SecretStr(self._SECRET_KEY),
            http_handler=mock_transport,
        )
        adapter = FirmsRawCaptureAdapter(client=client)
        req = FirmsCountryRequest(country_code="IND")

        with pytest.raises(FirmsAuthenticationError) as exc_info:
            adapter.capture_country(req)

        exc_str = str(exc_info.value)
        assert self._SECRET_KEY not in exc_str

    def test_secret_is_never_in_raw_capture_metadata(self) -> None:
        """Captured metadata and serialized representations do not leak the key."""

        def mock_transport(
            _req: urllib.request.Request, _timeout: float
        ) -> tuple[int, dict[str, str], bytes]:
            return 200, {}, _SAMPLE_CSV_BYTES

        client = FirmsClient(
            map_key=SecretStr(self._SECRET_KEY),
            http_handler=mock_transport,
        )
        adapter = FirmsRawCaptureAdapter(client=client)
        req = FirmsCountryRequest(country_code="IND")

        capture = adapter.capture_country(req)
        metadata_str = str(capture.safe_request_metadata)
        model_dump_str = str(capture.model_dump())

        assert self._SECRET_KEY not in metadata_str
        assert self._SECRET_KEY not in model_dump_str


class TestProvenanceAndData002Integration:
    """Validate cryptographic hashing and DATA-002 canonical parser integration."""

    def test_deterministic_hashing(self) -> None:
        """Same raw bytes produce identical content_hash."""
        h1 = compute_content_hash(_SAMPLE_CSV_BYTES)
        h2 = compute_content_hash(_SAMPLE_CSV_BYTES)
        h_empty = compute_content_hash(_EMPTY_CSV_BYTES)

        assert h1 == h2
        assert len(h1) == 64
        assert h1 != h_empty

    def test_data002_parser_integration_on_captured_payload(self) -> None:
        """Captured raw payload is parsed into canonical Detection models."""

        def mock_transport(
            _req: urllib.request.Request, _timeout: float
        ) -> tuple[int, dict[str, str], bytes]:
            return 200, {}, _SAMPLE_CSV_BYTES

        client = FirmsClient(
            map_key=SecretStr("TEST_KEY"),
            http_handler=mock_transport,
        )
        adapter = FirmsRawCaptureAdapter(client=client)
        req = FirmsAreaRequest(
            min_longitude=68.0,
            min_latitude=20.0,
            max_longitude=72.0,
            max_latitude=24.0,
            product=FirmsProduct.VIIRS_SNPP_NRT,
        )

        capture = adapter.capture_area(req)
        assert capture.availability_status == SnapshotAvailabilityState.AVAILABLE

        # Pass raw captured payload directly to DATA-002 parser
        detections = parse_firms_csv(
            csv_input=capture.raw_content_str,
            source_snapshot_id=capture.source_snapshot_id,
            product_type="nrt",
            product_version=capture.product_version,
        )

        assert len(detections) == 3
        assert detections[0].source_snapshot_id == capture.source_snapshot_id
        assert detections[0].source == "firms"
        assert detections[0].geometry.latitude == 22.4502
