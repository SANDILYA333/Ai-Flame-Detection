"""API request and response schemas."""

from packages.schemas.intelligence import IntelligenceResult
from services.api.schemas.detections import (
    DetectionPagination,
    DetectionsResponse,
)
from services.api.schemas.events import (
    EventDetailResponse,
    EventEvidenceResponse,
    EventPagination,
    EventResponse,
    EventsResponse,
    EventTimelineResponse,
    TimelineObservation,
)
from services.api.schemas.health import HealthResponse
from services.api.schemas.inference import (
    BatchPredictionRequestBody,
    BatchPredictionResponseBody,
    FirmsCsvPredictionRequestBody,
    FirmsCsvPredictionResponseBody,
    FirmsMLPredictionResponseBody,
    PredictionRequestBody,
    PredictionResponseBody,
)
from services.api.schemas.layers import (
    GeoJsonFeature,
    GeoJsonFeatureCollection,
    GeoJsonGeometry,
)
from services.api.schemas.readiness import (
    DependencyHealth,
    DependencyStatus,
    ReadinessResponse,
)
from services.api.schemas.sources import (
    SourceAvailabilityState,
    SourceOperationalMode,
    SourcesStatusResponse,
    SourceStatusItem,
)
from services.api.schemas.version import (
    VersionContracts,
    VersionResponse,
)

__all__ = [
    "BatchPredictionRequestBody",
    "BatchPredictionResponseBody",
    "DependencyHealth",
    "DependencyStatus",
    "DetectionPagination",
    "DetectionsResponse",
    "EventDetailResponse",
    "EventEvidenceResponse",
    "EventPagination",
    "EventResponse",
    "EventTimelineResponse",
    "EventsResponse",
    "FirmsCsvPredictionRequestBody",
    "FirmsCsvPredictionResponseBody",
    "FirmsMLPredictionResponseBody",
    "GeoJsonFeature",
    "GeoJsonFeatureCollection",
    "GeoJsonGeometry",
    "HealthResponse",
    "IntelligenceResult",
    "PredictionRequestBody",
    "PredictionResponseBody",
    "ReadinessResponse",
    "SourceAvailabilityState",
    "SourceOperationalMode",
    "SourceStatusItem",
    "SourcesStatusResponse",
    "TimelineObservation",
    "VersionContracts",
    "VersionResponse",
]
