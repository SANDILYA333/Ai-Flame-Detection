"""High-level NASA FIRMS raw capture adapter for deterministic source snapshots."""

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from packages.data.firms.client import FirmsClient
from packages.data.firms.schemas import (
    FirmsAreaRequest,
    FirmsCountryRequest,
    FirmsRawCapture,
)
from packages.schemas.enums import SnapshotAvailabilityState


def compute_request_fingerprint(safe_metadata: dict[str, Any]) -> str:
    """Compute deterministic SHA-256 fingerprint from sanitized request parameters."""
    canonical_json = json.dumps(
        safe_metadata, sort_keys=True, ensure_ascii=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def compute_content_hash(raw_bytes: bytes) -> str:
    """Compute SHA-256 cryptographic hash of exact raw response bytes."""
    return hashlib.sha256(raw_bytes).hexdigest()


def count_csv_data_rows(csv_text: str) -> int:
    """Count non-empty active fire data rows (excluding header and trailing blanks)."""
    if not csv_text or not csv_text.strip():
        return 0
    lines = [line.strip() for line in csv_text.splitlines() if line.strip()]
    if len(lines) <= 1:
        return 0
    return len(lines) - 1


class FirmsRawCaptureAdapter:
    """External FIRMS retrieval and immutable raw capture boundary adapter.

    Coordinates authenticated requests, computes hashes, generates
    deterministic snapshot identifiers, and distinguishes available data from empty.
    """

    def __init__(
        self,
        client: FirmsClient | None = None,
        clock_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self.client = client or FirmsClient()
        self.clock_fn = clock_fn or (lambda: datetime.now(tz=UTC))

    def capture_area(self, request: FirmsAreaRequest) -> FirmsRawCapture:
        """Execute Area query and capture exact provider response as immutable artifact.

        Args:
            request: Validated bounding-box request parameters.

        Returns:
            FirmsRawCapture: Immutable raw capture model with complete provenance.
        """
        real_url, safe_url = self.client.build_area_url(request)

        safe_metadata: dict[str, Any] = {
            "endpoint": "area",
            "product": request.product.value,
            "min_longitude": request.min_longitude,
            "min_latitude": request.min_latitude,
            "max_longitude": request.max_longitude,
            "max_latitude": request.max_latitude,
            "day_range": request.day_range,
            "date": request.date,
            "safe_url": safe_url,
        }
        request_fingerprint = compute_request_fingerprint(safe_metadata)

        status_code, _headers, raw_bytes = self.client.execute_request(
            real_url, safe_url
        )
        retrieved_at = self.clock_fn()
        content_hash = compute_content_hash(raw_bytes)
        raw_str = raw_bytes.decode("utf-8", errors="replace")

        row_count = count_csv_data_rows(raw_str)
        availability_status = (
            SnapshotAvailabilityState.AVAILABLE
            if row_count > 0
            else SnapshotAvailabilityState.EMPTY_RESULT
        )

        # Deterministic snapshot ID based on request fingerprint and content hash
        snapshot_seed = f"{request_fingerprint}:{content_hash}"
        seed_hash = hashlib.sha256(snapshot_seed.encode("utf-8")).hexdigest()[:16]
        snapshot_id = f"snap_{seed_hash}"

        return FirmsRawCapture(
            source_snapshot_id=snapshot_id,
            source_id="firms",
            product=request.product.value,
            product_version="v2.0",
            request_fingerprint=request_fingerprint,
            raw_content=raw_bytes,
            raw_content_str=raw_str,
            content_hash=content_hash,
            retrieved_at=retrieved_at,
            availability_status=availability_status,
            http_status=status_code,
            safe_request_metadata=safe_metadata,
            row_count=row_count,
            error_message=None,
            error_code=None,
        )

    def capture_country(self, request: FirmsCountryRequest) -> FirmsRawCapture:
        """Execute Country query and capture exact response as immutable artifact.

        Args:
            request: Validated country query parameters.

        Returns:
            FirmsRawCapture: Immutable raw capture model with complete provenance.
        """
        real_url, safe_url = self.client.build_country_url(request)

        safe_metadata: dict[str, Any] = {
            "endpoint": "country",
            "product": request.product.value,
            "country_code": request.country_code,
            "day_range": request.day_range,
            "date": request.date,
            "safe_url": safe_url,
        }
        request_fingerprint = compute_request_fingerprint(safe_metadata)

        status_code, _headers, raw_bytes = self.client.execute_request(
            real_url, safe_url
        )
        retrieved_at = self.clock_fn()
        content_hash = compute_content_hash(raw_bytes)
        raw_str = raw_bytes.decode("utf-8", errors="replace")

        row_count = count_csv_data_rows(raw_str)
        availability_status = (
            SnapshotAvailabilityState.AVAILABLE
            if row_count > 0
            else SnapshotAvailabilityState.EMPTY_RESULT
        )

        snapshot_seed = f"{request_fingerprint}:{content_hash}"
        seed_hash = hashlib.sha256(snapshot_seed.encode("utf-8")).hexdigest()[:16]
        snapshot_id = f"snap_{seed_hash}"

        return FirmsRawCapture(
            source_snapshot_id=snapshot_id,
            source_id="firms",
            product=request.product.value,
            product_version="v2.0",
            request_fingerprint=request_fingerprint,
            raw_content=raw_bytes,
            raw_content_str=raw_str,
            content_hash=content_hash,
            retrieved_at=retrieved_at,
            availability_status=availability_status,
            http_status=status_code,
            safe_request_metadata=safe_metadata,
            row_count=row_count,
            error_message=None,
            error_code=None,
        )
