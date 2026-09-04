"""FastAPI route handlers for Forest Intelligence (Phase 1, 2, 3)."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from packages.data.forests.client import OverpassApiError
from packages.data.forests.service import ForestIngestionService
from packages.data.forests.threat_service import get_forest_threat_service
from packages.errors import NotFoundError
from services.api.schemas.forests import (
    BoundingBoxModel,
    ForestDetailResponse,
    ForestIngestionRequest,
    ForestIngestionResponse,
    ForestMonitoringDashboardResponse,
    ForestProximityAlertRequest,
    ForestProximityAlertResponse,
    ForestThreatAssessmentResponse,
    ForestThreatCandidateEventResponse,
    ForestThreatDetailResponse,
    ForestThreatSummaryItemResponse,
    GlobalForestMonitoringSummaryResponse,
    NearbyForestsListResponse,
    NearbyForestThreatItemResponse,
    ThreatConfigurationModel,
)
from services.api.schemas.layers import GeoJsonFeatureCollection
from services.api.services.forests import ForestQueryService

router = APIRouter(prefix="/forests", tags=["forests"])


@router.get(
    "",
    response_model=GeoJsonFeatureCollection,
    summary="Retrieve global forest areas as GeoJSON FeatureCollection",
    description=(
        "Returns a RFC 7946 GeoJSON FeatureCollection of normalized OSM forest "
        "polygons. Supports filtering by country ISO code, bounding box, category, "
        "or search term."
    ),
)
def list_forests(
    country_code: Annotated[
        str | None,
        Query(description="ISO 3166-1 alpha-2 country code (e.g. 'IN')"),
    ] = None,
    bbox: Annotated[
        str | None,
        Query(
            description=(
                "Bounding box string formatted 'min_lon,min_lat,max_lon,max_lat'"
            )
        ),
    ] = None,
    min_lat: Annotated[
        float | None,
        Query(ge=-90.0, le=90.0, description="South boundary"),
    ] = None,
    min_lon: Annotated[
        float | None,
        Query(ge=-180.0, le=180.0, description="West boundary"),
    ] = None,
    max_lat: Annotated[
        float | None,
        Query(ge=-90.0, le=90.0, description="North boundary"),
    ] = None,
    max_lon: Annotated[
        float | None,
        Query(ge=-180.0, le=180.0, description="East boundary"),
    ] = None,
    forest_type: Annotated[
        str | None,
        Query(
            description="Filter by forest category ('natural_wood', 'landuse_forest')"
        ),
    ] = None,
    search: Annotated[
        str | None,
        Query(description="Search term in forest name or designation"),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=1000, description="Maximum number of features"),
    ] = 100,
    offset: Annotated[
        int,
        Query(ge=0, description="Pagination offset"),
    ] = 0,
) -> GeoJsonFeatureCollection:
    """Retrieve canonical forest areas matching spatial or attribute filters."""
    return ForestQueryService.query_forests_geojson(
        country=country_code,
        bbox=bbox,
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        forest_type=forest_type,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/ingest",
    response_model=ForestIngestionResponse,
    status_code=status.HTTP_200_OK,
    operation_id="ingest_forests",
    summary="Trigger administrative OSM forest data ingestion for a bounding box",
    description=(
        "Queries OpenStreetMap Overpass API for natural=wood and landuse=forest "
        "polygons within the specified bounding box, normalizes geometries, "
        "and idempotently persists them."
    ),
)
def ingest_forests(
    request: ForestIngestionRequest,
) -> ForestIngestionResponse:
    """Execute OSM forest data ingestion over a bounded geographic region."""
    try:
        south, west, north, east = request.get_resolved_bounds()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e

    service = ForestIngestionService()
    try:
        stats = service.ingest_by_bbox(
            min_lat=south,
            min_lon=west,
            max_lat=north,
            max_lon=east,
            country_code=request.country_code,
            dry_run=request.dry_run,
            limit=request.limit,
            include_boundary=request.include_boundary,
        )
    except OverpassApiError as oae:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"OpenStreetMap Overpass API request failed: {oae}",
        ) from oae
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Forest ingestion error: {e}",
        ) from e

    return ForestIngestionResponse(
        success=True,
        source="openstreetmap",
        bounding_box=BoundingBoxModel(
            south=south,
            west=west,
            north=north,
            east=east,
        ),
        statistics=stats.model_dump(),
        message="Forest ingestion completed successfully.",
    )


@router.get(
    "/nearby",
    response_model=NearbyForestsListResponse,
    status_code=status.HTTP_200_OK,
    operation_id="get_nearby_forests",
    summary="Query nearby forests by geodesic proximity",
    description=(
        "Returns nearby forest tracts ordered by ascending geodesic distance (km) "
        "relative to a thermal event or reference coordinate."
    ),
)
def get_nearby_forests(
    latitude: Annotated[
        float,
        Query(description="Query point latitude in decimal degrees", ge=-90, le=90),
    ],
    longitude: Annotated[
        float,
        Query(description="Query point longitude in decimal degrees", ge=-180, le=180),
    ],
    radius_km: Annotated[
        float, Query(description="Search radius in kilometers", ge=0.1, le=2000.0)
    ] = 25.0,
    limit: Annotated[
        int, Query(description="Maximum nearby records to return", ge=1, le=200)
    ] = 50,
) -> NearbyForestsListResponse:
    """Find nearby forests ordered by geodesic distance."""
    return ForestQueryService.find_nearby_forests(
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        limit=limit,
    )


@router.get(
    "/threat/evaluate",
    response_model=ForestThreatAssessmentResponse,
    status_code=status.HTTP_200_OK,
    operation_id="evaluate_forest_threat_point",
    summary="Evaluate fire-to-forest proximity threat for arbitrary coordinates",
    description=(
        "Calculates geodesic distance from a fire coordinate to actual polygon "
        "boundaries of all nearby forest areas, evaluating proximity threat."
    ),
)
def evaluate_forest_threat_point(
    latitude: Annotated[
        float,
        Query(description="Fire point latitude in decimal degrees", ge=-90, le=90),
    ],
    longitude: Annotated[
        float,
        Query(description="Fire point longitude in decimal degrees", ge=-180, le=180),
    ],
    fire_event_id: Annotated[
        str | None,
        Query(description="Optional thermal event ID"),
    ] = None,
    search_radius_km: Annotated[
        float | None,
        Query(description="Optional candidate search radius in km", ge=0.1, le=500.0),
    ] = None,
    threat_radius_km: Annotated[
        float | None,
        Query(
            description="Optional proximity threat threshold in km", ge=0.1, le=100.0
        ),
    ] = None,
) -> ForestThreatAssessmentResponse:
    """Evaluate proximity threat for a fire location."""
    threat_service = get_forest_threat_service()
    assessment = threat_service.evaluate_fire_point(
        latitude=latitude,
        longitude=longitude,
        fire_event_id=fire_event_id,
        search_radius_km=search_radius_km,
        threat_radius_km=threat_radius_km,
    )

    nearest_resp = None
    if assessment.nearest_forest:
        nf = assessment.nearest_forest
        nearest_resp = NearbyForestThreatItemResponse(
            forest_id=nf.forest_id,
            osm_identity=nf.osm_identity,
            name=nf.name,
            country_code=nf.country_code,
            forest_type=nf.forest_type.value,
            osm_tag=nf.osm_tag,
            distance_km=nf.distance_km,
            is_within_threat_radius=nf.is_within_threat_radius,
            threat_level=nf.threat_level.value,
            nearest_point=nf.nearest_point,
            centroid=nf.centroid,
            area_km2=nf.area_km2,
        )

    nearby_resps = [
        NearbyForestThreatItemResponse(
            forest_id=item.forest_id,
            osm_identity=item.osm_identity,
            name=item.name,
            country_code=item.country_code,
            forest_type=item.forest_type.value,
            osm_tag=item.osm_tag,
            distance_km=item.distance_km,
            is_within_threat_radius=item.is_within_threat_radius,
            threat_level=item.threat_level.value,
            nearest_point=item.nearest_point,
            centroid=item.centroid,
            area_km2=item.area_km2,
        )
        for item in assessment.nearby_forests
    ]

    return ForestThreatAssessmentResponse(
        success=True,
        fire_event_id=assessment.fire_event_id,
        fire_coordinate=assessment.fire_coordinate,
        configuration=ThreatConfigurationModel(
            search_radius_km=assessment.search_radius_km,
            threat_radius_km=assessment.threat_radius_km,
            critical_radius_km=assessment.critical_radius_km,
            high_radius_km=assessment.high_radius_km,
            moderate_radius_km=assessment.moderate_radius_km,
        ),
        is_threatened=assessment.is_threatened,
        threat_level=assessment.threat_level.value,
        nearest_forest=nearest_resp,
        nearby_forests=nearby_resps,
        total_threatened_forests=assessment.total_threatened_forests,
        evaluated_at=assessment.evaluated_at.isoformat(),
    )


@router.get(
    "/threat/{event_id}",
    response_model=ForestThreatAssessmentResponse,
    status_code=status.HTTP_200_OK,
    operation_id="evaluate_forest_threat_event",
    summary="Evaluate fire-to-forest proximity threat for an existing thermal event",
    description=(
        "Retrieves canonical thermal event coordinates and computes geodesic "
        "boundary distance to all nearby forest areas with operational threat levels."
    ),
)
def evaluate_forest_threat_event(
    event_id: str,
    search_radius_km: Annotated[
        float | None,
        Query(description="Optional candidate search radius in km", ge=0.1, le=500.0),
    ] = None,
    threat_radius_km: Annotated[
        float | None,
        Query(
            description="Optional proximity threat threshold in km", ge=0.1, le=100.0
        ),
    ] = None,
) -> ForestThreatAssessmentResponse:
    """Evaluate proximity threat for a canonical thermal event ID."""
    threat_service = get_forest_threat_service()
    try:
        assessment = threat_service.evaluate_fire_event_by_id(
            event_id=event_id,
            search_radius_km=search_radius_km,
            threat_radius_km=threat_radius_km,
        )
    except NotFoundError as nfe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(nfe),
        ) from nfe
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Threat evaluation failed: {e}",
        ) from e

    nearest_resp = None
    if assessment.nearest_forest:
        nf = assessment.nearest_forest
        nearest_resp = NearbyForestThreatItemResponse(
            forest_id=nf.forest_id,
            osm_identity=nf.osm_identity,
            name=nf.name,
            country_code=nf.country_code,
            forest_type=nf.forest_type.value,
            osm_tag=nf.osm_tag,
            distance_km=nf.distance_km,
            is_within_threat_radius=nf.is_within_threat_radius,
            threat_level=nf.threat_level.value,
            nearest_point=nf.nearest_point,
            centroid=nf.centroid,
            area_km2=nf.area_km2,
        )

    nearby_resps = [
        NearbyForestThreatItemResponse(
            forest_id=item.forest_id,
            osm_identity=item.osm_identity,
            name=item.name,
            country_code=item.country_code,
            forest_type=item.forest_type.value,
            osm_tag=item.osm_tag,
            distance_km=item.distance_km,
            is_within_threat_radius=item.is_within_threat_radius,
            threat_level=item.threat_level.value,
            nearest_point=item.nearest_point,
            centroid=item.centroid,
            area_km2=item.area_km2,
        )
        for item in assessment.nearby_forests
    ]

    return ForestThreatAssessmentResponse(
        success=True,
        fire_event_id=assessment.fire_event_id,
        fire_coordinate=assessment.fire_coordinate,
        configuration=ThreatConfigurationModel(
            search_radius_km=assessment.search_radius_km,
            threat_radius_km=assessment.threat_radius_km,
            critical_radius_km=assessment.critical_radius_km,
            high_radius_km=assessment.high_radius_km,
            moderate_radius_km=assessment.moderate_radius_km,
        ),
        is_threatened=assessment.is_threatened,
        threat_level=assessment.threat_level.value,
        nearest_forest=nearest_resp,
        nearby_forests=nearby_resps,
        total_threatened_forests=assessment.total_threatened_forests,
        evaluated_at=assessment.evaluated_at.isoformat(),
    )


@router.post(
    "/threat/alert",
    response_model=ForestProximityAlertResponse,
    status_code=status.HTTP_200_OK,
    operation_id="dispatch_forest_proximity_alert",
    summary="Evaluate and dispatch proximity alert for a fire threatening a forest",
    description=(
        "Evaluates the real-time distance from fire event to the specified forest, "
        "determines threat classification, checks deduplication and escalation state, "
        "and triggers multi-channel emergency notification if threat criteria are met."
    ),
)
def dispatch_forest_proximity_alert(
    request: ForestProximityAlertRequest,
) -> ForestProximityAlertResponse:
    """Generate forest proximity alert and dispatch notifications if warranted."""
    threat_service = get_forest_threat_service()
    try:
        alert_event = threat_service.create_forest_proximity_alert(
            event_id=request.event_id,
            forest_id=request.forest_id,
            fire_confidence=request.fire_confidence,
            recipient_phone=request.recipient_phone,
            channels=request.channels,
            force_dispatch=request.force_dispatch,
        )
    except NotFoundError as nfe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(nfe),
        ) from nfe
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(ve),
        ) from ve
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Proximity alert generation failed: {e}",
        ) from e

    return ForestProximityAlertResponse(
        success=True,
        alert_id=alert_event.alert_id,
        event_id=alert_event.event_id,
        forest_id=alert_event.forest_id,
        forest_name=alert_event.forest_name,
        distance_km=alert_event.distance_km,
        inside_forest=alert_event.inside_forest,
        threat_level=alert_event.threat_level.value,
        is_escalation=alert_event.is_escalation,
        notification_dispatched=alert_event.notification_dispatched,
        notification_id=alert_event.notification_id,
        created_at=alert_event.created_at.isoformat(),
    )


@router.get(
    "/threats/monitoring",
    response_model=ForestMonitoringDashboardResponse,
    status_code=status.HTTP_200_OK,
    operation_id="get_forest_monitoring_dashboard",
    summary="Retrieve global forest threat monitoring dashboard",
    description=(
        "Returns system-wide KPI summary statistics across all monitored forests "
        "and active fires, plus a ranked, prioritized list of threatened forests "
        "with grounded why-at-risk explainability bullets."
    ),
)
def get_forest_monitoring_dashboard(
    status_filter: Annotated[
        str | None,
        Query(
            alias="status",
            description="Filter by threat level (ACTIVE_FIRE, CRITICAL, WARNING, etc.)",
        ),
    ] = None,
    country_code: Annotated[
        str | None,
        Query(
            alias="country",
            description="ISO 3166-1 alpha-2 country code filter (e.g. 'IN', 'BR')",
        ),
    ] = None,
    search: Annotated[
        str | None,
        Query(description="Text search filter by name, OSM ID, or region"),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=500, description="Page limit"),
    ] = 50,
    offset: Annotated[
        int,
        Query(ge=0, description="Page offset"),
    ] = 0,
) -> ForestMonitoringDashboardResponse:
    """Retrieve global forest threat monitoring dashboard and prioritized list."""
    threat_service = get_forest_threat_service()
    summary, paged_items, total_filtered = (
        threat_service.get_global_monitoring_dashboard(
            status_filter=status_filter,
            country_code=country_code,
            search=search,
            limit=limit,
            offset=offset,
        )
    )

    summary_resp = GlobalForestMonitoringSummaryResponse(
        total_monitored_forests=summary.total_monitored_forests,
        safe_forests=summary.safe_forests,
        awareness_forests=summary.awareness_forests,
        warning_forests=summary.warning_forests,
        critical_forests=summary.critical_forests,
        active_fire_forests=summary.active_fire_forests,
        total_threatened_forests=summary.total_threatened_forests,
        active_thermal_events_evaluated=summary.active_thermal_events_evaluated,
        evaluated_at=summary.evaluated_at.isoformat(),
    )

    items_resp = [
        ForestThreatSummaryItemResponse(
            forest_id=item.forest_id,
            osm_identity=item.osm_identity,
            name=item.name,
            country_code=item.country_code,
            forest_type=item.forest_type.value,
            osm_tag=item.osm_tag,
            area_km2=item.area_km2,
            centroid=item.centroid,
            threat_level=item.threat_level.value,
            inside_forest=item.inside_forest,
            primary_event_id=item.primary_event_id,
            primary_distance_km=item.primary_distance_km,
            primary_confidence=item.primary_confidence,
            primary_frp_mw=item.primary_frp_mw,
            active_threat_count=item.active_threat_count,
            why_at_risk=item.why_at_risk,
            progression_trend=item.progression_trend,
            evaluated_at=item.evaluated_at.isoformat(),
        )
        for item in paged_items
    ]

    return ForestMonitoringDashboardResponse(
        success=True,
        summary=summary_resp,
        total_filtered=total_filtered,
        limit=limit,
        offset=offset,
        forests=items_resp,
    )


@router.get(
    "/threats/forest/{forest_id}",
    response_model=ForestThreatDetailResponse,
    status_code=status.HTTP_200_OK,
    operation_id="get_forest_threat_detail",
    summary="Retrieve detailed threat report for a single forest",
    description=(
        "Evaluates all active thermal events against this specific forest, "
        "returning all candidate fires, nearest boundary distance, and AI bullets."
    ),
)
def get_forest_threat_detail(forest_id: str) -> ForestThreatDetailResponse:
    """Retrieve detailed threat intelligence report for a single forest."""
    threat_service = get_forest_threat_service()
    try:
        detail = threat_service.get_forest_threat_detail_by_id(forest_id)
    except NotFoundError as nfe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(nfe),
        ) from nfe
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate threat detail for forest '{forest_id}': {e}",
        ) from e

    forest_resp = ForestDetailResponse(
        id=detail.forest.forest_id,
        osm_id=detail.forest.osm_id,
        osm_type=detail.forest.osm_type,
        osm_identity=detail.forest.osm_identity,
        name=detail.forest.name,
        name_en=detail.forest.name_en,
        country_code=detail.forest.country_code,
        region=detail.forest.region,
        forest_type=detail.forest.forest_type,
        osm_tag=detail.forest.osm_tag,
        area_km2=detail.forest.area_km2,
        centroid=detail.forest.centroid,
        geometry={
            "type": detail.forest.geometry.type,
            "coordinates": detail.forest.geometry.coordinates,
        },
        metadata=detail.forest.metadata_tags,
        source=detail.forest.source,
        is_repaired=detail.forest.is_repaired,
    )

    threatening_resps = [
        ForestThreatCandidateEventResponse(
            event_id=ev.event_id,
            coordinate=ev.coordinate,
            distance_km=ev.distance_km,
            inside_forest=ev.inside_forest,
            threat_level=ev.threat_level.value,
            confidence=ev.confidence,
            frp_mw=ev.frp_mw,
            classification=ev.classification,
            detected_at=ev.detected_at.isoformat() if ev.detected_at else None,
        )
        for ev in detail.threatening_events
    ]

    return ForestThreatDetailResponse(
        success=True,
        forest=forest_resp,
        threat_level=detail.threat_level.value,
        is_threatened=detail.is_threatened,
        inside_forest=detail.inside_forest,
        nearest_event_id=detail.nearest_event_id,
        nearest_distance_km=detail.nearest_distance_km,
        nearest_point=detail.nearest_point,
        primary_confidence=detail.primary_confidence,
        primary_frp_mw=detail.primary_frp_mw,
        threatening_events=threatening_resps,
        why_at_risk=detail.why_at_risk,
        progression_trend=detail.progression_trend,
        evaluated_at=detail.evaluated_at.isoformat(),
    )


@router.get(
    "/{forest_id}",
    response_model=ForestDetailResponse,
    status_code=status.HTTP_200_OK,
    operation_id="get_forest_detail",
    summary="Retrieve canonical forest detail by ID",
    description="Returns full metadata, geometry, centroid, and OSM tags for a forest.",
)
def get_forest_detail(forest_id: str) -> ForestDetailResponse:
    """Retrieve canonical single forest detail."""
    return ForestQueryService.get_forest_by_id(forest_id)
