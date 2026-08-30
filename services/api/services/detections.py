"""Application service for querying canonical detection observations (API-005)."""

from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from packages.data.firms.activation import FirmsDataActivationService
from packages.errors import ValidationError
from packages.feasibility.candidates import JAMNAGAR_KUTCH
from packages.schemas.detection import Detection
from packages.schemas.enums import DayNight
from services.api.schemas.detections import (
    DetectionPagination,
    DetectionsResponse,
)

_FIXTURE_PATH = Path("fixtures/firms/firms_real_sample_jamnagar.csv")
_DEFAULT_START_DATE = "2026-08-01"
_DEFAULT_END_DATE = "2026-08-03"


class DetectionQueryService:
    """Service orchestrating querying, filtering, and pagination of detections."""

    _cached_detections: list[Detection] | None = None

    @classmethod
    def get_canonical_detections(cls) -> list[Detection]:
        """Load and cache canonical detection records from authoritative source."""
        if cls._cached_detections is None:
            if _FIXTURE_PATH.exists():
                dataset = FirmsDataActivationService.activate_from_csv(
                    csv_input=_FIXTURE_PATH,
                    study_area=JAMNAGAR_KUTCH,
                    requested_start_date=_DEFAULT_START_DATE,
                    requested_end_date=_DEFAULT_END_DATE,
                )
                cls._cached_detections = list(dataset.detections)
            else:
                cls._cached_detections = []
        return cls._cached_detections

    @classmethod
    def set_mock_detections(cls, detections: Sequence[Detection] | None) -> None:
        """Override cached detections for testing purposes."""
        cls._cached_detections = list(detections) if detections is not None else None

    @classmethod
    def query_detections(
        cls,
        *,
        min_lat: float | None = None,
        max_lat: float | None = None,
        min_lon: float | None = None,
        max_lon: float | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        source: str | None = None,
        satellite: str | None = None,
        instrument: str | None = None,
        day_night: DayNight | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> DetectionsResponse:
        """Query canonical detections with spatial, temporal, and metadata filters."""
        # 1. Validate bounding box coordinates
        bbox_coords = [min_lat, max_lat, min_lon, max_lon]
        has_any_bbox = any(c is not None for c in bbox_coords)
        has_all_bbox = all(c is not None for c in bbox_coords)

        if has_any_bbox and not has_all_bbox:
            raise ValidationError(
                "Bounding box query requires all four coordinates: "
                "min_lat, max_lat, min_lon, max_lon."
            )

        if has_all_bbox:
            assert min_lat is not None and max_lat is not None
            assert min_lon is not None and max_lon is not None
            if min_lat > max_lat:
                raise ValidationError("Bounding box min_lat cannot exceed max_lat.")
            if min_lon > max_lon:
                raise ValidationError("Bounding box min_lon cannot exceed max_lon.")

        # 2. Validate time range boundaries
        if start_time is not None and start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=UTC)
        if end_time is not None and end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=UTC)

        if start_time is not None and end_time is not None and start_time > end_time:
            raise ValidationError("start_time cannot be later than end_time.")

        # 3. Retrieve canonical dataset
        detections = cls.get_canonical_detections()

        # 4. Apply filtering
        filtered: list[Detection] = []
        for det in detections:
            # Spatial filter
            if has_all_bbox:
                assert min_lat is not None and max_lat is not None
                assert min_lon is not None and max_lon is not None
                lat = det.geometry.latitude
                lon = det.geometry.longitude
                if not (min_lat <= lat <= max_lat and min_lon <= lon <= max_lon):
                    continue

            # Temporal filter
            if start_time is not None and det.acquired_at < start_time:
                continue
            if end_time is not None and det.acquired_at > end_time:
                continue

            # Source / product filter
            if source is not None:
                query_src = source.strip().lower()
                if (
                    query_src not in det.source.lower()
                    and query_src not in det.product_type.lower()
                ):
                    continue

            # Satellite filter
            if (
                satellite is not None
                and det.satellite.strip().lower() != satellite.strip().lower()
            ):
                continue

            # Instrument filter
            if (
                instrument is not None
                and det.instrument.strip().lower() != instrument.strip().lower()
            ):
                continue

            # Day / Night filter
            if day_night is not None and det.day_night != day_night:
                continue

            filtered.append(det)

        # 5. Deterministic sorting: acquired_at ascending, then detection_id ascending
        filtered.sort(key=lambda d: (d.acquired_at, d.detection_id))

        # 6. Apply pagination
        total_count = len(filtered)
        paginated_detections = filtered[offset : offset + limit]
        has_next = (offset + limit) < total_count

        pagination = DetectionPagination(
            total_count=total_count,
            limit=limit,
            offset=offset,
            has_next=has_next,
        )

        return DetectionsResponse(
            service="sih26162-api",
            pagination=pagination,
            detections=paginated_detections,
        )
