"""Low-level HTTP client for NASA FIRMS API with bounded retries."""

import logging
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable

from pydantic import SecretStr

from packages.config import get_settings
from packages.data.firms.errors import (
    FirmsAuthenticationError,
    FirmsMalformedPayloadError,
    FirmsRateLimitError,
    FirmsTimeoutError,
    FirmsUnavailableError,
)
from packages.data.firms.schemas import FirmsAreaRequest, FirmsCountryRequest
from packages.errors import MissingConfigurationError

logger = logging.getLogger(__name__)

_REDACTED_MASK = "***_REDACTED_***"


class FirmsClient:
    """Authenticated HTTP client for communicating with NASA FIRMS API.

    Features:
    - Zero secret leakage in URLs, exceptions, and logs.
    - Bounded exponential backoff retries for transient failures.
    - Explicit classification of 401, 403, 429, 5xx, timeouts, and error responses.
    - Pluggable transport handler and sleep function for deterministic testing.
    """

    def __init__(
        self,
        base_url: str | None = None,
        map_key: SecretStr | str | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
        retry_backoff_factor: float | None = None,
        user_agent: str | None = None,
        sleep_fn: Callable[[float], None] | None = None,
        http_handler: (
            Callable[[urllib.request.Request, float], tuple[int, dict[str, str], bytes]]
            | None
        ) = None,
    ) -> None:
        settings = get_settings()

        self.base_url = (base_url or settings.FIRMS_BASE_URL).rstrip("/")
        self.map_key: SecretStr | None
        if isinstance(map_key, str):
            self.map_key = SecretStr(map_key)
        elif isinstance(map_key, SecretStr):
            self.map_key = map_key
        else:
            self.map_key = settings.FIRMS_MAP_KEY

        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.FIRMS_TIMEOUT_SECONDS
        )
        self.max_retries = (
            max_retries if max_retries is not None else settings.FIRMS_MAX_RETRIES
        )
        self.retry_backoff_factor = (
            retry_backoff_factor
            if retry_backoff_factor is not None
            else settings.FIRMS_RETRY_BACKOFF_FACTOR
        )
        self.user_agent = user_agent or settings.FIRMS_USER_AGENT
        self.sleep_fn = sleep_fn or (lambda s: None)
        self._http_handler = http_handler

    def build_area_url(self, request: FirmsAreaRequest) -> tuple[str, str]:
        """Construct real and redacted URLs for Area query.

        Returns:
            tuple[str, str]: (real_url_with_key, redacted_safe_url)
        """
        key_val = self._get_resolved_key()
        area_coords = (
            f"{request.min_longitude},{request.min_latitude},"
            f"{request.max_longitude},{request.max_latitude}"
        )

        path_parts = [
            self.base_url,
            "area",
            "csv",
            key_val,
            request.product.value,
            area_coords,
            str(request.day_range),
        ]
        redacted_parts = [
            self.base_url,
            "area",
            "csv",
            _REDACTED_MASK,
            request.product.value,
            area_coords,
            str(request.day_range),
        ]

        if request.date:
            path_parts.append(request.date.strip())
            redacted_parts.append(request.date.strip())

        return "/".join(path_parts), "/".join(redacted_parts)

    def build_country_url(self, request: FirmsCountryRequest) -> tuple[str, str]:
        """Construct real and redacted URLs for Country query.

        Returns:
            tuple[str, str]: (real_url_with_key, redacted_safe_url)
        """
        key_val = self._get_resolved_key()
        path_parts = [
            self.base_url,
            "country",
            "csv",
            key_val,
            request.product.value,
            request.country_code,
            str(request.day_range),
        ]
        redacted_parts = [
            self.base_url,
            "country",
            "csv",
            _REDACTED_MASK,
            request.product.value,
            request.country_code,
            str(request.day_range),
        ]

        if request.date:
            path_parts.append(request.date.strip())
            redacted_parts.append(request.date.strip())

        return "/".join(path_parts), "/".join(redacted_parts)

    def _get_resolved_key(self) -> str:
        """Resolve and validate MAP_KEY existence."""
        if self.map_key is None:
            raise MissingConfigurationError(
                "FIRMS_MAP_KEY is not configured.",
                details={"source": "firms"},
            )
        val = self.map_key.get_secret_value().strip()
        if not val:
            raise MissingConfigurationError(
                "FIRMS_MAP_KEY is empty. A valid 32-char MAP_KEY is required.",
                details={"source": "firms"},
            )
        return val

    def _default_transport(
        self, req: urllib.request.Request, timeout: float
    ) -> tuple[int, dict[str, str], bytes]:
        """Default HTTP transport using urllib.request."""
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = resp.status if hasattr(resp, "status") else resp.getcode()
                headers = dict(resp.headers.items())
                body = resp.read()
                return status, headers, body
        except urllib.error.HTTPError as e:
            status = e.code
            headers = dict(e.headers.items()) if e.headers else {}
            body = e.read() if hasattr(e, "read") else b""
            return status, headers, body

    def execute_request(
        self, real_url: str, safe_url: str
    ) -> tuple[int, dict[str, str], bytes]:
        """Execute HTTP request with bounded retry and status classification.

        Args:
            real_url: Full credential-bearing request URL.
            safe_url: Redacted URL for logs and exceptions.

        Returns:
            tuple[int, dict[str, str], bytes]: (status, headers, body)

        Raises:
            FirmsAuthenticationError: On 401/403 or invalid MAP_KEY.
            FirmsRateLimitError: On 429 after retries exhausted.
            FirmsUnavailableError: On 5xx server errors after retries exhausted.
            FirmsTimeoutError: On request timeout after retries exhausted.
            FirmsMalformedPayloadError: On HTML error body or corrupted payload.
        """
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/csv, application/csv, text/plain, */*",
        }
        req = urllib.request.Request(real_url, headers=headers, method="GET")

        attempt = 0
        while True:
            attempt += 1
            try:
                if self._http_handler:
                    status, resp_headers, body = self._http_handler(
                        req, self.timeout_seconds
                    )
                else:
                    status, resp_headers, body = self._default_transport(
                        req, self.timeout_seconds
                    )

                # 1. Handle HTTP 200 (Success or provider body error)
                if status == 200:
                    self._validate_csv_payload(body, safe_url)
                    return status, resp_headers, body

                # 2. Handle HTTP 401 / 403 Authentication failure (No retry)
                if status in (401, 403):
                    raise FirmsAuthenticationError(
                        f"NASA FIRMS authentication rejected with HTTP {status}.",
                        details={"safe_url": safe_url, "http_status": status},
                    )

                # 3. Handle HTTP 429 Rate Limit
                if status == 429:
                    retry_after_str = resp_headers.get("Retry-After")
                    retry_after = (
                        float(retry_after_str)
                        if retry_after_str and retry_after_str.isdigit()
                        else None
                    )

                    if attempt <= self.max_retries:
                        sleep_time = (
                            retry_after
                            if retry_after is not None
                            else self.retry_backoff_factor * (2 ** (attempt - 1))
                        )
                        logger.warning(
                            "FIRMS rate limit (429). Attempt %d/%d (wait %.2fs)",
                            attempt,
                            self.max_retries,
                            sleep_time,
                        )
                        self.sleep_fn(sleep_time)
                        continue

                    raise FirmsRateLimitError(
                        f"FIRMS rate limit exceeded after {attempt} attempts.",
                        retry_after_seconds=retry_after,
                        details={"safe_url": safe_url, "http_status": 429},
                    )

                # 4. Handle HTTP 5xx Server Errors (Transient)
                if 500 <= status <= 599:
                    if attempt <= self.max_retries:
                        sleep_time = self.retry_backoff_factor * (2 ** (attempt - 1))
                        logger.warning(
                            "FIRMS server error (%d). Attempt %d/%d (wait %.2fs)",
                            status,
                            attempt,
                            self.max_retries,
                            sleep_time,
                        )
                        self.sleep_fn(sleep_time)
                        continue

                    raise FirmsUnavailableError(
                        f"FIRMS unavailable (HTTP {status}) after {attempt} attempts.",
                        details={"safe_url": safe_url, "http_status": status},
                    )

                # 5. Other HTTP client errors (400, 404, etc.)
                raise FirmsMalformedPayloadError(
                    f"NASA FIRMS request failed with HTTP {status}.",
                    details={"safe_url": safe_url, "http_status": status},
                )

            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt <= self.max_retries:
                    sleep_time = self.retry_backoff_factor * (2 ** (attempt - 1))
                    logger.warning(
                        "NASA FIRMS network error: %s. Attempt %d/%d (wait %.2fs)",
                        str(exc),
                        attempt,
                        self.max_retries,
                        sleep_time,
                    )
                    self.sleep_fn(sleep_time)
                    continue

                raise FirmsTimeoutError(
                    f"NASA FIRMS request timed out after {attempt} attempts.",
                    details={"safe_url": safe_url, "error": str(exc)},
                ) from exc

    def _validate_csv_payload(self, body: bytes, safe_url: str) -> None:
        """Validate that HTTP 200 payload is valid CSV, not provider HTML/error."""
        if not body:
            # Empty bytes is considered valid empty response (0 records)
            return

        try:
            text = body.decode("utf-8", errors="replace").strip()
        except Exception as exc:
            raise FirmsMalformedPayloadError(
                "NASA FIRMS returned non-UTF8 binary payload.",
                details={"safe_url": safe_url, "error": str(exc)},
            ) from exc

        lower_text = text.lower()

        # Check for HTML error document
        if lower_text.startswith("<!doctype html") or lower_text.startswith("<html"):
            raise FirmsMalformedPayloadError(
                "NASA FIRMS returned an HTML error document instead of CSV.",
                details={
                    "safe_url": safe_url,
                    "preview": text[:200],
                },
            )

        # Check for known provider error text responses
        if "invalid map_key" in lower_text or "invalid map key" in lower_text:
            raise FirmsAuthenticationError(
                "NASA FIRMS returned 'Invalid MAP_KEY' error.",
                details={"safe_url": safe_url},
            )

        if lower_text.startswith("error:") or lower_text.startswith("bad request"):
            raise FirmsMalformedPayloadError(
                f"NASA FIRMS returned provider error: {text[:150]}",
                details={"safe_url": safe_url, "error_preview": text[:200]},
            )
